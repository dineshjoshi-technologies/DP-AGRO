package scheduler

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/djtech/job-queue/queue"
	"github.com/google/uuid"
	"github.com/robfig/cron/v3"
)

// SchedulerConfig holds scheduler configuration
type SchedulerConfig struct {
	Enabled            bool
	CronPollInterval   time.Duration
	DelayedPollInterval time.Duration
	Timezone           string
}

// CronJob represents a recurring scheduled job
type CronJob struct {
	ID            string          `json:"id"`
	Name          string          `json:"name"`
	Schedule      string          `json:"schedule"`      // Cron expression
	JobType       string          `json:"job_type"`
	Payload       json.RawMessage `json:"payload"`
	Priority      int             `json:"priority"`
	MaxAttempts   int             `json:"max_attempts"`
	Timeout       time.Duration   `json:"timeout"`
	RetryPolicy   queue.RetryPolicy `json:"retry_policy"`
	Timezone      string          `json:"timezone,omitempty"`
	Enabled       bool            `json:"enabled"`
	NextRun       *time.Time      `json:"next_run,omitempty"`
	LastRun       *time.Time      `json:"last_run,omitempty"`
	RunCount      int64           `json:"run_count"`
	EntryID       cron.EntryID    `json:"-"` // Internal cron entry ID
}

// Scheduler manages cron jobs and delayed job promotion
type Scheduler struct {
	config      SchedulerConfig
	queue       queue.Queue
	cron        *cron.Cron
	cronJobs    map[string]*CronJob
	mu          sync.RWMutex
	ctx         context.Context
	cancel      context.CancelFunc
	wg          sync.WaitGroup
	running     bool
	delayedMover *delayedMover
}

// delayedMover moves jobs from delayed queue to pending queue
type delayedMover struct {
	queue     queue.Queue
	interval  time.Duration
	batchSize int
	ctx       context.Context
	cancel    context.CancelFunc
	wg        sync.WaitGroup
	running   bool
}

// NewScheduler creates a new scheduler
func NewScheduler(config SchedulerConfig, q queue.Queue) *Scheduler {
	if config.CronPollInterval == 0 {
		config.CronPollInterval = 10 * time.Second
	}
	if config.DelayedPollInterval == 0 {
		config.DelayedPollInterval = 5 * time.Second
	}
	if config.Timezone == "" {
		config.Timezone = "UTC"
	}

	loc, _ := time.LoadLocation(config.Timezone)
	c := cron.New(cron.WithLocation(loc), cron.WithSeconds())

	ctx, cancel := context.WithCancel(context.Background())

	s := &Scheduler{
		config:   config,
		queue:    q,
		cron:     c,
		cronJobs: make(map[string]*CronJob),
		ctx:      ctx,
		cancel:   cancel,
	}

	s.delayedMover = &delayedMover{
		queue:     q,
		interval:  config.DelayedPollInterval,
		batchSize: 100,
		ctx:       ctx,
		cancel:    cancel,
	}

	return s
}

// Start begins the scheduler
func (s *Scheduler) Start() error {
	s.mu.Lock()
	if s.running {
		s.mu.Unlock()
		return fmt.Errorf("scheduler already running")
	}
	s.running = true
	s.mu.Unlock()

	if s.config.Enabled {
		s.cron.Start()
		s.startDelayedMover()
		log.Println("Scheduler started")
	}
	return nil
}

// Stop gracefully stops the scheduler
func (s *Scheduler) Stop() error {
	s.mu.Lock()
	if !s.running {
		s.mu.Unlock()
		return nil
	}
	s.running = false
	s.mu.Unlock()

	s.cron.Stop()
	s.delayedMover.stop()
	s.cancel()
	s.wg.Wait()
	log.Println("Scheduler stopped")
	return nil
}

// AddCronJob adds a new cron job
func (s *Scheduler) AddCronJob(job *CronJob) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if job.ID == "" {
		job.ID = uuid.New().String()
	}
	if job.MaxAttempts == 0 {
		job.MaxAttempts = 3
	}
	if job.RetryPolicy.MaxAttempts == 0 {
		job.RetryPolicy = queue.DefaultRetryPolicy()
	}

	entryID, err := s.cron.AddFunc(job.Schedule, func() {
		s.executeCronJob(job)
	})
	if err != nil {
		return fmt.Errorf("failed to add cron job: %w", err)
	}

	job.EntryID = entryID
	job.Enabled = true
	s.updateNextRun(job)
	s.cronJobs[job.ID] = job

	log.Printf("Added cron job: %s (%s) with schedule %s", job.Name, job.ID, job.Schedule)
	return nil
}

// RemoveCronJob removes a cron job
func (s *Scheduler) RemoveCronJob(id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	job, ok := s.cronJobs[id]
	if !ok {
		return fmt.Errorf("cron job not found: %s", id)
	}

	s.cron.Remove(job.EntryID)
	delete(s.cronJobs, id)
	log.Printf("Removed cron job: %s (%s)", job.Name, id)
	return nil
}

// EnableCronJob enables or disables a cron job
func (s *Scheduler) EnableCronJob(id string, enabled bool) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	job, ok := s.cronJobs[id]
	if !ok {
		return fmt.Errorf("cron job not found: %s", id)
	}

	if job.Enabled == enabled {
		return nil
	}

	if enabled {
		entryID, err := s.cron.AddFunc(job.Schedule, func() {
			s.executeCronJob(job)
		})
		if err != nil {
			return fmt.Errorf("failed to re-enable cron job: %w", err)
		}
		job.EntryID = entryID
	} else {
		s.cron.Remove(job.EntryID)
		job.EntryID = 0
	}

	job.Enabled = enabled
	s.updateNextRun(job)
	return nil
}

// GetCronJob returns a cron job by ID
func (s *Scheduler) GetCronJob(id string) (*CronJob, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	job, ok := s.cronJobs[id]
	return job, ok
}

// ListCronJobs returns all cron jobs
func (s *Scheduler) ListCronJobs() []*CronJob {
	s.mu.RLock()
	defer s.mu.RUnlock()

	jobs := make([]*CronJob, 0, len(s.cronJobs))
	for _, job := range s.cronJobs {
		jobs = append(jobs, job)
	}
	return jobs
}

// ScheduleJob schedules a one-time job for future execution
func (s *Scheduler) ScheduleJob(ctx context.Context, job *queue.Job, runAt time.Time) error {
	job.ScheduledAt = &runAt
	job.Status = queue.JobStatusScheduled
	return s.queue.Enqueue(ctx, job)
}

// executeCronJob creates and enqueues a job instance from a cron job
func (s *Scheduler) executeCronJob(cronJob *CronJob) {
	job := &queue.Job{
		ID:            uuid.New().String(),
		Type:          cronJob.JobType,
		Payload:       cronJob.Payload,
		Priority:      cronJob.Priority,
		MaxAttempts:   cronJob.MaxAttempts,
		Timeout:       cronJob.Timeout,
		RetryPolicy:   cronJob.RetryPolicy,
		IdempotencyKey: fmt.Sprintf("cron-%s-%d", cronJob.ID, time.Now().Unix()),
		Metadata: map[string]string{
			"cron_job_id": cronJob.ID,
			"cron_job_name": cronJob.Name,
		},
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := s.queue.Enqueue(ctx, job); err != nil {
		log.Printf("Failed to enqueue cron job %s: %v", cronJob.ID, err)
		return
	}

	now := time.Now()
	cronJob.LastRun = &now
	cronJob.RunCount++
	s.updateNextRun(cronJob)
	log.Printf("Enqueued cron job instance: %s (from cron %s)", job.ID, cronJob.ID)
}

func (s *Scheduler) updateNextRun(job *CronJob) {
	entries := s.cron.Entries()
	for _, entry := range entries {
		if entry.ID == job.EntryID {
			next := entry.Next
			job.NextRun = &next
			break
		}
	}
}

func (s *Scheduler) startDelayedMover() {
	s.delayedMover.running = true
	s.wg.Add(1)
	go s.delayedMover.run()
}

func (d *delayedMover) run() {
	defer d.wg.Done()

	ticker := time.NewTicker(d.interval)
	defer ticker.Stop()

	for {
		select {
		case <-d.ctx.Done():
			return
		case <-ticker.C:
			d.moveBatch()
		}
	}
}

func (d *delayedMover) moveBatch() {
	ctx, cancel := context.WithTimeout(d.ctx, 10*time.Second)
	defer cancel()

	count, err := d.queue.MoveDelayedToPending(ctx, d.batchSize)
	if err != nil {
		log.Printf("Delayed mover error: %v", err)
		return
	}
	if count > 0 {
		log.Printf("Moved %d jobs from delayed to pending", count)
	}
}

func (d *delayedMover) stop() {
	if d.running {
		d.running = false
		d.cancel()
		d.wg.Wait()
	}
}