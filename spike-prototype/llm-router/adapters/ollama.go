package router

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// OllamaProvider implements the Provider interface for Ollama API
type OllamaProvider struct {
	config  ProviderConfig
	client  *http.Client
	baseURL string
	models  []string
}

var _ Provider = (*OllamaProvider)(nil)

func NewOllamaProvider(config ProviderConfig) *OllamaProvider {
	baseURL := config.BaseURL
	if baseURL == "" {
		baseURL = "http://localhost:11434/v1"
	}
	baseURL = strings.TrimSuffix(baseURL, "/")

	return &OllamaProvider{
		config:  config,
		client:  &http.Client{Timeout: 120 * time.Second},
		baseURL: baseURL,
		models:  config.Models,
	}
}

func (p *OllamaProvider) Name() string {
	return p.config.Name
}

func (p *OllamaProvider) Models() []string {
	return p.models
}

func (p *OllamaProvider) SupportsStreaming() bool {
	return true
}

func (p *OllamaProvider) SupportsTools() bool {
	return false // Ollama doesn't support tools yet
}

func (p *OllamaProvider) SupportsVision() bool {
	return false
}

func (p *OllamaProvider) ChatCompletion(ctx context.Context, req *ChatCompletionRequest) (*ChatCompletionResponse, error) {
	// Ollama uses OpenAI-compatible API
	openAIReq := p.toOpenAIRequest(req)
	
	body, err := json.Marshal(openAIReq)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", p.baseURL+"/chat/completions", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := p.client.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API error %d: %s", resp.StatusCode, string(respBody))
	}

	var openAIResp openAIChatCompletionResponse
	if err := json.Unmarshal(respBody, &openAIResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return p.fromOpenAIResponse(&openAIResp), nil
}

func (p *OllamaProvider) ChatCompletionStream(ctx context.Context, req *ChatCompletionRequest) (<-chan StreamChunk, error) {
	openAIReq := p.toOpenAIRequest(req)
	openAIReq.Stream = true

	body, err := json.Marshal(openAIReq)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", p.baseURL+"/chat/completions", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := p.client.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}

	chunks := make(chan StreamChunk, 100)
	go func() {
		defer close(chunks)
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			chunks <- StreamChunk{Delta: fmt.Sprintf("API error %d: %s", resp.StatusCode, string(body)), FinishReason: "error"}
			return
		}

		p.parseStream(resp.Body, chunks)
	}()

	return chunks, nil
}

func (p *OllamaProvider) EstimateTokens(req *ChatCompletionRequest) int {
	totalChars := 0
	for _, msg := range req.Messages {
		totalChars += len(msg.Content)
	}
	return totalChars / 4
}

func (p *OllamaProvider) HealthCheck(ctx context.Context) error {
	req, err := http.NewRequestWithContext(ctx, "GET", p.baseURL+"/models", nil)
	if err != nil {
		return err
	}

	resp, err := p.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("health check failed: %d", resp.StatusCode)
	}
	return nil
}

func (p *OllamaProvider) toOpenAIRequest(req *ChatCompletionRequest) *openAIChatCompletionRequest {
	messages := make([]openAIMessage, len(req.Messages))
	for i, msg := range req.Messages {
		messages[i] = openAIMessage{
			Role:    msg.Role,
			Content: msg.Content,
		}
	}

	return &openAIChatCompletionRequest{
		Model:    req.Model,
		Messages: messages,
		Stream:   req.Stream,
	}
}

func (p *OllamaProvider) fromOpenAIResponse(resp *openAIChatCompletionResponse) *ChatCompletionResponse {
	choices := make([]Choice, len(resp.Choices))
	for i, choice := range resp.Choices {
		choices[i] = Choice{
			Index: choice.Index,
			Message: Message{
				Role:    choice.Message.Role,
				Content: choice.Message.Content,
			},
			FinishReason: choice.FinishReason,
		}
	}

	return &ChatCompletionResponse{
		ID:      resp.ID,
		Object:  resp.Object,
		Created: resp.Created,
		Model:   resp.Model,
		Choices: choices,
		Usage: Usage{
			PromptTokens:     resp.Usage.PromptTokens,
			CompletionTokens: resp.Usage.CompletionTokens,
			TotalTokens:      resp.Usage.TotalTokens,
		},
	}
}

func (p *OllamaProvider) parseStream(body io.Reader, chunks chan<- StreamChunk) {
	buf := make([]byte, 4096)
	for {
		n, err := body.Read(buf)
		if err != nil {
			if err != io.EOF {
				chunks <- StreamChunk{Delta: fmt.Sprintf("Stream error: %v", err), FinishReason: "error"}
			}
			return
		}

		data := buf[:n]
		lines := bytes.Split(data, []byte("\n"))
		for _, line := range lines {
			line = bytes.TrimSpace(line)
			if len(line) == 0 {
				continue
			}
			if bytes.HasPrefix(line, []byte("data: ")) {
				line = line[6:]
			}
			if bytes.Equal(line, []byte("[DONE]")) {
				return
			}

			var chunk openAIStreamChunk
			if err := json.Unmarshal(line, &chunk); err != nil {
				continue
			}

			if len(chunk.Choices) > 0 && chunk.Choices[0].Delta.Content != "" {
				chunks <- StreamChunk{
					Delta:        chunk.Choices[0].Delta.Content,
					FinishReason: chunk.Choices[0].FinishReason,
				}
			}
		}
	}
}

// Re-use OpenAI types
type openAIChatCompletionRequest struct {
	Model    string          `json:"model"`
	Messages []openAIMessage `json:"messages"`
	Stream   bool            `json:"stream,omitempty"`
}

type openAIMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type openAIChatCompletionResponse struct {
	ID      string                 `json:"id"`
	Object  string                 `json:"object"`
	Created int64                  `json:"created"`
	Model   string                 `json:"model"`
	Choices []openAIChoice         `json:"choices"`
	Usage   openAIUsage            `json:"usage"`
}

type openAIChoice struct {
	Index        int           `json:"index"`
	Message      openAIMessage `json:"message"`
	FinishReason string        `json:"finish_reason"`
}

type openAIUsage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

type openAIStreamChunk struct {
	Choices []openAIStreamChoice `json:"choices"`
}

type openAIStreamChoice struct {
	Index        int                `json:"index"`
	Delta        openAIStreamDelta  `json:"delta"`
	FinishReason string             `json:"finish_reason"`
}

type openAIStreamDelta struct {
	Content string `json:"content,omitempty"`
}