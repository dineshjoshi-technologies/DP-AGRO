package router

import (
	"sync"
	"time"
)

// CostTracker tracks costs and latencies per model/provider
type CostTracker struct {
	mu       sync.RWMutex
	requests []RequestRecord
	stats    CostStats
}

type RequestRecord struct {
	Timestamp       time.Time
	Model           string
	Provider        string
	EstimatedTokens int
	ActualTokens    int
	Latency         time.Duration
	Error           error
}

type CostStats struct {
	TotalRequests     int64
	TotalTokens       int64
	TotalCost         float64
	AvgLatency        time.Duration
	ByModel           map[string]ModelStats
	ByProvider        map[string]ProviderStats
	Errors            int64
	LastUpdated       time.Time
}

type ModelStats struct {
	Requests     int64
	Tokens       int64
	Cost         float64
	AvgLatency   time.Duration
	ErrorRate    float64
	P50Latency   time.Duration
	P95Latency   time.Duration
	P99Latency   time.Duration
}

type ProviderStats struct {
	Requests  int64
	Tokens    int64
	Cost      float64
	Errors    int64
	ErrorRate float64
}

// NewCostTracker creates a new cost tracker
func NewCostTracker() *CostTracker {
	return &CostTracker{
		requests: make([]RequestRecord, 0, 10000),
		stats: CostStats{
			ByModel:    make(map[string]ModelStats),
			ByProvider: make(map[string]ProviderStats),
		},
	}
}

// Record records a request
func (c *CostTracker) Record(model, provider string, estimatedTokens, actualTokens int, latency time.Duration, err error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	record := RequestRecord{
		Timestamp:       time.Now(),
		Model:           model,
		Provider:        provider,
		EstimatedTokens: estimatedTokens,
		ActualTokens:    actualTokens,
		Latency:         latency,
		Error:           err,
	}

	c.requests = append(c.requests, record)
	if len(c.requests) > 10000 {
		c.requests = c.requests[len(c.requests)-10000:]
	}

	c.updateStats(record)
}

func (c *CostTracker) updateStats(record RequestRecord) {
	c.stats.TotalRequests++
	c.stats.TotalTokens += int64(record.ActualTokens)
	c.stats.LastUpdated = record.Timestamp

	// Calculate cost (simplified - would use actual model pricing)
	cost := c.estimateCost(record.Model, record.ActualTokens)
	c.stats.TotalCost += cost

	// Update running average latency
	if c.stats.TotalRequests == 1 {
		c.stats.AvgLatency = record.Latency
	} else {
		c.stats.AvgLatency = time.Duration(
			(int64(c.stats.AvgLatency)*(c.stats.TotalRequests-1) + int64(record.Latency)) / c.stats.TotalRequests,
		)
	}

	if record.Error != nil {
		c.stats.Errors++
	}

	// Update model stats
	ms := c.stats.ByModel[record.Model]
	ms.Requests++
	ms.Tokens += int64(record.ActualTokens)
	ms.Cost += cost
	if ms.Requests == 1 {
		ms.AvgLatency = record.Latency
	} else {
		ms.AvgLatency = time.Duration(
			(int64(ms.AvgLatency)*(ms.Requests-1) + int64(record.Latency)) / ms.Requests,
		)
	}
	ms.ErrorRate = float64(c.countErrorsForModel(record.Model)) / float64(ms.Requests)
	c.stats.ByModel[record.Model] = ms

	// Update provider stats
	ps := c.stats.ByProvider[record.Provider]
	ps.Requests++
	ps.Tokens += int64(record.ActualTokens)
	ps.Cost += cost
	ps.Errors += c.boolToInt(record.Error != nil)
	ps.ErrorRate = float64(ps.Errors) / float64(ps.Requests)
	c.stats.ByProvider[record.Provider] = ps
}

func (c *CostTracker) estimateCost(model string, tokens int) float64 {
	// Simplified cost estimation
	// In production, would look up actual model pricing
	costPerMillion := 1.0 // default $1/M tokens
	return float64(tokens) * costPerMillion / 1_000_000
}

func (c *CostTracker) countErrorsForModel(model string) int {
	count := 0
	for _, r := range c.requests {
		if r.Model == model && r.Error != nil {
			count++
		}
	}
	return count
}

func (c *CostTracker) boolToInt(b bool) int {
	if b {
		return 1
	}
	return 0
}

// GetStats returns current cost statistics
func (c *CostTracker) GetStats() CostStats {
	c.mu.RLock()
	defer c.mu.RUnlock()

	// Deep copy stats
	stats := c.stats
	stats.ByModel = make(map[string]ModelStats, len(c.stats.ByModel))
	for k, v := range c.stats.ByModel {
		stats.ByModel[k] = v
	}
	stats.ByProvider = make(map[string]ProviderStats, len(c.stats.ByProvider))
	for k, v := range c.stats.ByProvider {
		stats.ByProvider[k] = v
	}
	return stats
}

// GetModelStats returns stats for a specific model
func (c *CostTracker) GetModelStats(model string) (ModelStats, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	stats, ok := c.stats.ByModel[model]
	return stats, ok
}

// GetProviderStats returns stats for a specific provider
func (c *CostTracker) GetProviderStats(provider string) (ProviderStats, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	stats, ok := c.stats.ByProvider[provider]
	return stats, ok
}

// Reset clears all statistics
func (c *CostTracker) Reset() {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.requests = c.requests[:0]
	c.stats = CostStats{
		ByModel:    make(map[string]ModelStats),
		ByProvider: make(map[string]ProviderStats),
	}
}