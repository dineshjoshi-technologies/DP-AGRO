package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// Config holds the gateway configuration
type Config struct {
	AllowedModels     []string          `json:"allowed_models"`
	TokenBudgets      map[string]int    `json:"token_budgets"`      // agent_id -> daily token limit
	RateLimits        map[string]int    `json:"rate_limits"`        // agent_id -> requests per minute
	PIIPatterns       []string          `json:"pii_patterns"`       // regex patterns for PII
	UpstreamEndpoints map[string]string `json:"upstream_endpoints"` // model -> endpoint URL
	Port              string            `json:"port"`
}

// TokenBucket implements a simple token bucket for rate limiting
type TokenBucket struct {
	mu       sync.Mutex
	tokens   float64
	maxTokens float64
	refillRate float64 // tokens per second
	lastRefill time.Time
}

func NewTokenBucket(ratePerMinute int) *TokenBucket {
	return &TokenBucket{
		tokens:       float64(ratePerMinute),
		maxTokens:    float64(ratePerMinute),
		refillRate:   float64(ratePerMinute) / 60.0,
		lastRefill:   time.Now(),
	}
}

func (tb *TokenBucket) Take() bool {
	tb.mu.Lock()
	defer tb.mu.Unlock()

	now := time.Now()
	elapsed := now.Sub(tb.lastRefill).Seconds()
	tb.tokens = min(tb.maxTokens, tb.tokens+elapsed*tb.refillRate)
	tb.lastRefill = now

	if tb.tokens >= 1 {
		tb.tokens--
		return true
	}
	return false
}

// PIIRedactor handles PII detection and redaction
type PIIRedactor struct {
	patterns []*regexp.Regexp
}

func NewPIIRedactor(patterns []string) *PIIRedactor {
	var compiled []*regexp.Regexp
	for _, p := range patterns {
		if re, err := regexp.Compile(p); err == nil {
			compiled = append(compiled, re)
		} else {
			log.Printf("Warning: invalid PII pattern %q: %v", p, err)
		}
	}
	return &PIIRedactor{patterns: compiled}
}

func (r *PIIRedactor) Redact(text string) string {
	result := text
	for _, re := range r.patterns {
		result = re.ReplaceAllString(result, "[REDACTED]")
	}
	return result
}

func (r *PIIRedactor) ContainsPII(text string) bool {
	for _, re := range r.patterns {
		if re.MatchString(text) {
			return true
		}
	}
	return false
}

// TokenCounter estimates token count (rough approximation)
type TokenCounter struct{}

func (tc *TokenCounter) Count(text string) int {
	// Rough approximation: ~4 characters per token for English
	return len(text) / 4
}

// AuditLogger logs all gateway activity
type AuditLogger struct {
	mu    sync.Mutex
	file  *os.File
	encoder *json.Encoder
}

func NewAuditLogger(path string) (*AuditLogger, error) {
	f, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return nil, err
	}
	return &AuditLogger{
		file:    f,
		encoder: json.NewEncoder(f),
	}, nil
}

func (al *AuditLogger) Log(entry AuditEntry) {
	al.mu.Lock()
	defer al.mu.Unlock()
	al.encoder.Encode(entry)
}

func (al *AuditLogger) Close() error {
	return al.file.Close()
}

// AuditEntry represents a single audit log entry
type AuditEntry struct {
	Timestamp    time.Time         `json:"timestamp"`
	RequestID    string            `json:"request_id"`
	AgentID      string            `json:"agent_id"`
	Model        string            `json:"model"`
	Action       string            `json:"action"` // allow, deny, redact
	TokensIn     int               `json:"tokens_in"`
	TokensOut    int               `json:"tokens_out"`
	LatencyMs    int64             `json:"latency_ms"`
	Error        string            `json:"error,omitempty"`
	Metadata     map[string]string `json:"metadata,omitempty"`
}

// LLMRequest represents an incoming LLM API request
type LLMRequest struct {
	Model       string          `json:"model"`
	Messages    []Message       `json:"messages"`
	Tools       []Tool          `json:"tools,omitempty"`
	ToolChoice  interface{}     `json:"tool_choice,omitempty"`
	Temperature float64         `json:"temperature,omitempty"`
	MaxTokens   int             `json:"max_tokens,omitempty"`
	Stream      bool            `json:"stream,omitempty"`
	Metadata    json.RawMessage `json:"metadata,omitempty"`
}

type Message struct {
	Role       string          `json:"role"`
	Content    string          `json:"content"`
	ToolCalls  []ToolCall      `json:"tool_calls,omitempty"`
	ToolCallID string          `json:"tool_call_id,omitempty"`
	Name       string          `json:"name,omitempty"`
}

type Tool struct {
	Type     string       `json:"type"`
	Function ToolFunction `json:"function"`
}

type ToolFunction struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	Parameters  json.RawMessage `json:"parameters"`
}

type ToolCall struct {
	ID       string          `json:"id"`
	Type     string          `json:"type"`
	Function ToolCallFunction `json:"function"`
}

type ToolCallFunction struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

// LLMResponse represents an LLM API response
type LLMResponse struct {
	ID      string   `json:"id"`
	Object  string   `json:"object"`
	Created int64    `json:"created"`
	Model   string   `json:"model"`
	Choices []Choice `json:"choices"`
	Usage   Usage    `json:"usage"`
}

type Choice struct {
	Index        int     `json:"index"`
	Message      Message `json:"message"`
	FinishReason string  `json:"finish_reason"`
}

type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// Gateway holds all gateway state
type Gateway struct {
	config       *Config
	piiRedactor  *PIIRedactor
	tokenCounter *TokenCounter
	auditLogger  *AuditLogger
	rateLimiters map[string]*TokenBucket
	tokenBudgets map[string]*TokenBudget
	upstream     *http.Client
	mu           sync.RWMutex
}

type TokenBudget struct {
	mu           sync.Mutex
	dailyLimit   int
	usedToday    int
	lastReset    time.Time
}

func NewTokenBudget(limit int) *TokenBudget {
	return &TokenBudget{
		dailyLimit: limit,
		lastReset:  time.Now().Truncate(24 * time.Hour),
	}
}

func (tb *TokenBudget) CheckAndConsume(tokens int) bool {
	tb.mu.Lock()
	defer tb.mu.Unlock()

	now := time.Now().Truncate(24 * time.Hour)
	if now.After(tb.lastReset) {
		tb.usedToday = 0
		tb.lastReset = now
	}

	if tb.usedToday+tokens > tb.dailyLimit {
		return false
	}
	tb.usedToday += tokens
	return true
}

func (tb *TokenBudget) Remaining() int {
	tb.mu.Lock()
	defer tb.mu.Unlock()

	now := time.Now().Truncate(24 * time.Hour)
	if now.After(tb.lastReset) {
		return tb.dailyLimit
	}
	return tb.dailyLimit - tb.usedToday
}

// NewGateway creates a new gateway instance
func NewGateway(config *Config) (*Gateway, error) {
	auditLogger, err := NewAuditLogger("/var/log/llm-gateway-audit.jsonl")
	if err != nil {
		return nil, fmt.Errorf("failed to create audit logger: %w", err)
	}

	g := &Gateway{
		config:       config,
		piiRedactor:  NewPIIRedactor(config.PIIPatterns),
		tokenCounter: &TokenCounter{},
		auditLogger:  auditLogger,
		rateLimiters: make(map[string]*TokenBucket),
		tokenBudgets: make(map[string]*TokenBudget),
		upstream: &http.Client{
			Timeout: 120 * time.Second,
		},
	}

	// Initialize rate limiters and token budgets
	for agentID, rate := range config.RateLimits {
		g.rateLimiters[agentID] = NewTokenBucket(rate)
	}
	for agentID, budget := range config.TokenBudgets {
		g.tokenBudgets[agentID] = NewTokenBudget(budget)
	}

	return g, nil
}

func (g *Gateway) getRateLimiter(agentID string) *TokenBucket {
	g.mu.RLock()
	rl, exists := g.rateLimiters[agentID]
	g.mu.RUnlock()

	if !exists {
		g.mu.Lock()
		rl = NewTokenBucket(60) // default 60/min
		g.rateLimiters[agentID] = rl
		g.mu.Unlock()
	}
	return rl
}

func (g *Gateway) getTokenBudget(agentID string) *TokenBudget {
	g.mu.RLock()
	tb, exists := g.tokenBudgets[agentID]
	g.mu.RUnlock()

	if !exists {
		g.mu.Lock()
		tb = NewTokenBudget(100000) // default 100k/day
		g.tokenBudgets[agentID] = tb
		g.mu.Unlock()
	}
	return tb
}

func (g *Gateway) isModelAllowed(model string) bool {
	for _, m := range g.config.AllowedModels {
		if m == "*" || m == model {
			return true
		}
	}
	return false
}

func (g *Gateway) getUpstreamURL(model string) string {
	if url, ok := g.config.UpstreamEndpoints[model]; ok {
		return url
	}
	// Default to OpenAI-compatible endpoint
	return "https://api.openai.com/v1"
}

// ChatCompletions handles the /v1/chat/completions endpoint
func (g *Gateway) ChatCompletions(c *gin.Context) {
	startTime := time.Now()
	requestID := uuid.New().String()

	// Extract agent ID from header (set by sandbox runtime)
	agentID := c.GetHeader("X-Agent-ID")
	if agentID == "" {
		agentID = "unknown"
	}

	var req LLMRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		g.logAudit(AuditEntry{
			Timestamp: startTime,
			RequestID: requestID,
			AgentID:   agentID,
			Model:     req.Model,
			Action:    "deny",
			Error:     fmt.Sprintf("invalid request: %v", err),
			LatencyMs: time.Since(startTime).Milliseconds(),
		})
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request"})
		return
	}

	// Check model allowlist
	if !g.isModelAllowed(req.Model) {
		g.logAudit(AuditEntry{
			Timestamp: startTime,
			RequestID: requestID,
			AgentID:   agentID,
			Model:     req.Model,
			Action:    "deny",
			Error:     "model not allowed",
			LatencyMs: time.Since(startTime).Milliseconds(),
		})
		c.JSON(http.StatusForbidden, gin.H{"error": "model not allowed"})
		return
	}

	// Rate limiting
	rl := g.getRateLimiter(agentID)
	if !rl.Take() {
		g.logAudit(AuditEntry{
			Timestamp: startTime,
			RequestID: requestID,
			AgentID:   agentID,
			Model:     req.Model,
			Action:    "deny",
			Error:     "rate limit exceeded",
			LatencyMs: time.Since(startTime).Milliseconds(),
		})
		c.JSON(http.StatusTooManyRequests, gin.H{"error": "rate limit exceeded"})
		return
	}

	// Estimate input tokens
	inputText := ""
	for _, msg := range req.Messages {
		inputText += msg.Content + " "
	}
	estimatedInputTokens := g.tokenCounter.Count(inputText)

	// Check token budget
	tb := g.getTokenBudget(agentID)
	if !tb.CheckAndConsume(estimatedInputTokens + req.MaxTokens) {
		g.logAudit(AuditEntry{
			Timestamp: startTime,
			RequestID: requestID,
			AgentID:   agentID,
			Model:     req.Model,
			Action:    "deny",
			Error:     "token budget exceeded",
			TokensIn:  estimatedInputTokens,
			LatencyMs: time.Since(startTime).Milliseconds(),
		})
		c.JSON(http.StatusForbidden, gin.H{"error": "token budget exceeded"})
		return
	}

	// PII detection and redaction on input
	hasPII := false
	for i := range req.Messages {
		if g.piiRedactor.ContainsPII(req.Messages[i].Content) {
			hasPII = true
			req.Messages[i].Content = g.piiRedactor.Redact(req.Messages[i].Content)
		}
	}

	// Forward to upstream
	upstreamURL := g.getUpstreamURL(req.Model) + "/chat/completions"
	reqBody, _ := json.Marshal(req)

	upstreamReq, err := http.NewRequestWithContext(c.Request.Context(), "POST", upstreamURL, strings.NewReader(string(reqBody)))
	if err != nil {
		g.logAudit(AuditEntry{
			Timestamp: startTime,
			RequestID: requestID,
			AgentID:   agentID,
			Model:     req.Model,
			Action:    "deny",
			Error:     fmt.Sprintf("upstream request error: %v", err),
			LatencyMs: time.Since(startTime).Milliseconds(),
		})
		c.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
		return
	}

	// Copy headers
	for k, v := range c.Request.Header {
		if k != "Host" && k != "Content-Length" {
			upstreamReq.Header[k] = v
		}
	}
	upstreamReq.Header.Set("Content-Type", "application/json")

	// Execute upstream request
	resp, err := g.upstream.Do(upstreamReq)
	if err != nil {
		g.logAudit(AuditEntry{
			Timestamp: startTime,
			RequestID: requestID,
			AgentID:   agentID,
			Model:     req.Model,
			Action:    "deny",
			Error:     fmt.Sprintf("upstream error: %v", err),
			LatencyMs: time.Since(startTime).Milliseconds(),
		})
		c.JSON(http.StatusBadGateway, gin.H{"error": "upstream error"})
		return
	}
	defer resp.Body.Close()

	// Read response
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		g.logAudit(AuditEntry{
			Timestamp: startTime,
			RequestID: requestID,
			AgentID:   agentID,
			Model:     req.Model,
			Action:    "deny",
			Error:     fmt.Sprintf("read response error: %v", err),
			LatencyMs: time.Since(startTime).Milliseconds(),
		})
		c.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
		return
	}

	// Parse response to check for PII in output
	var llmResp LLMResponse
	if err := json.Unmarshal(respBody, &llmResp); err == nil {
		// Check and redact PII in response
		for i := range llmResp.Choices {
			if g.piiRedactor.ContainsPII(llmResp.Choices[i].Message.Content) {
				hasPII = true
				llmResp.Choices[i].Message.Content = g.piiRedactor.Redact(llmResp.Choices[i].Message.Content)
			}
		}
		// Re-marshal if we redacted
		if hasPII {
			respBody, _ = json.Marshal(llmResp)
		}
	}

	// Log success
	tokensOut := 0
	if llmResp.Usage.TotalTokens > 0 {
		tokensOut = llmResp.Usage.CompletionTokens
	}

	g.logAudit(AuditEntry{
		Timestamp: startTime,
		RequestID: requestID,
		AgentID:   agentID,
		Model:     req.Model,
		Action:    "allow",
		TokensIn:  estimatedInputTokens,
		TokensOut: tokensOut,
		LatencyMs: time.Since(startTime).Milliseconds(),
		Metadata: map[string]string{
			"pii_detected": fmt.Sprintf("%v", hasPII),
			"status_code":  fmt.Sprintf("%d", resp.StatusCode),
		},
	})

	// Forward response
	c.Data(resp.StatusCode, "application/json", respBody)
}

func (g *Gateway) logAudit(entry AuditEntry) {
	g.auditLogger.Log(entry)
}

// HealthCheck returns the health status
func (g *Gateway) HealthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":       "healthy",
		"timestamp":    time.Now().Unix(),
		"version":      "0.1.0",
		"active_agents": len(g.rateLimiters),
	})
}

func (g *Gateway) Metrics(c *gin.Context) {
	g.mu.RLock()
	defer g.mu.RUnlock()

	metrics := gin.H{
		"rate_limiters": len(g.rateLimiters),
		"token_budgets": len(g.tokenBudgets),
		"agents":        gin.H{},
	}

	agents := make(map[string]gin.H)
	for id, rl := range g.rateLimiters {
		tb := g.getTokenBudget(id)
		agents[id] = gin.H{
			"token_budget_remaining": tb.Remaining(),
		}
	}
	metrics["agents"] = agents

	c.JSON(http.StatusOK, metrics)
}

func loadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}
	// Set defaults
	if cfg.Port == "" {
		cfg.Port = "8080"
	}
	if len(cfg.AllowedModels) == 0 {
		cfg.AllowedModels = []string{"gpt-4o", "claude-3.5-sonnet", "*"}
	}
	if len(cfg.PIIPatterns) == 0 {
		cfg.PIIPatterns = []string{
			`\b\d{3}-\d{2}-\d{4}\b`,           // SSN
			`\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b`, // Credit card
			`\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`, // Email
			`\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b`, // Phone
		}
	}
	return &cfg, nil
}

func main() {
	configPath := os.Getenv("CONFIG_PATH")
	if configPath == "" {
		configPath = "/etc/llm-gateway/config.json"
	}

	cfg, err := loadConfig(configPath)
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	gateway, err := NewGateway(cfg)
	if err != nil {
		log.Fatalf("Failed to create gateway: %v", err)
	}
	defer gateway.auditLogger.Close()

	r := gin.Default()
	r.Use(gin.Recovery())

	// Health and metrics
	r.GET("/health", gateway.HealthCheck)
	r.GET("/metrics", gateway.Metrics)

	// OpenAI-compatible endpoints
	v1 := r.Group("/v1")
	{
		v1.POST("/chat/completions", gateway.ChatCompletions)
		v1.POST("/completions", gateway.ChatCompletions) // alias
		v1.POST("/embeddings", gateway.ChatCompletions)  // placeholder
	}

	addr := ":" + cfg.Port
	log.Printf("Starting LLM Gateway on %s", addr)
	if err := r.Run(addr); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}

func min(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}