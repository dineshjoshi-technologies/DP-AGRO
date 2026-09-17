package queue

import (
	"encoding/json"
	"time"
)

// JobStatus represents the status of a job
type JobStatus string

const (
	JobStatusPending     JobStatus = "pending"
	JobStatusScheduled   JobStatus = "scheduled"
	JobStatusProcessing  JobStatus = "processing"
	JobStatusCompleted   JobStatus = "completed"
	JobStatusFailed      JobStatus = "failed"
	JobStatusDeadLetter  JobStatus = "dead_letter"
	JobStatusCancelled   JobStatus = "cancelled"
)

// RetryPolicy defines how a job should be retried
type RetryPolicy struct {
	MaxAttempts     int           `json:"max_attempts"`
	BaseDelay       time.Duration `json:"base_delay"`
	MaxDelay        time.Duration `json:"max_delay"`
	Multiplier      float64       `json:"multiplier"`
	Jitter          float64       `json:"jitter"`
	RetryableErrors []string      `json:"retryable_errors"`
}

// DefaultRetryPolicy returns a sensible default retry policy
func DefaultRetryPolicy() RetryPolicy {
	return RetryPolicy{
		MaxAttempts:     3,
		BaseDelay:       1 * time.Second,
		MaxDelay:        5 * time.Minute,
		Multiplier:      2.0,
		Jitter:          0.1,
		RetryableErrors: []string{"timeout", "unavailable", "rate_limit"},
	}
}

// JobResult represents the result of a job execution
type JobResult struct {
	Output     json.RawMessage `json:"output,omitempty"`
	Checkpoint string          `json:"checkpoint,omitempty"` // For resume capability
	Metadata   map[string]any  `json:"metadata,omitempty"`
}

// Job represents a unit of work in the queue
type Job struct {
	ID              string          `json:"id"`
	Type            string          `json:"type"`
	Payload         json.RawMessage `json:"payload"`
	Priority        int             `json:"priority"`
	Status          JobStatus       `json:"status"`
	CreatedAt       time.Time       `json:"created_at"`
	UpdatedAt       time.Time       `json:"updated_at"`
	ScheduledAt     *time.Time      `json:"scheduled_at,omitempty"`
	StartedAt       *time.Time      `json:"started_at,omitempty"`
	CompletedAt     *time.Time      `json:"completed_at,omitempty"`
	Attempts        int             `json:"attempts"`
	MaxAttempts     int             `json:"max_attempts"`
	Timeout         time.Duration   `json:"timeout"`
	RetryPolicy     RetryPolicy     `json:"retry_policy"`
	IdempotencyKey  string          `json:"idempotency_key,omitempty"`
	Result          *JobResult      `json:"result,omitempty"`
	Error           string          `json:"error,omitempty"`
	Metadata        map[string]string `json:"metadata,omitempty"`
	Version         int             `json:"version"` // Optimistic locking
}

// NextRetryAt calculates when the job should be retried
func (j *Job) NextRetryAt() time.Time {
	if j.Attempts >= j.MaxAttempts {
		return time.Time{} // No more retries
	}

	delay := j.RetryPolicy.BaseDelay
	for i := 0; i < j.Attempts; i++ {
		delay = time.Duration(float64(delay) * j.RetryPolicy.Multiplier)
		if delay > j.RetryPolicy.MaxDelay {
			delay = j.RetryPolicy.MaxDelay
			break
		}
	}

	// Add jitter
	if j.RetryPolicy.Jitter > 0 {
		jitterRange := float64(delay) * j.RetryPolicy.Jitter
		// In real implementation, use crypto/rand for proper jitter
		delay = delay + time.Duration(jitterRange*0.5) // Simplified
	}

	return time.Now().Add(delay)
}

// IsRetryableError checks if an error is retryable according to policy
func (j *Job) IsRetryableError(err error) bool {
	if err == nil {
		return false
	}
	errStr := err.Error()
	for _, retryable := range j.RetryPolicy.RetryableErrors {
		if contains(errStr, retryable) {
			return true
		}
	}
	return false
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > len(substr) && (s[:len(substr)] == substr || s[len(s)-len(substr):] == substr || indexOf(s, substr) >= 0))
}

func indexOf(s, substr string) int {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return i
		}
	}
	return -1
}

// JobEvent represents an event in the job lifecycle
type JobEvent struct {
	ID        string          `json:"id"`
	JobID     string          `json:"job_id"`
	EventType string          `json:"event_type"`
	Payload   json.RawMessage `json:"payload,omitempty"`
	CreatedAt time.Time       `json:"created_at"`
}

// JobFilter for querying jobs
type JobFilter struct {
	Status       []JobStatus `json:"status,omitempty"`
	Type         string      `json:"type,omitempty"`
	Limit        int         `json:"limit,omitempty"`
	Offset       int         `json:"offset,omitempty"`
	Since        *time.Time  `json:"since,omitempty"`
	IdempotencyKey string    `json:"idempotency_key,omitempty"`
}

// QueueStats represents queue statistics
type QueueStats struct {
	PendingCount    int64 `json:"pending_count"`
	ProcessingCount int64 `json:"processing_count"`
	ScheduledCount  int64 `json:"scheduled_count"`
	CompletedCount  int64 `json:"completed_count"`
	FailedCount     int64 `json:"failed_count"`
	DeadLetterCount int64 `json:"dead_letter_count"`
	OldestPending   *time.Time `json:"oldest_pending,omitempty"`
}