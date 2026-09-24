package queue

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
)

// RedisQueue implements the Queue interface using Redis
type RedisQueue struct {
	client      *redis.Client
	keyPrefix   string
	scripts     *redisScripts
	mu          sync.RWMutex
	jobTTL      time.Duration
	heartbeatTTL time.Duration
}

// redisScripts holds Lua scripts for atomic operations
type redisScripts struct {
	claimJob      *redis.Script
	heartbeat     *redis.Script
	completeJob   *redis.Script
	failJob       *redis.Script
	moveToPending *redis.Script
}

// NewRedisQueue creates a new Redis-backed queue
func NewRedisQueue(client *redis.Client, keyPrefix string, jobTTL, heartbeatTTL time.Duration) *RedisQueue {
	q := &RedisQueue{
		client:       client,
		keyPrefix:    keyPrefix,
		jobTTL:       jobTTL,
		heartbeatTTL: heartbeatTTL,
	}
	q.initScripts()
	return q
}

func (q *RedisQueue) initScripts() {
	// Atomic job claim: pop from pending, add to processing
	q.scripts.claimJob = redis.NewScript(`
		local job_id = redis.call('ZPOPMIN', KEYS[1], 1)
		if #job_id == 0 then return nil end
		local job_data = job_id[1]
		redis.call('HSET', KEYS[2], 'data', job_data, 'claimed_at', ARGV[1], 'worker_id', ARGV[2])
		redis.call('EXPIRE', KEYS[2], ARGV[3])
		return job_data
	`)

	// Heartbeat: extend TTL on processing job
	q.scripts.heartbeat = redis.NewScript(`
		if redis.call('EXISTS', KEYS[1]) == 0 then return 0 end
		redis.call('EXPIRE', KEYS[1], ARGV[1])
		return 1
	`)

	// Complete job: remove from processing, add to completed
	q.scripts.completeJob = redis.NewScript(`
		redis.call('DEL', KEYS[1])
		return 1
	`)

	// Fail job: increment attempts, re-queue or move to DLQ
	q.scripts.failJob = redis.NewScript(`
		local job_data = redis.call('HGET', KEYS[1], 'data')
		if not job_data then return nil end
		local job = cjson.decode(job_data)
		job.attempts = job.attempts + 1
		job.updated_at = ARGV[1]
		job.error = ARGV[2]
		
		if job.attempts >= job.max_attempts then
			redis.call('DEL', KEYS[1])
			redis.call('RPUSH', KEYS[2], job_data)
			return 'dead_letter'
		else
			local next_retry = ARGV[3]
			job.status = 'scheduled'
			redis.call('DEL', KEYS[1])
			redis.call('ZADD', KEYS[3], next_retry, cjson.encode(job))
			return 'requeued'
		end
	`)

	// Move delayed jobs to pending
	q.scripts.moveToPending = redis.NewScript(`
		local now = tonumber(ARGV[1])
		local jobs = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', now, 'LIMIT', 0, ARGV[2])
		if #jobs > 0 then
			redis.call('ZREM', KEYS[1], unpack(jobs))
			for _, job_data in ipairs(jobs) do
				local job = cjson.decode(job_data)
				job.status = 'pending'
				job.updated_at = ARGV[1]
				redis.call('ZADD', KEYS[2], -job.priority * 1000000 + job.created_at, cjson.encode(job))
			end
		end
		return #jobs
	`)
}

// Enqueue adds a job to the queue
func (q *RedisQueue) Enqueue(ctx context.Context, job *Job) error {
	if job.ID == "" {
		job.ID = uuid.New().String()
	}
	now := time.Now()
	job.CreatedAt = now
	job.UpdatedAt = now
	job.Status = JobStatusPending
	if job.MaxAttempts == 0 {
		job.MaxAttempts = 3
	}
	if job.RetryPolicy.MaxAttempts == 0 {
		job.RetryPolicy = DefaultRetryPolicy()
	}
	job.Version = 1

	data, err := json.Marshal(job)
	if err != nil {
		return fmt.Errorf("failed to marshal job: %w", err)
	}

	// Score: negative priority (higher priority = lower score = popped first) + timestamp for FIFO
	score := float64(-job.Priority*1000000) + float64(job.CreatedAt.UnixNano())/1e9

	key := q.keyPrefix + ":pending"
	if job.ScheduledAt != nil && job.ScheduledAt.After(now) {
		key = q.keyPrefix + ":delayed"
		score = float64(job.ScheduledAt.UnixNano()) / 1e9
		job.Status = JobStatusScheduled
	}

	err = q.client.ZAdd(ctx, key, redis.Z{Score: score, Member: data}).Err()
	if err != nil {
		return fmt.Errorf("failed to enqueue job: %w", err)
	}

	// Also store in PostgreSQL via separate persistence layer
	return nil
}

// Claim atomically claims a job for processing
func (q *RedisQueue) Claim(ctx context.Context, workerID string) (*Job, error) {
	pendingKey := q.keyPrefix + ":pending"
	processingKey := q.keyPrefix + ":processing:" + workerID
	now := time.Now().Unix()
	ttlSeconds := int(q.jobTTL.Seconds())

	result, err := q.scripts.claimJob.Run(ctx, q.client, []string{pendingKey, processingKey}, now, workerID, ttlSeconds).Text()
	if err == redis.Nil {
		return nil, nil // No jobs available
	}
	if err != nil {
		return nil, fmt.Errorf("failed to claim job: %w", err)
	}

	var job Job
	if err := json.Unmarshal([]byte(result), &job); err != nil {
		return nil, fmt.Errorf("failed to unmarshal claimed job: %w", err)
	}

	job.Status = JobStatusProcessing
	nowTime := time.Now()
	job.StartedAt = &nowTime
	job.UpdatedAt = nowTime

	return &job, nil
}

// Heartbeat extends the TTL of a processing job
func (q *RedisQueue) Heartbeat(ctx context.Context, workerID string) error {
	processingKey := q.keyPrefix + ":processing:" + workerID
	ttlSeconds := int(q.heartbeatTTL.Seconds())

	result, err := q.scripts.heartbeat.Run(ctx, q.client, []string{processingKey}, ttlSeconds).Int()
	if err != nil {
		return fmt.Errorf("failed to heartbeat: %w", err)
	}
	if result == 0 {
		return ErrJobNotFound
	}
	return nil
}

// Complete marks a job as completed
func (q *RedisQueue) Complete(ctx context.Context, workerID string, job *Job, result *JobResult) error {
	processingKey := q.keyPrefix + ":processing:" + workerID

	job.Status = JobStatusCompleted
	now := time.Now()
	job.CompletedAt = &now
	job.UpdatedAt = now
	job.Result = result
	job.Version++

	_, err := q.scripts.completeJob.Run(ctx, q.client, []string{processingKey}).Int()
	return err
}

// Fail marks a job as failed and handles retry logic
func (q *RedisQueue) Fail(ctx context.Context, workerID string, job *Job, err error) error {
	processingKey := q.keyPrefix + ":processing:" + workerID
	deadLetterKey := q.keyPrefix + ":dead_letter"
	delayedKey := q.keyPrefix + ":delayed"

	job.Error = err.Error()
	nextRetry := job.NextRetryAt().Unix()

	result, err := q.scripts.failJob.Run(ctx, q.client, []string{processingKey, deadLetterKey, delayedKey},
		time.Now().Unix(), job.Error, nextRetry).Text()
	if err != nil {
		return fmt.Errorf("failed to fail job: %w", err)
	}

	if result == "dead_letter" {
		job.Status = JobStatusDeadLetter
	} else {
		job.Status = JobStatusScheduled
	}
	job.Attempts++
	job.UpdatedAt = time.Now()
	job.Version++

	return nil
}

// GetJob retrieves a job from processing (for heartbeat/monitoring)
func (q *RedisQueue) GetJob(ctx context.Context, workerID string) (*Job, error) {
	processingKey := q.keyPrefix + ":processing:" + workerID
	data, err := q.client.HGet(ctx, processingKey, "data").Text()
	if err == redis.Nil {
		return nil, ErrJobNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get job: %w", err)
	}

	var job Job
	if err := json.Unmarshal([]byte(data), &job); err != nil {
		return nil, fmt.Errorf("failed to unmarshal job: %w", err)
	}
	return &job, nil
}

// MoveDelayedToPending moves jobs from delayed to pending queue
func (q *RedisQueue) MoveDelayedToPending(ctx context.Context, batchSize int) (int, error) {
	delayedKey := q.keyPrefix + ":delayed"
	pendingKey := q.keyPrefix + ":pending"
	now := time.Now().Unix()

	count, err := q.scripts.moveToPending.Run(ctx, q.client, []string{delayedKey, pendingKey}, now, batchSize).Int()
	if err != nil {
		return 0, fmt.Errorf("failed to move delayed jobs: %w", err)
	}
	return count, nil
}

// GetStats returns queue statistics
func (q *RedisQueue) GetStats(ctx context.Context) (*QueueStats, error) {
	pendingKey := q.keyPrefix + ":pending"
	delayedKey := q.keyPrefix + ":delayed"
	deadLetterKey := q.keyPrefix + ":dead_letter"

	// Count pending
	pendingCount, err := q.client.ZCard(ctx, pendingKey).Result()
	if err != nil {
		return nil, err
	}

	// Count delayed
	scheduledCount, err := q.client.ZCard(ctx, delayedKey).Result()
	if err != nil {
		return nil, err
	}

	// Count dead letter
	deadLetterCount, err := q.client.LLen(ctx, deadLetterKey).Result()
	if err != nil {
		return nil, err
	}

	// Get oldest pending
	var oldestPending *time.Time
	oldest, err := q.client.ZRange(ctx, pendingKey, 0, 0).Result()
	if err == nil && len(oldest) > 0 {
		var job Job
		if json.Unmarshal([]byte(oldest[0]), &job) == nil {
			oldestPending = &job.CreatedAt
		}
	}

	// Note: processing and completed counts would need separate tracking
	// or scanning all worker processing keys

	return &QueueStats{
		PendingCount:    pendingCount,
		ScheduledCount:  scheduledCount,
		DeadLetterCount: deadLetterCount,
		OldestPending:   oldestPending,
	}, nil
}

// RequeueDeadLetter moves a job from DLQ back to pending
func (q *RedisQueue) RequeueDeadLetter(ctx context.Context, jobID string) error {
	deadLetterKey := q.keyPrefix + ":dead_letter"
	pendingKey := q.keyPrefix + ":pending"

	// Find and remove from DLQ (simplified - would need scan in production)
	jobs, err := q.client.LRange(ctx, deadLetterKey, 0, -1).Result()
	if err != nil {
		return err
	}

	for _, jobData := range jobs {
		var job Job
		if json.Unmarshal([]byte(jobData), &job) == nil && job.ID == jobID {
			job.Status = JobStatusPending
			job.Attempts = 0
			job.Error = ""
			job.UpdatedAt = time.Now()
			job.Version++

			newData, _ := json.Marshal(job)
			score := float64(-job.Priority*1000000) + float64(job.UpdatedAt.UnixNano())/1e9

			pipe := q.client.TxPipeline()
			pipe.LRem(ctx, deadLetterKey, 1, jobData)
			pipe.ZAdd(ctx, pendingKey, redis.Z{Score: score, Member: newData})
			_, err = pipe.Exec(ctx)
			return err
		}
	}

	return ErrJobNotFound
}

// Errors
var (
	ErrJobNotFound = &QueueError{Code: "JOB_NOT_FOUND", Message: "Job not found"}
)

type QueueError struct {
	Code    string
	Message string
}

func (e *QueueError) Error() string {
	return e.Message
}

// MockQueue for testing
type MockQueue struct {
	jobs       map[string]*Job
	pending    []*Job
	processing map[string]*Job
	deadLetter []*Job
	mu         sync.RWMutex
}

func NewMockQueue() *MockQueue {
	return &MockQueue{
		jobs:       make(map[string]*Job),
		pending:    make([]*Job, 0),
		processing: make(map[string]*Job),
		deadLetter: make([]*Job, 0),
	}
}

func (m *MockQueue) Enqueue(ctx context.Context, job *Job) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if job.ID == "" {
		job.ID = uuid.New().String()
	}
	job.CreatedAt = time.Now()
	job.UpdatedAt = time.Now()
	job.Status = JobStatusPending
	if job.MaxAttempts == 0 {
		job.MaxAttempts = 3
	}
	if job.RetryPolicy.MaxAttempts == 0 {
		job.RetryPolicy = DefaultRetryPolicy()
	}
	job.Version = 1

	m.jobs[job.ID] = job
	m.pending = append(m.pending, job)
	return nil
}

func (m *MockQueue) Claim(ctx context.Context, workerID string) (*Job, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if len(m.pending) == 0 {
		return nil, nil
	}

	job := m.pending[0]
	m.pending = m.pending[1:]

	job.Status = JobStatusProcessing
	now := time.Now()
	job.StartedAt = &now
	job.UpdatedAt = now

	m.processing[workerID] = job
	return job, nil
}

func (m *MockQueue) Heartbeat(ctx context.Context, workerID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, ok := m.processing[workerID]; !ok {
		return ErrJobNotFound
	}
	return nil
}

func (m *MockQueue) Complete(ctx context.Context, workerID string, job *Job, result *JobResult) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.processing[workerID] == nil || m.processing[workerID].ID != job.ID {
		return ErrJobNotFound
	}

	job.Status = JobStatusCompleted
	now := time.Now()
	job.CompletedAt = &now
	job.UpdatedAt = now
	job.Result = result
	job.Version++

	delete(m.processing, workerID)
	return nil
}

func (m *MockQueue) Fail(ctx context.Context, workerID string, job *Job, err error) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.processing[workerID] == nil || m.processing[workerID].ID != job.ID {
		return ErrJobNotFound
	}

	job.Error = err.Error()
	job.Attempts++
	job.UpdatedAt = time.Now()
	job.Version++

	if job.Attempts >= job.MaxAttempts {
		job.Status = JobStatusDeadLetter
		m.deadLetter = append(m.deadLetter, job)
	} else {
		job.Status = JobStatusScheduled
		// Re-add to pending with delay (simplified)
		m.pending = append(m.pending, job)
	}

	delete(m.processing, workerID)
	return nil
}

func (m *MockQueue) GetJob(ctx context.Context, workerID string) (*Job, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	job, ok := m.processing[workerID]
	if !ok {
		return nil, ErrJobNotFound
	}
	return job, nil
}

func (m *MockQueue) MoveDelayedToPending(ctx context.Context, batchSize int) (int, error) {
	// Simplified for mock
	return 0, nil
}

func (m *MockQueue) GetStats(ctx context.Context) (*QueueStats, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	return &QueueStats{
		PendingCount:    int64(len(m.pending)),
		ProcessingCount: int64(len(m.processing)),
		DeadLetterCount: int64(len(m.deadLetter)),
	}, nil
}

func (m *MockQueue) RequeueDeadLetter(ctx context.Context, jobID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	for i, job := range m.deadLetter {
		if job.ID == jobID {
			job.Status = JobStatusPending
			job.Attempts = 0
			job.Error = ""
			job.UpdatedAt = time.Now()
			job.Version++

			m.deadLetter = append(m.deadLetter[:i], m.deadLetter[i+1:]...)
			m.pending = append(m.pending, job)
			return nil
		}
	}
	return ErrJobNotFound
}