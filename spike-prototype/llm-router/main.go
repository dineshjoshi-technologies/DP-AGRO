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

	"github.com/djtech/llm-router/router"
)

func main() {
	configPath := flag.String("config", "/etc/llm-router/config.json", "Path to router config file")
	port := flag.String("port", "8081", "Port to listen on")
	flag.Parse()

	// Load config
	configData, err := os.ReadFile(*configPath)
	if err != nil {
		log.Fatalf("Failed to read config: %v", err)
	}

	var config router.RouterConfig
	if err := json.Unmarshal(configData, &config); err != nil {
		log.Fatalf("Failed to parse config: %v", err)
	}

	// Expand environment variables in config
	expandEnvVars(&config)

	// Create router
	r, err := router.NewRouter(&config)
	if err != nil {
		log.Fatalf("Failed to create router: %v", err)
	}

	// Create HTTP server
	server := &http.Server{
		Addr:    ":" + *port,
		Handler: r.HTTPHandler(),
	}

	// Start server
	go func() {
		log.Printf("Starting LLM Router on port %s", *port)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server failed: %v", err)
		}
	}()

	// Wait for shutdown signal
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh

	log.Println("Shutting down...")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	server.Shutdown(ctx)
	log.Println("Router stopped")
}

func expandEnvVars(config *router.RouterConfig) {
	for i := range config.Providers {
		config.Providers[i].APIKey = os.Getenv(config.Providers[i].APIKey)
		config.Providers[i].BaseURL = os.Getenv(config.Providers[i].BaseURL)
		for k, v := range config.Providers[i].Headers {
			config.Providers[i].Headers[k] = os.Getenv(v)
		}
	}
}