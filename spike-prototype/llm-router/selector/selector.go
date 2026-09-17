package router

import (
	"math"
	"sort"
	"sync"
)

// ModelSelector selects the best model for a request
type ModelSelector struct {
	weights    SelectionWeights
	modelInfos map[string]ModelInfo
	mu         sync.RWMutex
}

// NewModelSelector creates a new model selector
func NewModelSelector(weights SelectionWeights, modelInfos map[string]ModelInfo) *ModelSelector {
	// Set defaults if not provided
	if weights.Quality == 0 && weights.Cost == 0 && weights.Latency == 0 && weights.Budget == 0 {
		weights = SelectionWeights{
			Quality:  0.5,
			Cost:     0.3,
			Latency:  0.1,
			Budget:   0.1,
		}
	}
	return &ModelSelector{
		weights:    weights,
		modelInfos: modelInfos,
	}
}

// SelectModel selects the best model for a request
func (s *ModelSelector) SelectModel(req *ChatCompletionRequest, availableModels []string) (string, string, error) {
	if len(availableModels) == 0 {
		return "", "", ErrNoModelsAvailable
	}

	// If specific model requested and available, use it
	if req.Model != "" {
		for _, m := range availableModels {
			if m == req.Model {
				provider := s.getProviderForModel(m)
				if provider != "" {
					return m, provider, nil
				}
			}
		}
	}

	// Score all available models
	type scoredModel struct {
		model     string
		provider  string
		score     float64
	}

	var scored []scoredModel
	for _, modelID := range availableModels {
		info, ok := s.modelInfos[modelID]
		if !ok {
			continue
		}
		provider := s.getProviderForModel(modelID)
		if provider == "" {
			continue
		}

		score := s.calculateScore(req, info)
		scored = append(scored, scoredModel{
			model:    modelID,
			provider: provider,
			score:    score,
		})
	}

	if len(scored) == 0 {
		return "", "", ErrNoModelsAvailable
	}

	// Sort by score descending
	sort.Slice(scored, func(i, j int) bool {
		return scored[i].score > scored[j].score
	})

	return scored[0].model, scored[0].provider, nil
}

// calculateScore calculates the selection score for a model
func (s *ModelSelector) calculateScore(req *ChatCompletionRequest, info ModelInfo) float64 {
	s.mu.RLock()
	weights := s.weights
	s.mu.RUnlock()

	// Normalize values to 0-1 range
	qualityScore := float64(info.QualityTier) / 5.0
	
	// Cost: lower is better, normalize by max cost in registry
	maxInputCost := s.getMaxInputCost()
	maxOutputCost := s.getMaxOutputCost()
	costScore := 1.0
	if maxInputCost > 0 || maxOutputCost > 0 {
		avgCost := (info.InputCost + info.OutputCost) / 2.0
		maxAvgCost := (maxInputCost + maxOutputCost) / 2.0
		if maxAvgCost > 0 {
			costScore = 1.0 - (avgCost / maxAvgCost)
		}
	}

	// Latency: lower tier is better (1=fastest)
	latencyScore := 1.0 - (float64(info.LatencyTier)-1)/4.0

	// Budget fit: prefer models that fit within typical budgets
	budgetScore := 1.0
	if req.MaxTokens != nil && *req.MaxTokens > 0 {
		estimatedCost := (info.InputCost + info.OutputCost) * float64(*req.MaxTokens) / 1_000_000
		// Prefer models under $0.10 per request
		if estimatedCost > 0.10 {
			budgetScore = 0.5
		}
	}

	// Weighted sum
	score := weights.Quality*qualityScore +
		weights.Cost*costScore +
		weights.Latency*latencyScore +
		weights.Budget*budgetScore

	// Boost score for models that support required features
	if req.Tools != nil && len(req.Tools) > 0 && !info.SupportsTools {
		score *= 0.5 // Penalize models without tool support when tools requested
	}

	return score
}

func (s *ModelSelector) getMaxInputCost() float64 {
	max := 0.0
	for _, info := range s.modelInfos {
		if info.InputCost > max {
			max = info.InputCost
		}
	}
	return max
}

func (s *ModelSelector) getMaxOutputCost() float64 {
	max := 0.0
	for _, info := range s.modelInfos {
		if info.OutputCost > max {
			max = info.OutputCost
		}
	}
	return max
}

func (s *ModelSelector) getProviderForModel(modelID string) string {
	// This would be populated from provider registration
	// For now, infer from model ID prefix
	switch {
	case len(modelID) >= 4 && modelID[:4] == "gpt-":
		return "openai"
	case len(modelID) >= 7 && modelID[:7] == "claude-":
		return "anthropic"
	case len(modelID) >= 5 && modelID[:5] == "llama":
		return "ollama"
	default:
		return "openai" // default
	}
}

// Errors
var (
	ErrNoModelsAvailable = &RouterError{Code: "NO_MODELS_AVAILABLE", Message: "No models available for selection"}
)

type RouterError struct {
	Code    string
	Message string
}

func (e *RouterError) Error() string {
	return e.Message
}