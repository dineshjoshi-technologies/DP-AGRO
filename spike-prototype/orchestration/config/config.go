package config

import (
	"time"
)

// OrchestrationConfig holds the complete orchestration configuration
type OrchestrationConfig struct {
	Sandbox  SandboxConfig  `json:"sandbox"`
	Executor ExecutorConfig `json:"executor"`
	Billing  BillingConfig  `json:"billing"`
}

// SandboxConfig holds sandbox manager configuration
type SandboxConfig struct {
	ContainerdSocket string        `json:"containerd_socket"` // e.g., "/run/containerd/containerd.sock"
	GVisorRuntime    string        `json:"gvisor_runtime"`    // e.g., "runsc"
	BaseImage        string        `json:"base_image"`        // e.g., "djtech/agent-base:latest"
	NetworkProfile   string        `json:"network_profile"`   // e.g., "default-deny"
	DefaultCPU       string        `json:"default_cpu"`       // e.g., "1000m"
	DefaultMemory    string        `json:"default_memory"`    // e.g., "512Mi"
	DefaultDisk      string        `json:"default_disk"`      // e.g., "1Gi"
	DefaultTimeout   time.Duration `json:"default_timeout"`   // e.g., "24h"
	MaxConcurrent    int           `json:"max_concurrent"`    // max concurrent sandboxes
}

// ExecutorConfig holds agent executor configuration
type ExecutorConfig struct {
	LLMRouterURL      string `json:"llm_router_url"`       // e.g., "http://localhost:8081"
	LLMGatewayURL     string `json:"llm_gateway_url"`      // e.g., "http://localhost:8080"
	JobQueueRedisAddr string `json:"job_queue_redis_addr"` // e.g., "localhost:6379"
	JobQueuePostgresDSN string `json:"job_queue_postgres_dsn"` // e.g., "postgres://user:pass@localhost:5432/queue"
	WorkerConcurrency int    `json:"worker_concurrency"`   // e.g., 10
	HeartbeatInterval time.Duration `json:"heartbeat_interval"` // e.g., "30s"
	JobTTL            time.Duration `json:"job_ttl"`            // e.g., "5m"
	ClaimTimeout      time.Duration `json:"claim_timeout"`      // e.g., "30s"
}

// BillingConfig holds billing configuration
type BillingConfig struct {
	PricePerCPUSecond      string  `json:"price_per_cpu_second"`       // e.g., "0.00001"
	PricePerMemoryGBSecond string  `json:"price_per_memory_gb_second"` // e.g., "0.000001"
	PricePerLLMToken       string  `json:"price_per_llm_token"`        // e.g., "0.000001"
	WebhookURL             string  `json:"webhook_url"`                // e.g., "https://billing.example.com/webhook"
	Currency               string  `json:"currency"`                   // e.g., "USD"
	Enabled                bool    `json:"enabled"`                    // e.g., true
}