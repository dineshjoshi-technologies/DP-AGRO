package executor

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/djtech/job-queue/queue"
	"github.com/djtech/job-queue/worker"
	"github.com/djtech/orchestration/sandbox"
	"github.com/djtech/orchestration/billing"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
)

// ExecuteRequest represents a request to execute an agent
type ExecuteRequest struct {
	AgentID       string          `json:"agent_id"`
	AgentType     string          `json:"agent_type"`     // e.g., "python", "node", "go"
	Code          string          `json:"code"`           // Agent code to execute
	Config        json.RawMessage `json:"config"`         // Agent configuration
	Env           map[string]string `json:"env"`          // Environment variables
	Secrets       map[string]string `json:"secrets"`      // Secrets (injected at runtime)
	Timeout       time.Duration   `json:"timeout"`        // Execution timeout
	MaxTokens     int             `json:"max_tokens"`     // Max LLM tokens
	AllowedModels []string        `json:"allowed_models"` // Allowed LLM models
	Priority      int             `json:"priority"`       // Job priority
	IdempotencyKey string         `json:"idempotency_key"` // For exactly-once
}

// ExecuteResponse represents the result of agent execution
type ExecuteResponse struct {
	ExecutionID string          `json:"execution_id"`
	JobID       string          `json:"job_id"`
	Status      string          `json:"status"`       // pending, running, completed, failed
	Result      json.RawMessage `json:"result,omitempty"`
	Error       string          `json:"error,omitempty"`
	StartedAt   *time.Time      `json:"started_at,omitempty"`
	CompletedAt *time.Time      `json:"completed_at,omitempty"`
	Billing     *BillingInfo    `json:"billing,omitempty"`
}

// BillingInfo contains billing details for an execution
type BillingInfo struct {
	ExecutionID      string  `json:"execution_id"`
	AgentID          string  `json:"agent_id"`
	DurationSeconds  float64 `json:"duration_seconds"`
	CPUSeconds       float64 `json:"cpu_seconds"`
	MemoryGBSeconds  float64 `json:"memory_gb_seconds"`
	LLMTokensIn      int64   `json:"llm_tokens_in"`
	LLMTokensOut     int64   `json:"llm_tokens_out"`
	EstimatedCost    float64 `json:"estimated_cost"`
	Currency         string  `json:"currency"`
}

// Executor executes agent jobs using sandbox + LLM router + LLM gateway + job queue
type Executor struct {
	config        *ExecutorConfig
	sandboxMgr    *sandbox.Manager
	billingTracker *billing.Tracker
	worker        *worker.Worker
	jobQueue      queue.Queue
	llmRouterURL  string
	llmGatewayURL string
	httpClient    *http.Client
	executions    map[string]*Execution
	mu            sync.RWMutex
	closed        bool
}

// ExecutorConfig holds executor configuration
type ExecutorConfig struct {
	LLMRouterURL      string
	LLMGatewayURL     string
	JobQueueRedisAddr string
	JobQueuePostgresDSN string
	WorkerConcurrency int
	HeartbeatInterval time.Duration
	JobTTL            time.Duration
	ClaimTimeout      time.Duration
}

// Execution represents a running agent execution
type Execution struct {
	ID            string
	AgentID       string
	JobID         string
	SandboxID     string
	Request       *ExecuteRequest
	Response      *ExecuteResponse
	Sandbox       *sandbox.Sandbox
	Status        string // pending, running, completed, failed
	CreatedAt     time.Time
	StartedAt     *time.Time
	CompletedAt   *time.Time
	Error         string
	Billing       *BillingInfo
	mu            sync.RWMutex
}

// NewExecutor creates a new agent executor
func NewExecutor(config *ExecutorConfig, sandboxMgr *sandbox.Manager, billingTracker *billing.Tracker) (*Executor, error) {
	// Set defaults
	if config.WorkerConcurrency == 0 {
		config.WorkerConcurrency = 10
	}
	if config.HeartbeatInterval == 0 {
		config.HeartbeatInterval = 30 * time.Second
	}
	if config.JobTTL == 0 {
		config.JobTTL = 5 * time.Minute
	}
	if config.ClaimTimeout == 0 {
		config.ClaimTimeout = 30 * time.Second
	}

	e := &Executor{
		config:         config,
		sandboxMgr:     sandboxMgr,
		billingTracker: billingTracker,
		executions:     make(map[string]*Execution),
		httpClient: &http.Client{
			Timeout: 120 * time.Second,
		},
	}

	// Initialize job queue
	if config.JobQueueRedisAddr != "" {
		client := redis.NewClient(&redis.Options{
			Addr: config.JobQueueRedisAddr,
		})
		q := queue.NewRedisQueue(client, "queue", config.JobTTL, config.HeartbeatInterval)
		e.jobQueue = q
	}

	// Create worker pool for background job processing
	workerConfig := worker.WorkerConfig{
		WorkerID:        "executor-" + uuid.New().String()[:8],
		Concurrency:     config.WorkerConcurrency,
		HeartbeatInterval: config.HeartbeatInterval,
		JobTTL:          config.JobTTL,
		ClaimTimeout:    config.ClaimTimeout,
	}
	e.worker = worker.NewWorker(workerConfig, e.jobQueue)

	// Register job handlers
	e.worker.RegisterHandler("agent-execution", e.handleAgentExecution)
	e.worker.RegisterHandler("llm-call", e.handleLLMCall)
	e.worker.RegisterHandler("checkpoint", e.handleCheckpoint)

	return e, nil
}

// Execute executes an agent (synchronously for now, can be made async)
func (e *Executor) Execute(ctx context.Context, req *ExecuteRequest) (*ExecuteResponse, error) {
	executionID := "exec-" + uuid.New().String()[:12]
	
	execution := &Execution{
		ID:        executionID,
		AgentID:   req.AgentID,
		Request:   req,
		Status:    "pending",
		CreatedAt: time.Now(),
		Response: &ExecuteResponse{
			ExecutionID: executionID,
			Status:      "pending",
		},
	}

	e.mu.Lock()
	e.executions[executionID] = execution
	e.mu.Unlock()

	// For now, execute synchronously
	// In production, this would enqueue a job and return immediately
	return e.executeSync(ctx, execution)
}

// executeSync executes an agent synchronously
func (e *Executor) executeSync(ctx context.Context, execution *Execution) (*ExecuteResponse, error) {
	req := execution.Request
	
	execution.mu.Lock()
	execution.Status = "running"
	now := time.Now()
	execution.StartedAt = &now
	execution.Response.Status = "running"
	execution.Response.StartedAt = &now
	execution.mu.Unlock()

	// Create sandbox
	sandboxConfig := sandbox.SandboxConfig{
		CPU:     e.config.DefaultCPU,
		Memory:  e.config.DefaultMemory,
		Disk:    e.config.DefaultDisk,
		Timeout: req.Timeout,
		Network: "default-deny",
		Env:     req.Env,
		Secrets: req.Secrets,
		Workdir: "/workspace",
		Command: e.getCommandForType(req.AgentType),
		Args:    []string{req.Code},
	}

	if req.Timeout == 0 {
		sandboxConfig.Timeout = 24 * time.Hour
	}

	sandbox, err := e.sandboxMgr.CreateSandbox(ctx, req.AgentID, sandboxConfig)
	if err != nil {
		execution.setError(fmt.Sprintf("failed to create sandbox: %v", err))
		return execution.Response, err
	}

	execution.Sandbox = sandbox
	execution.SandboxID = sandbox.ID()

	// Wait for sandbox to complete
	completedSandbox, err := e.sandboxMgr.WaitSandbox(ctx, sandbox.ID())
	if err != nil {
		execution.setError(fmt.Sprintf("sandbox execution failed: %v", err))
		return execution.Response, err
	}

	// Collect resource usage
	resources, err := e.sandboxMgr.CollectResources(ctx, sandbox.ID())
	if err != nil {
		log.Printf("Warning: failed to collect resources: %v", err)
	}

	// Calculate billing
	billingInfo := e.calculateBilling(execution, resources)
	execution.Billing = billingInfo
	execution.Response.Billing = billingInfo

	// Record billing
	if e.billingTracker != nil && e.billingTracker.Enabled() {
		e.billingTracker.Record(billingInfo)
	}

	// Update execution status
	execution.mu.Lock()
	execution.Status = "completed"
	now = time.Now()
	execution.CompletedAt = &now
	execution.Response.Status = "completed"
	execution.Response.CompletedAt = &now
	execution.Response.Result = json.RawMessage(fmt.Sprintf(`{"output": "completed", "sandbox_id": "%s"}`, sandbox.ID()))
	execution.mu.Unlock()

	// Clean up sandbox (or keep for debugging)
	// e.sandboxMgr.TerminateSandbox(ctx, sandbox.ID())

	return execution.Response, nil
}

// getCommandForType returns the command to run based on agent type
func (e *Executor) getCommandForType(agentType string) []string {
	switch agentType {
	case "python":
		return []string{"python3", "-c"}
	case "node", "nodejs", "javascript":
		return []string{"node", "-e"}
	case "go", "golang":
		return []string{"go", "run"}
	case "rust":
		return []string{"rustc", "--edition", "2021", "-o", "/tmp/agent", "-"; "sh", "-c", "/tmp/agent"}
	default:
		return []string{"python3", "-c"}
	}
}

// calculateBilling calculates billing for an execution
func (e *Executor) calculateBilling(execution *Execution, resources *sandbox.ResourceUsage) *BillingInfo {
	// In a real implementation, these would come from config
	pricePerCPUSecond := 0.00001
	pricePerMemoryGBSecond := 0.000001
	pricePerLLMToken := 0.000001

	duration := 0.0
	if execution.StartedAt != nil && execution.CompletedAt != nil {
		duration = execution.CompletedAt.Sub(*execution.StartedAt).Seconds()
	}

	cpuCost := resources.CPUSeconds * pricePerCPUSecond
	memoryCost := resources.MemoryGBSeconds * pricePerMemoryGBSecond
	llmCost := float64(resources.LLMTokensIn+resources.LLMTokensOut) * pricePerLLMToken
	totalCost := cpuCost + memoryCost + llmCost

	return &BillingInfo{
		ExecutionID:      execution.ID,
		AgentID:          execution.AgentID,
		DurationSeconds:  duration,
		CPUSeconds:       resources.CPUSeconds,
		MemoryGBSeconds:  resources.MemoryGBSeconds,
		LLMTokensIn:      resources.LLMTokensIn,
		LLMTokensOut:     resources.LLMTokensOut,
		EstimatedCost:    totalCost,
		Currency:         "USD",
	}
}

// handleAgentExecution handles agent execution jobs from the queue
func (e *Executor) handleAgentExecution(ctx context.Context, job *queue.Job) (*queue.JobResult, error) {
	var req ExecuteRequest
	if err := json.Unmarshal(job.Payload, &req); err != nil {
		return nil, fmt.Errorf("invalid job payload: %w", err)
	}

	executionID := job.ID
	execution := &Execution{
		ID:        executionID,
		AgentID:   req.AgentID,
		JobID:     job.ID,
		Request:   &req,
		Status:    "running",
		CreatedAt: job.CreatedAt,
		Response: &ExecuteResponse{
			ExecutionID: executionID,
			JobID:       job.ID,
			Status:      "running",
		},
	}

	e.mu.Lock()
	e.executions[executionID] = execution
	e.mu.Unlock()

	now := time.Now()
	execution.StartedAt = &now
	execution.Response.StartedAt = &now

	// Create sandbox
	sandboxConfig := sandbox.SandboxConfig{
		CPU:     e.config.DefaultCPU,
		Memory:  e.config.DefaultMemory,
		Disk:    e.config.DefaultDisk,
		Timeout: req.Timeout,
		Network: "default-deny",
		Env:     req.Env,
		Secrets: req.Secrets,
		Workdir: "/workspace",
		Command: e.getCommandForType(req.AgentType),
		Args:    []string{req.Code},
	}

	sandbox, err := e.sandboxMgr.CreateSandbox(ctx, req.AgentID, sandboxConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create sandbox: %w", err)
	}

	execution.Sandbox = sandbox
	execution.SandboxID = sandbox.ID()

	// Wait for completion
	completedSandbox, err := e.sandboxMgr.WaitSandbox(ctx, sandbox.ID())
	if err != nil {
		return nil, fmt.Errorf("sandbox execution failed: %w", err)
	}

	// Collect resources
	resources, _ := e.sandboxMgr.CollectResources(ctx, sandbox.ID())
	billingInfo := e.calculateBilling(execution, resources)

	// Record billing
	if e.billingTracker != nil && e.billingTracker.Enabled() {
		e.billingTracker.Record(billingInfo)
	}

	// Complete
	completedAt := time.Now()
	execution.CompletedAt = &completedAt
	execution.Response.CompletedAt = &completedAt
	execution.Response.Status = "completed"
	execution.Response.Billing = billingInfo
	execution.Response.Result = json.RawMessage(fmt.Sprintf(`{"output": "completed", "sandbox_id": "%s"}`, sandbox.ID()))

	return &queue.JobResult{
		Output: execution.Response.Result,
	}, nil
}

// handleLLMCall handles LLM call jobs from the queue
func (e *Executor) handleLLMCall(ctx context.Context, job *queue.Job) (*queue.JobResult, error) {
	// Forward to LLM Router
	// This is a placeholder - in reality, this would call the LLM router HTTP API
	return &queue.JobResult{
		Output: json.RawMessage(`{"status": "llm call not implemented"}`),
	}, nil
}

// handleCheckpoint handles checkpoint/resume jobs
func (e *Executor) handleCheckpoint(ctx context.Context, job *queue.Job) (*queue.JobResult, error) {
	// Handle checkpoint/resume for long-running agents
	return &queue.JobResult{
		Output: json.RawMessage(`{"status": "checkpoint not implemented"}`),
	}, nil
}

// GetExecution returns an execution by ID
func (e *Executor) GetExecution(id string) (*Execution, bool) {
	e.mu.RLock()
	defer e.mu.RUnlock()
	exec, ok := e.executions[id]
	return exec, ok
}

// ListExecutions returns all executions
func (e *Executor) ListExecutions() []*Execution {
	e.mu.RLock()
	defer e.mu.RUnlock()
	result := make([]*Execution, 0, len(e.executions))
	for _, exec := range e.executions {
		result = append(result, exec)
	}
	return result
}

// Start starts the executor's worker pool
func (e *Executor) Start() error {
	return e.worker.Start()
}

// Stop stops the executor
func (e *Executor) Stop() error {
	e.mu.Lock()
	e.closed = true
	e.mu.Unlock()

	if e.worker != nil {
		e.worker.Stop()
	}
	if e.jobQueue != nil {
		// Job queue doesn't have a close method in the interface
	}
	return nil
}

// Close closes the executor
func (e *Executor) Close() error {
	return e.Stop()
}

// Stats returns executor statistics
func (e *Executor) Stats() map[string]interface{} {
	e.mu.RLock()
	defer e.mu.RUnlock()

	stats := map[string]interface{}{
		"total_executions": len(e.executions),
		"pending":          0,
		"running":          0,
		"completed":        0,
		"failed":           0,
	}

	for _, exec := range e.executions {
		exec.mu.RLock()
		switch exec.Status {
		case "pending":
			stats["pending"] = stats["pending"].(int) + 1
		case "running":
			stats["running"] = stats["running"].(int) + 1
		case "completed":
			stats["completed"] = stats["completed"].(int) + 1
		case "failed":
			stats["failed"] = stats["failed"].(int) + 1
		}
		exec.mu.RUnlock()
	}

	if e.worker != nil {
		workerStats := e.worker.Stats()
		stats["worker"] = map[string]interface{}{
			"jobs_processed":   workerStats.JobsProcessed,
			"jobs_succeeded":   workerStats.JobsSucceeded,
			"jobs_failed":      workerStats.JobsFailed,
			"avg_latency_ms":   workerStats.AverageLatency().Milliseconds(),
		}
	}

	return stats
}

// Execution methods

func (ex *Execution) setError(errMsg string) {
	ex.mu.Lock()
	defer ex.mu.Unlock()
	ex.Error = errMsg
	ex.Status = "failed"
	now := time.Now()
	ex.CompletedAt = &now
	ex.Response.Status = "failed"
	ex.Response.Error = errMsg
	ex.Response.CompletedAt = &now
}