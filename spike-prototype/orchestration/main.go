package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/djtech/orchestration/sandbox"
	"github.com/djtech/orchestration/executor"
	"github.com/djtech/orchestration/billing"
	"github.com/djtech/orchestration/config"
)

func main() {
	configPath := flag.String("config", "/etc/orchestration/config.json", "Path to orchestration config file")
	port := flag.String("port", "8082", "Port to listen on")
	flag.Parse()

	// Load config
	configData, err := os.ReadFile(*configPath)
	if err != nil {
		log.Fatalf("Failed to read config: %v", err)
	}

	var cfg config.OrchestrationConfig
	if err := json.Unmarshal(configData, &cfg); err != nil {
		log.Fatalf("Failed to parse config: %v", err)
	}

	// Expand environment variables
	expandEnvVars(&cfg)

	// Create sandbox manager
	sandboxMgr, err := sandbox.NewManager(&cfg.Sandbox)
	if err != nil {
		log.Fatalf("Failed to create sandbox manager: %v", err)
	}
	defer sandboxMgr.Close()

	// Create billing tracker
	billingTracker := billing.NewTracker(&cfg.Billing)

	// Create agent executor
	agentExecutor, err := executor.NewExecutor(&cfg.Executor, sandboxMgr, billingTracker)
	if err != nil {
		log.Fatalf("Failed to create executor: %v", err)
	}
	defer agentExecutor.Close()

	// Create HTTP server
	server := &http.Server{
		Addr:    ":" + *port,
		Handler: createHandler(agentExecutor, billingTracker),
	}

	// Start server
	go func() {
		log.Printf("Starting Orchestration Service on port %s", *port)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server failed: %v", err)
		}
	}()

	// Wait for shutdown signal
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh

	log.Println("Shutting down...")
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	server.Shutdown(ctx)
	log.Println("Orchestration service stopped")
}

func expandEnvVars(cfg *config.OrchestrationConfig) {
	// Expand env vars in sandbox config
	cfg.Sandbox.ContainerdSocket = os.Getenv(cfg.Sandbox.ContainerdSocket)
	cfg.Sandbox.GVisorRuntime = os.Getenv(cfg.Sandbox.GVisorRuntime)
	cfg.Sandbox.BaseImage = os.Getenv(cfg.Sandbox.BaseImage)
	cfg.Sandbox.NetworkProfile = os.Getenv(cfg.Sandbox.NetworkProfile)

	// Expand env vars in executor config
	cfg.Executor.LLMRouterURL = os.Getenv(cfg.Executor.LLMRouterURL)
	cfg.Executor.LLMGatewayURL = os.Getenv(cfg.Executor.LLMGatewayURL)
	cfg.Executor.JobQueueRedisAddr = os.Getenv(cfg.Executor.JobQueueRedisAddr)
	cfg.Executor.JobQueuePostgresDSN = os.Getenv(cfg.Executor.JobQueuePostgresDSN)

	// Expand env vars in billing config
	cfg.Billing.PricePerCPUSecond = os.Getenv(cfg.Billing.PricePerCPUSecond)
	cfg.Billing.PricePerMemoryGBSecond = os.Getenv(cfg.Billing.PricePerMemoryGBSecond)
	cfg.Billing.PricePerLLMToken = os.Getenv(cfg.Billing.PricePerLLMToken)
	cfg.Billing.WebhookURL = os.Getenv(cfg.Billing.WebhookURL)
}

func createHandler(exec *executor.Executor, billing *billing.Tracker) http.Handler {
	mux := http.NewServeMux()
	
	// Health check
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"status":    "healthy",
			"timestamp": time.Now().Unix(),
			"version":   "0.1.0",
		})
	})

	// Metrics
	mux.HandleFunc("/metrics", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		stats := exec.Stats()
		billingStats := billing.Stats()
		json.NewEncoder(w).Encode(map[string]interface{}{
			"executor": stats,
			"billing":  billingStats,
		})
	})

	// Agent execution API
	mux.HandleFunc("/v1/agents/execute", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		var req executor.ExecuteRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "Invalid request", http.StatusBadRequest)
			return
		}

		ctx := r.Context()
		resp, err := exec.Execute(ctx, &req)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	})

	// Agent status API
	mux.HandleFunc("/v1/agents/", func(w http.ResponseWriter, r *http.Request) {
		// Extract agent ID from path
		// /v1/agents/{id}/status or /v1/agents/{id}/logs
		// Simplified for now
		http.Error(w, "Not implemented", http.StatusNotImplemented)
	})

	// Billing API
	mux.HandleFunc("/v1/billing/usage", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(billing.Stats())
	})

	return mux
}