package router

import (
	"fmt"
)

// ProviderFactory creates providers from config
type ProviderFactory struct{}

func NewProviderFactory() *ProviderFactory {
	return &ProviderFactory{}
}

func (f *ProviderFactory) CreateProvider(config ProviderConfig) (Provider, error) {
	switch config.Type {
	case "openai":
		return NewOpenAIProvider(config), nil
	case "anthropic":
		return NewAnthropicProvider(config), nil
	case "ollama":
		return NewOllamaProvider(config), nil
	case "vllm":
		return NewVLLMProvider(config), nil
	case "bedrock":
		return NewBedrockProvider(config), nil
	default:
		return nil, fmt.Errorf("unknown provider type: %s", config.Type)
	}
}

// NewProvider is a convenience function that uses the factory
func NewProvider(config ProviderConfig) (Provider, error) {
	factory := NewProviderFactory()
	return factory.CreateProvider(config)
}