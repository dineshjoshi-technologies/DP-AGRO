package billing

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/google/uuid"
)

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
	Timestamp        time.Time `json:"timestamp"`
}

// TrackerConfig holds billing tracker configuration
type TrackerConfig struct {
	PricePerCPUSecond      float64 `json:"price_per_cpu_second"`
	PricePerMemoryGBSecond float64 `json:"price_per_memory_gb_second"`
	PricePerLLMToken       float64 `json:"price_per_llm_token"`
	WebhookURL             string  `json:"webhook_url"`
	Currency               string  `json:"currency"`
	Enabled                bool    `json:"enabled"`
}

// Tracker tracks billing for agent executions
type Tracker struct {
	config     *TrackerConfig
	records    []BillingRecord
	mu         sync.RWMutex
	httpClient *http.Client
	closed     bool
}

// BillingRecord represents a billing record
type BillingRecord struct {
	ID              string    `json:"id"`
	ExecutionID     string    `json:"execution_id"`
	AgentID         string    `json:"agent_id"`
	DurationSeconds float64   `json:"duration_seconds"`
	CPUSeconds      float64   `json:"cpu_seconds"`
	MemoryGBSeconds float64   `json:"memory_gb_seconds"`
	LLMTokensIn     int64     `json:"llm_tokens_in"`
	LLMTokensOut    int64     `json:"llm_tokens_out"`
	EstimatedCost   float64   `json:"estimated_cost"`
	Currency        string    `json:"currency"`
	Timestamp       time.Time `json:"timestamp"`
	WebhookSent     bool      `json:"webhook_sent"`
	WebhookError    string    `json:"webhook_error,omitempty"`
}

// Stats returns billing statistics
type Stats struct {
	TotalExecutions    int64    `json:"total_executions"`
	TotalCPUSeconds    float64  `json:"total_cpu_seconds"`
	TotalMemoryGBSeconds float64 `json:"total_memory_gb_seconds"`
	TotalLLMTokensIn   int64    `json:"total_llm_tokens_in"`
	TotalLLMTokensOut  int64    `json:"total_llm_tokens_out"`
	TotalCost          float64  `json:"total_cost"`
	Currency           string   `json:"currency"`
	ByAgent            map[string]AgentStats `json:"by_agent"`
	LastUpdated        time.Time `json:"last_updated"`
}

// AgentStats contains stats per agent
type AgentStats struct {
	Executions       int64   `json:"executions"`
	CPUSeconds       float64 `json:"cpu_seconds"`
	MemoryGBSeconds  float64 `json:"memory_gb_seconds"`
	LLMTokensIn      int64   `json:"llm_tokens_in"`
	LLMTokensOut     int64   `json:"llm_tokens_out"`
	Cost             float64 `json:"cost"`
}

// NewTracker creates a new billing tracker
func NewTracker(config *TrackerConfig) *Tracker {
	// Parse string prices to float64
	// In production, would use decimal for precision
	t := &Tracker{
		config: config,
		records: make([]BillingRecord, 0, 10000),
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}

	// Start webhook sender routine if webhook configured
	if config.WebhookURL != "" && config.Enabled {
		go t.webhookSender()
	}

	return t
}

// Enabled returns whether billing is enabled
func (t *Tracker) Enabled() bool {
	return t.config.Enabled
}

// Record records a billing event
func (t *Tracker) Record(info *BillingInfo) {
	if !t.config.Enabled {
		return
	}

	record := BillingRecord{
		ID:              "bill-" + uuid.New().String()[:12],
		ExecutionID:     info.ExecutionID,
		AgentID:         info.AgentID,
		DurationSeconds: info.DurationSeconds,
		CPUSeconds:      info.CPUSeconds,
		MemoryGBSeconds: info.MemoryGBSeconds,
		LLMTokensIn:     info.LLMTokensIn,
		LLMTokensOut:    info.LLMTokensOut,
		EstimatedCost:   info.EstimatedCost,
		Currency:        info.Currency,
		Timestamp:       time.Now(),
	}

	t.mu.Lock()
	t.records = append(t.records, record)
	// Keep only last 10000 records in memory
	if len(t.records) > 10000 {
		t.records = t.records[len(t.records)-10000:]
	}
	t.mu.Unlock()

	// Send webhook asynchronously
	if t.config.WebhookURL != "" {
		go t.sendWebhook(record)
	}
}

// sendWebhook sends a billing record to the webhook URL
func (t *Tracker) sendWebhook(record BillingRecord) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	body, err := json.Marshal(record)
	if err != nil {
		log.Printf("Billing webhook: failed to marshal record: %v", err)
		t.updateWebhookStatus(record.ID, false, err.Error())
		return
	}

	req, err := http.NewRequestWithContext(ctx, "POST", t.config.WebhookURL, bytes.NewReader(body))
	if err != nil {
		log.Printf("Billing webhook: failed to create request: %v", err)
		t.updateWebhookStatus(record.ID, false, err.Error())
		return
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := t.httpClient.Do(req)
	if err != nil {
		log.Printf("Billing webhook: request failed: %v", err)
		t.updateWebhookStatus(record.ID, false, err.Error())
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		err := fmt.Errorf("webhook returned status %d", resp.StatusCode)
		log.Printf("Billing webhook: %v", err)
		t.updateWebhookStatus(record.ID, false, err.Error())
		return
	}

	t.updateWebhookStatus(record.ID, true, "")
}

// updateWebhookStatus updates the webhook status for a record
func (t *Tracker) updateWebhookStatus(recordID string, sent bool, errMsg string) {
	t.mu.Lock()
	defer t.mu.Unlock()

	for i := range t.records {
		if t.records[i].ID == recordID {
			t.records[i].WebhookSent = sent
			if !sent {
				t.records[i].WebhookError = errMsg
			}
			break
		}
	}
}

// webhookSender periodically retries failed webhooks
func (t *Tracker) webhookSender() {
	ticker := time.NewTicker(1 * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			t.retryFailedWebhooks()
		}
	}
}

// retryFailedWebhooks retries failed webhooks
func (t *Tracker) retryFailedWebhooks() {
	t.mu.RLock()
	var failed []BillingRecord
	for _, r := range t.records {
		if !r.WebhookSent && r.WebhookError != "" {
			failed = append(failed, r)
		}
	}
	t.mu.RUnlock()

	for _, record := range failed {
		go t.sendWebhook(record)
	}
}

// Stats returns billing statistics
func (t *Tracker) Stats() Stats {
	t.mu.RLock()
	defer t.mu.RUnlock()

	stats := Stats{
		Currency: t.config.Currency,
		ByAgent:  make(map[string]AgentStats),
		LastUpdated: time.Now(),
	}

	for _, r := range t.records {
		stats.TotalExecutions++
		stats.TotalCPUSeconds += r.CPUSeconds
		stats.TotalMemoryGBSeconds += r.MemoryGBSeconds
		stats.TotalLLMTokensIn += r.LLMTokensIn
		stats.TotalLLMTokensOut += r.LLMTokensOut
		stats.TotalCost += r.EstimatedCost

		agentStats := stats.ByAgent[r.AgentID]
		agentStats.Executions++
		agentStats.CPUSeconds += r.CPUSeconds
		agentStats.MemoryGBSeconds += r.MemoryGBSeconds
		agentStats.LLMTokensIn += r.LLMTokensIn
		agentStats.LLMTokensOut += r.LLMTokensOut
		agentStats.Cost += r.EstimatedCost
		stats.ByAgent[r.AgentID] = agentStats
	}

	return stats
}

// GetRecords returns billing records (with optional filter)
func (t *Tracker) GetRecords(agentID string, since time.Time, limit int) []BillingRecord {
	t.mu.RLock()
	defer t.mu.RUnlock()

	result := make([]BillingRecord, 0)
	for i := len(t.records) - 1; i >= 0 && (limit <= 0 || len(result) < limit); i-- {
		r := t.records[i]
		if agentID != "" && r.AgentID != agentID {
			continue
		}
		if !since.IsZero() && r.Timestamp.Before(since) {
			continue
		}
		result = append(result, r)
	}

	return result
}

// Close closes the tracker
func (t *Tracker) Close() error {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.closed = true
	return nil
}