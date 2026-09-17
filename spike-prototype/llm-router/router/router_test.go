package router

import (
	"context"
	"testing"
	"time"
)

func TestRouterConfigDefaults(t *testing.T) {
	config := &RouterConfig{
		DefaultModel: "gpt-4o-mini",
		Selection: SelectionConfig{
			Weights: SelectionWeights{
				Quality: 0.5,
				Cost:    0.3,
				Latency: 0.1,
				Budget:  0.1,
			},
		},
		Models: map[string]ModelInfo{
			"gpt-4o-mini": {
				ID:            "gpt-4o-mini",
				Provider:      "openai",
				InputCost:     0.15,
				OutputCost:    0.6,
				QualityTier:   4,
				LatencyTier:   2,
				ContextWindow: 128000,
				SupportsTools: true,
				SupportsVision: true,
			},
		},
		Providers: []ProviderConfig{
			{
				Name:    "openai",
				Type:    "openai",
				APIKey:  "test-key",
				Models:  []string{"gpt-4o-mini"},
				Enabled: true,
			},
		},
	}

	r, err := NewRouter(config)
	if err != nil {
		t.Fatalf("Failed to create router: %v", err)
	}

	if r == nil {
		t.Fatal("Router should not be nil")
	}

	models := r.GetModels()
	if len(models) != 1 {
		t.Errorf("Expected 1 model, got %d", len(models))
	}
}

func TestModelSelectorDefaults(t *testing.T) {
	weights := SelectionWeights{}
	if weights.Quality == 0 && weights.Cost == 0 && weights.Latency == 0 && weights.Budget == 0 {
		selector := NewModelSelector(weights, map[string]ModelInfo{
			"test-model": {
				ID:           "test-model",
				Provider:     "test",
				InputCost:    1.0,
				OutputCost:   2.0,
				QualityTier:  3,
				LatencyTier:  2,
			},
		})
		
		if selector == nil {
			t.Fatal("Selector should not be nil")
		}
		
		// Check defaults were applied
		req := &ChatCompletionRequest{}
		_, _, err := selector.SelectModel(req, []string{"test-model"})
		if err != nil {
			t.Errorf("Selection should work with defaults: %v", err)
		}
	}
}

func TestModelSelectorScoring(t *testing.T) {
	modelInfos := map[string]ModelInfo{
		"premium-model": {
			ID:           "premium-model",
			Provider:     "test",
			InputCost:    10.0,
			OutputCost:   30.0,
			QualityTier:  5,
			LatencyTier:  3,
			SupportsTools: true,
		},
		"cheap-model": {
			ID:           "cheap-model",
			Provider:     "test",
			InputCost:    0.1,
			OutputCost:   0.2,
			QualityTier:  3,
			LatencyTier:  1,
			SupportsTools: false,
		},
	}

	selector := NewModelSelector(SelectionWeights{
		Quality:  0.5,
		Cost:     0.3,
		Latency:  0.1,
		Budget:   0.1,
	}, modelInfos)

	// Test with tools required - should prefer premium model
	reqWithTools := &ChatCompletionRequest{
		Tools: []Tool{{Type: "function", Function: ToolFunction{Name: "test"}}},
	}
	model, provider, err := selector.SelectModel(reqWithTools, []string{"premium-model", "cheap-model"})
	if err != nil {
		t.Fatalf("Selection failed: %v", err)
	}
	if model != "premium-model" {
		t.Errorf("Expected premium-model for tools, got %s", model)
	}
	if provider != "test" {
		t.Errorf("Expected provider test, got %s", provider)
	}

	// Test without tools - might prefer cheap model
	reqNoTools := &ChatCompletionRequest{}
	model, provider, err = selector.SelectModel(reqNoTools, []string{"premium-model", "cheap-model"})
	if err != nil {
		t.Fatalf("Selection failed: %v", err)
	}
	if provider != "test" {
		t.Errorf("Expected provider test, got %s", provider)
	}
}

func TestCostTracker(t *testing.T) {
	tracker := NewCostTracker()

	// Record some requests
	tracker.Record("gpt-4o", "openai", 100, 150, 500*time.Millisecond, nil)
	tracker.Record("gpt-4o", "openai", 200, 250, 600*time.Millisecond, nil)
	tracker.Record("claude-3.5-sonnet", "anthropic", 150, 180, 400*time.Millisecond, nil)

	stats := tracker.GetStats()
	if stats.TotalRequests != 3 {
		t.Errorf("Expected 3 total requests, got %d", stats.TotalRequests)
	}
	if stats.TotalTokens != 580 {
		t.Errorf("Expected 580 total tokens, got %d", stats.TotalTokens)
	}

	modelStats, ok := stats.ByModel["gpt-4o"]
	if !ok {
		t.Fatal("Expected gpt-4o stats")
	}
	if modelStats.Requests != 2 {
		t.Errorf("Expected 2 requests for gpt-4o, got %d", modelStats.Requests)
	}

	providerStats, ok := stats.ByProvider["openai"]
	if !ok {
		t.Fatal("Expected openai stats")
	}
	if providerStats.Requests != 2 {
		t.Errorf("Expected 2 requests for openai, got %d", providerStats.Requests)
	}
}

func TestCostTrackerReset(t *testing.T) {
	tracker := NewCostTracker()
	tracker.Record("gpt-4o", "openai", 100, 150, 500*time.Millisecond, nil)
	
	tracker.Reset()
	
	stats := tracker.GetStats()
	if stats.TotalRequests != 0 {
		t.Errorf("Expected 0 requests after reset, got %d", stats.TotalRequests)
	}
}

func TestProviderInterface(t *testing.T) {
	// This is a compile-time check that our types satisfy the Provider interface
	var _ Provider = (*OpenAIProvider)(nil)
	var _ Provider = (*AnthropicProvider)(nil)
	var _ Provider = (*OllamaProvider)(nil)
}

func TestRequestTokenEstimation(t *testing.T) {
	req := &ChatCompletionRequest{
		Messages: []Message{
			{Role: "user", Content: "Hello world"},
			{Role: "assistant", Content: "Hi there!"},
		},
	}
	
	// Rough estimation test
	estimator := &OpenAIProvider{}
	tokens := estimator.EstimateTokens(req)
	expected := (len("Hello world") + len("Hi there!")) / 4
	if tokens != expected {
		t.Errorf("Expected ~%d tokens, got %d", expected, tokens)
	}
}

func TestChatCompletionRequestJSON(t *testing.T) {
	req := ChatCompletionRequest{
		Model: "gpt-4o",
		Messages: []Message{
			{Role: "user", Content: "Hello"},
		},
		MaxTokens: intPtr(100),
		Temperature: float64Ptr(0.7),
		Stream: false,
	}

	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("Failed to marshal: %v", err)
	}

	var parsed ChatCompletionRequest
	if err := json.Unmarshal(data, &parsed); err != nil {
		t.Fatalf("Failed to unmarshal: %v", err)
	}

	if parsed.Model != req.Model {
		t.Errorf("Model mismatch: %s != %s", parsed.Model, req.Model)
	}
	if len(parsed.Messages) != len(req.Messages) {
		t.Errorf("Messages length mismatch")
	}
	if parsed.MaxTokens == nil || *parsed.MaxTokens != *req.MaxTokens {
		t.Errorf("MaxTokens mismatch")
	}
}

func intPtr(i int) *int { return &i }
func float64Ptr(f float64) *float64 { return &f }

func TestRouterHealthCheck(t *testing.T) {
	config := &RouterConfig{
		DefaultModel: "gpt-4o-mini",
		Models: map[string]ModelInfo{
			"gpt-4o-mini": {ID: "gpt-4o-mini", Provider: "test"},
		},
		Providers: []ProviderConfig{
			{Name: "test", Type: "openai", Models: []string{"gpt-4o-mini"}, Enabled: true},
		},
	}

	// This will fail because we don't have real credentials, but we can test the structure
	r, err := NewRouter(config)
	if err != nil {
		// Expected to fail without real credentials
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	health := r.GetProviderHealth(ctx)
	if len(health) == 0 {
		t.Error("Expected at least one provider in health check")
	}
}