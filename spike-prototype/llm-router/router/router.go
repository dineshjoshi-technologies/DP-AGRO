package router

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sync"
	"time"

	"github.com/google/uuid"
)

// Message represents a chat message in canonical format
type Message struct {
	Role       string          `json:"role"`
	Content    string          `json:"content"`
	ToolCalls  []ToolCall      `json:"tool_calls,omitempty"`
	ToolCallID string          `json:"tool_call_id,omitempty"`
	Name       string          `json:"name,omitempty"`
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

// Tool represents a function/tool definition
type Tool struct {
	Type     string       `json:"type"`
	Function ToolFunction `json:"function"`
}

type ToolFunction struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	Parameters  json.RawMessage `json:"parameters"`
}

// ChatCompletionRequest is the canonical request format
type ChatCompletionRequest struct {
	Model       string          `json:"model"`
	Messages    []Message       `json:"messages"`
	Tools       []Tool          `json:"tools,omitempty"`
	ToolChoice  interface{}     `json:"tool_choice,omitempty"`
	Temperature *float64        `json:"temperature,omitempty"`
	MaxTokens   *int            `json:"max_tokens,omitempty"`
	Stream      bool            `json:"stream,omitempty"`
	Metadata    json.RawMessage `json:"metadata,omitempty"`
}

// ChatCompletionResponse is the canonical response format
type ChatCompletionResponse struct {
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

// StreamChunk represents a streaming response chunk
type StreamChunk struct {
	Delta        string `json:"delta"`
	FinishReason string `json:"finish_reason,omitempty"`
	Usage        *Usage `json:"usage,omitempty"`
}

// Provider defines the interface for LLM providers
type Provider interface {
	Name() string
	Models() []string
	SupportsStreaming() bool
	SupportsTools() bool
	SupportsVision() bool
	
	// ChatCompletion performs a non-streaming completion
	ChatCompletion(ctx context.Context, req *ChatCompletionRequest) (*ChatCompletionResponse, error)
	
	// ChatCompletionStream performs a streaming completion
	ChatCompletionStream(ctx context.Context, req *ChatCompletionRequest) (<-chan StreamChunk, error)
	
	// EstimateTokens estimates token count for a request
	EstimateTokens(req *ChatCompletionRequest) int
	
	// HealthCheck verifies provider connectivity
	HealthCheck(ctx context.Context) error
}

// ProviderConfig holds configuration for a provider
type ProviderConfig struct {
	Name     string            `json:"name" yaml:"name"`
	Type     string            `json:"type" yaml:"type"` // openai, anthropic, ollama, vllm, bedrock
	APIKey   string            `json:"api_key,omitempty" yaml:"api_key,omitempty"`
	BaseURL  string            `json:"base_url,omitempty" yaml:"base_url,omitempty"`
	Models   []string          `json:"models" yaml:"models"`
	Headers  map[string]string `json:"headers,omitempty" yaml:"headers,omitempty"`
	Enabled  bool              `json:"enabled" yaml:"enabled"`
	Priority int               `json:"priority" yaml:"priority"` // lower = higher priority
}

// ModelInfo holds metadata about a model
type ModelInfo struct {
	ID            string  `json:"id"`
	Provider      string  `json:"provider"`
	InputCost     float64 `json:"input_cost_per_million"`  // $ per 1M tokens
	OutputCost    float64 `json:"output_cost_per_million"` // $ per 1M tokens
	QualityTier   int     `json:"quality_tier"`            // 1-5, higher = better
	LatencyTier   int     `json:"latency_tier"`            // 1-5, lower = faster
	ContextWindow int     `json:"context_window"`
	SupportsTools bool    `json:"supports_tools"`
	SupportsVision bool   `json:"supports_vision"`
}

// RouterConfig holds router configuration
type RouterConfig struct {
	DefaultModel  string                    `json:"default_model" yaml:"default_model"`
	Selection     SelectionConfig           `json:"selection" yaml:"selection"`
	Fallbacks     map[string][]string       `json:"fallbacks" yaml:"fallbacks"`
	Providers     []ProviderConfig          `json:"providers" yaml:"providers"`
	Models        map[string]ModelInfo      `json:"models" yaml:"models"`
	RequestTimeout time.Duration            `json:"request_timeout" yaml:"request_timeout"`
}

type SelectionConfig struct {
	Weights SelectionWeights `json:"weights" yaml:"weights"`
}

type SelectionWeights struct {
	Quality  float64 `json:"quality" yaml:"quality"`
	Cost     float64 `json:"cost" yaml:"cost"`
	Latency  float64 `json:"latency" yaml:"latency"`
	Budget   float64 `json:"budget" yaml:"budget"`
}

// Router is the main LLM router
type Router struct {
	config       *RouterConfig
	providers    map[string]Provider
	models       map[string]ModelInfo
	fallbacks    map[string][]string
	selection    *ModelSelector
	costTracker  *CostTracker
	mu           sync.RWMutex
	requestCount int64
}

// NewRouter creates a new router instance
func NewRouter(config *RouterConfig) (*Router, error) {
	r := &Router{
		config:    config,
		providers: make(map[string]Provider),
		models:    config.Models,
		fallbacks: config.Fallbacks,
		costTracker: NewCostTracker(),
		selection: NewModelSelector(config.Selection.Weights, config.Models),
	}

	// Initialize providers
	for _, pc := range config.Providers {
		if !pc.Enabled {
			continue
		}
		provider, err := NewProvider(pc)
		if err != nil {
			return nil, fmt.Errorf("failed to create provider %s: %w", pc.Name, err)
		}
		r.providers[pc.Name] = provider
	}

	if len(r.providers) == 0 {
		return nil, fmt.Errorf("no enabled providers configured")
	}

	return r, nil
}

// RouteRequest routes a request to the best available provider/model
func (r *Router) RouteRequest(ctx context.Context, req *ChatCompletionRequest) (*ChatCompletionResponse, error) {
	startTime := time.Now()
	requestID := uuid.New().String()

	// Normalize request
	if req.Model == "" {
		req.Model = r.config.DefaultModel
	}

	// Select model
	model, providerName, err := r.selection.SelectModel(req, r.getAvailableModels())
	if err != nil {
		return nil, fmt.Errorf("model selection failed: %w", err)
	}
	req.Model = model

	// Get provider
	provider, ok := r.providers[providerName]
	if !ok {
		return nil, fmt.Errorf("provider %s not found", providerName)
	}

	// Estimate tokens for budget check
	estimatedTokens := provider.EstimateTokens(req)

	// Execute with fallback
	resp, err := r.executeWithFallback(ctx, req, providerName, estimatedTokens)
	
	// Record metrics
	latency := time.Since(startTime)
	r.costTracker.Record(model, providerName, estimatedTokens, resp.Usage.TotalTokens, latency, err)
	
	return resp, err
}

// RouteRequestStream routes a streaming request
func (r *Router) RouteRequestStream(ctx context.Context, req *ChatCompletionRequest) (<-chan StreamChunk, error) {
	if req.Model == "" {
		req.Model = r.config.DefaultModel
	}

	model, providerName, err := r.selection.SelectModel(req, r.getAvailableModels())
	if err != nil {
		return nil, fmt.Errorf("model selection failed: %w", err)
	}
	req.Model = model

	provider, ok := r.providers[providerName]
	if !ok {
		return nil, fmt.Errorf("provider %s not found", providerName)
	}

	if !provider.SupportsStreaming() {
		return nil, fmt.Errorf("provider %s does not support streaming", providerName)
	}

	return provider.ChatCompletionStream(ctx, req)
}

// executeWithFallback executes request with fallback chain
func (r *Router) executeWithFallback(ctx context.Context, req *ChatCompletionRequest, primaryProvider string, estimatedTokens int) (*ChatCompletionResponse, error) {
	// Try primary provider
	provider := r.providers[primaryProvider]
	resp, err := provider.ChatCompletion(ctx, req)
	if err == nil {
		return resp, nil
	}

	// Try fallbacks
	fallbacks := r.fallbacks[req.Model]
	if fallbacks == nil {
		fallbacks = r.fallbacks["default"]
	}

	for _, fallbackModel := range fallbacks {
		fallbackProviderName := r.getProviderForModel(fallbackModel)
		if fallbackProviderName == "" || fallbackProviderName == primaryProvider {
			continue
		}

		fallbackProvider := r.providers[fallbackProviderName]
		if fallbackProvider == nil {
			continue
		}

		// Update request with fallback model
		fallbackReq := *req
		fallbackReq.Model = fallbackModel

		resp, err = fallbackProvider.ChatCompletion(ctx, &fallbackReq)
		if err == nil {
			return resp, nil
		}
		// Log fallback attempt
		_ = fmt.Sprintf("Fallback from %s to %s failed: %v", primaryProvider, fallbackModel, err)
	}

	return nil, fmt.Errorf("all providers failed, last error: %w", err)
}

func (r *Router) getAvailableModels() []string {
	r.mu.RLock()
	defer r.mu.RUnlock()

	models := make([]string, 0, len(r.models))
	for id := range r.models {
		models = append(models, id)
	}
	return models
}

func (r *Router) getProviderForModel(model string) string {
	for name, provider := range r.providers {
		for _, m := range provider.Models() {
			if m == model {
				return name
			}
		}
	}
	return ""
}

// GetModels returns all available models
func (r *Router) GetModels() []ModelInfo {
	r.mu.RLock()
	defer r.mu.RUnlock()

	result := make([]ModelInfo, 0, len(r.models))
	for _, m := range r.models {
		result = append(result, m)
	}
	return result
}

// GetProviderHealth returns health status of all providers
func (r *Router) GetProviderHealth(ctx context.Context) map[string]error {
	r.mu.RLock()
	defer r.mu.RUnlock()

	result := make(map[string]error)
	for name, provider := range r.providers {
		result[name] = provider.HealthCheck(ctx)
	}
	return result
}

// GetCostStats returns cost tracking statistics
func (r *Router) GetCostStats() CostStats {
	return r.costTracker.GetStats()
}

// HTTPHandler returns an HTTP handler for the router (OpenAI-compatible)
func (r *Router) HTTPHandler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/v1/chat/completions", r.handleChatCompletions)
	mux.HandleFunc("/v1/models", r.handleModels)
	mux.HandleFunc("/health", r.handleHealth)
	return mux
}

func (r *Router) handleChatCompletions(w http.ResponseWriter, req *http.Request) {
	ctx := req.Context()
	
	var request ChatCompletionRequest
	body, err := io.ReadAll(req.Body)
	if err != nil {
		http.Error(w, "Failed to read request", http.StatusBadRequest)
		return
	}
	defer req.Body.Close()

	if err := json.Unmarshal(body, &request); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if request.Stream {
		r.handleStream(w, req, &request)
		return
	}

	resp, err := r.RouteRequest(ctx, &request)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func (r *Router) handleStream(w http.ResponseWriter, req *http.Request, request *ChatCompletionRequest) {
	ctx := req.Context()
	
	chunks, err := r.RouteRequestStream(ctx, request)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming not supported", http.StatusInternalServerError)
		return
	}

	for chunk := range chunks {
		data, _ := json.Marshal(chunk)
		fmt.Fprintf(w, "data: %s\n\n", data)
		flusher.Flush()
	}
	fmt.Fprintf(w, "data: [DONE]\n\n")
	flusher.Flush()
}

func (r *Router) handleModels(w http.ResponseWriter, req *http.Request) {
	models := r.GetModels()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"object": "list",
		"data":   models,
	})
}

func (r *Router) handleHealth(w http.ResponseWriter, req *http.Request) {
	ctx := req.Context()
	health := r.GetProviderHealth(ctx)
	
	allHealthy := true
	for _, err := range health {
		if err != nil {
			allHealthy = false
			break
		}
	}

	status := "healthy"
	if !allHealthy {
		status = "degraded"
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":    status,
		"providers": health,
		"timestamp": time.Now().Unix(),
	})
}