package worker

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/djtech/job-queue/queue"
	"github.com/google/uuid"
)

// JobHandler defines the interface for processing jobs
type JobHandler interface {
	Handle(ctx context.Context, job *queue.Job) (*queue.JobResult, error)
}

// WorkerConfig holds worker configuration
type WorkerConfig struct {
	WorkerID       string
	Concurrency    int
	HeartbeatInterval time.Duration
	JobTTL         time.Duration
	ClaimTimeout   time.Duration
	Queues         []string // Queue names to listen to (for future multi-queue support)
}

// Worker processes jobs from the queue
type Worker struct {
	config   WorkerConfig
	queue    queue.Queue
	handlers map[string]JobHandler
	mu       sync.RWMutex
	wg       sync.WaitGroup
	ctx      context.Context
	cancel   context.CancelFunc
	running  bool
	stats    WorkerStats
}

// WorkerStats holds worker statistics
type WorkerStats struct {
	JobsProcessed   int64
	JobsSucceeded   int64
	JobsFailed      int64
	JobsRetried     int64
	TotalLatency    time.Duration
	StartTime       time.Time
	LastJobTime     time.Time
	mu              sync.Mutex
}

// NewWorker creates a new worker
func NewWorker(config WorkerConfig, q queue.Queue) *Worker {
	if config.WorkerID == "" {
		config.WorkerID = "worker-" + uuid.New().String()[:8]
	}
	if config.Concurrency == 0 {
		config.Concurrency = 10
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

	ctx, cancel := context.WithCancel(context.Background())
	return &Worker{
		config:   config,
		queue:    q,
		handlers: make(map[string]JobHandler),
		ctx:      ctx,
		cancel:   cancel,
		stats:    WorkerStats{StartTime: time.Now()},
	}
}

// RegisterHandler registers a handler for a job type
func (w *Worker) RegisterHandler(jobType string, handler JobHandler) {
	w.mu.Lock()
	defer w.mu.Unlock()
	w.handlers[jobType] = handler
}

// Start begins processing jobs
func (w *Worker) Start() error {
	w.mu.Lock()
	if w.running {
		w.mu.Unlock()
		return fmt.Errorf("worker already running")
	}
	w.running = true
	w.mu.Unlock()

	log.Printf("Worker %s starting with concurrency %d", w.config.WorkerID, w.config.Concurrency)

	// Start heartbeat goroutine
	w.wg.Add(1)
	go w.heartbeatLoop()

	// Start worker pool
	for i := 0; i < w.config.Concurrency; i++ {
		w.wg.Add(1)
		go w.workerLoop(i)
	}

	return nil
}

// Stop gracefully stops the worker
func (w *Worker) Stop() error {
	w.mu.Lock()
	if !w.running {
		w.mu.Unlock()
		return nil
	}
	w.running = false
	w.mu.Unlock()

	log.Printf("Worker %s stopping...", w.config.WorkerID)
	w.cancel()
	w.wg.Wait()
	log.Printf("Worker %s stopped", w.config.WorkerID)
	return nil
}

// Stats returns worker statistics
func (w *Worker) Stats() WorkerStats {
	w.stats.mu.Lock()
	defer w.stats.mu.Unlock()
	return w.stats
}

func (w *Worker) workerLoop(workerIndex int) {
	defer w.wg.Done()

	for {
		select {
		case <-w.ctx.Done():
			return
		default:
			w.processOneJob()
		}
	}
}

func (w *Worker) processOneJob() {
	// Claim a job
	job, err := w.queue.Claim(w.ctx, w.config.WorkerID)
	if err != nil {
		log.Printf("Worker %s: failed to claim job: %v", w.config.WorkerID, err)
		time.Sleep(1 * time.Second) // Back off on error
		return
	}

	if job == nil {
		// No jobs available, brief pause
		time.Sleep(500 * time.Millisecond)
		return
	}

	// Find handler
	w.mu.RLock()
	handler, ok := w.handlers[job.Type]
	w.mu.RUnlock()

	if !ok {
		err := fmt.Errorf("no handler registered for job type: %s", job.Type)
		log.Printf("Worker %s: %v", w.config.WorkerID, err)
		w.queue.Fail(w.ctx, w.config.WorkerID, job, err)
		w.recordFailure()
		return
	}

	// Process job with timeout
	jobCtx, cancel := context.WithTimeout(w.ctx, job.Timeout)
	defer cancel()

	startTime := time.Now()
	result, err := handler.Handle(jobCtx, job)
	latency := time.Since(startTime)

	if err != nil {
		log.Printf("Worker %s: job %s failed: %v", w.config.WorkerID, job.ID, err)
		w.queue.Fail(w.ctx, w.config.WorkerID, job, err)
		w.recordFailure()
		return
	}

	// Complete job
	if err := w.queue.Complete(w.ctx, w.config.WorkerID, job, result); err != nil {
		log.Printf("Worker %s: failed to complete job %s: %v", w.config.WorkerID, job.ID, err)
		w.recordFailure()
		return
	}

	w.recordSuccess(latency)
	log.Printf("Worker %s: job %s completed in %v", w.config.WorkerID, job.ID, latency)
}

func (w *Worker) heartbeatLoop() {
	defer w.wg.Done()

	ticker := time.NewTicker(w.config.HeartbeatInterval)
	defer ticker.Stop()

	for {
		select {
		case <-w.ctx.Done():
			return
		case <-ticker.C:
			if err := w.queue.Heartbeat(w.ctx, w.config.WorkerID); err != nil {
				log.Printf("Worker %s: heartbeat failed: %v", w.config.WorkerID, err)
			}
		}
	}
}

func (w *Worker) recordSuccess(latency time.Duration) {
	w.stats.mu.Lock()
	defer w.stats.mu.Unlock()
	w.stats.JobsProcessed++
	w.stats.JobsSucceeded++
	w.stats.TotalLatency += latency
	w.stats.LastJobTime = time.Now()
}

func (w *Worker) recordFailure() {
	w.stats.mu.Lock()
	defer w.stats.mu.Unlock()
	w.stats.JobsProcessed++
	w.stats.JobsFailed++
	w.stats.LastJobTime = time.Now()
}

// AverageLatency returns the average job processing latency
func (ws *WorkerStats) AverageLatency() time.Duration {
	ws.mu.Lock()
	defer ws.mu.Unlock()
	if ws.JobsSucceeded == 0 {
		return 0
	}
	return ws.TotalLatency / time.Duration(ws.JobsSucceeded)
}

// JobHandlerFunc allows using a function as a JobHandler
type JobHandlerFunc func(ctx context.Context, job *queue.Job) (*queue.JobResult, error)

func (f JobHandlerFunc) Handle(ctx context.Context, job *queue.Job) (*queue.JobResult, error) {
	return f(ctx, job)
}

// Example handlers

// EchoHandler is a simple test handler
func EchoHandler(ctx context.Context, job *queue.Job) (*queue.JobResult, error) {
	var payload map[string]any
	if err := json.Unmarshal(job.Payload, &payload); err != nil {
		return nil, fmt.Errorf("invalid payload: %w", err)
	}

	message, _ := payload["message"].(string)
	return &queue.JobResult{
		Output: json.RawMessage(fmt.Sprintf(`{"echo": "%s"}`, message)),
	}, nil
}

// SleepHandler sleeps for a specified duration (for testing timeouts)
func SleepHandler(ctx context.Context, job *queue.Job) (*queue.JobResult, error) {
	var payload map[string]any
	if err := json.Unmarshal(job.Payload, &payload); err != nil {
		return nil, fmt.Errorf("invalid payload: %w", err)
	}

	durationMs, _ := payload["duration_ms"].(float64)
	if durationMs == 0 {
		durationMs = 1000
	}

	select {
	case <-ctx.Done():
		return nil, ctx.Err()
	case <-time.After(time.Duration(durationMs) * time.Millisecond):
		return &queue.JobResult{
			Output: json.RawMessage(fmt.Sprintf(`{"slept_ms": %f}`, durationMs)),
		}, nil
	}
}