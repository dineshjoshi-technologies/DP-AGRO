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

	"github.com/google/uuid"
)

// OpenAIProvider implements the Provider interface for OpenAI-compatible APIs
type OpenAIProvider struct {
	config   ProviderConfig
	client   *http.Client
	baseURL  string
	apiKey   string
	models   []string
}

var _ Provider = (*OpenAIProvider)(nil)

// NewOpenAIProvider creates a new OpenAI provider
func NewOpenAIProvider(config ProviderConfig) *OpenAIProvider {
	baseURL := config.BaseURL
	if baseURL == "" {
		baseURL = "https://api.openai.com/v1"
	}
	baseURL = strings.TrimSuffix(baseURL, "/")

	return &OpenAIProvider{
		config:  config,
		client:  &http.Client{Timeout: 120 * time.Second},
		baseURL: baseURL,
		apiKey:  config.APIKey,
		models:  config.Models,
	}
}

func (p *OpenAIProvider) Name() string {
	return p.config.Name
}

func (p *OpenAIProvider) Models() []string {
	return p.models
}

func (p *OpenAIProvider) SupportsStreaming() bool {
	return true
}

func (p *OpenAIProvider) SupportsTools() bool {
	return true
}

func (p *OpenAIProvider) SupportsVision() bool {
	// Check if any model supports vision
	for _, m := range p.models {
		if strings.Contains(strings.ToLower(m), "vision") || strings.Contains(m, "gpt-4o") {
			return true
		}
	}
	return false
}

func (p *OpenAIProvider) ChatCompletion(ctx context.Context, req *ChatCompletionRequest) (*ChatCompletionResponse, error) {
	// Convert to OpenAI format
	openAIReq := p.toOpenAIRequest(req)
	
	body, err := json.Marshal(openAIReq)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", p.baseURL+"/chat/completions", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	p.setHeaders(httpReq)

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

func (p *OpenAIProvider) ChatCompletionStream(ctx context.Context, req *ChatCompletionRequest) (<-chan StreamChunk, error) {
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

	p.setHeaders(httpReq)

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

func (p *OpenAIProvider) EstimateTokens(req *ChatCompletionRequest) int {
	// Rough estimation: ~4 chars per token
	totalChars := 0
	for _, msg := range req.Messages {
		totalChars += len(msg.Content)
	}
	if req.Tools != nil {
		for _, tool := range req.Tools {
			totalChars += len(tool.Function.Description)
			totalChars += len(string(tool.Function.Parameters))
		}
	}
	return totalChars / 4
}

func (p *OpenAIProvider) HealthCheck(ctx context.Context) error {
	req, err := http.NewRequestWithContext(ctx, "GET", p.baseURL+"/models", nil)
	if err != nil {
		return err
	}
	p.setHeaders(req)

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

func (p *OpenAIProvider) setHeaders(req *http.Request) {
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+p.apiKey)
	for k, v := range p.config.Headers {
		req.Header.Set(k, v)
	}
}

func (p *OpenAIProvider) toOpenAIRequest(req *ChatCompletionRequest) *openAIChatCompletionRequest {
	messages := make([]openAIMessage, len(req.Messages))
	for i, msg := range req.Messages {
		messages[i] = openAIMessage{
			Role:       msg.Role,
			Content:    msg.Content,
			Name:       msg.Name,
			ToolCalls:  p.toOpenAIToolCalls(msg.ToolCalls),
			ToolCallID: msg.ToolCallID,
		}
	}

	var tools []openAITool
	if req.Tools != nil {
		tools = make([]openAITool, len(req.Tools))
		for i, tool := range req.Tools {
			tools[i] = openAITool{
				Type: tool.Type,
				Function: openAIFunction{
					Name:        tool.Function.Name,
					Description: tool.Function.Description,
					Parameters:  tool.Function.Parameters,
				},
			}
		}
	}

	return &openAIChatCompletionRequest{
		Model:       req.Model,
		Messages:    messages,
		Tools:       tools,
		ToolChoice:  req.ToolChoice,
		Temperature: req.Temperature,
		MaxTokens:   req.MaxTokens,
		Stream:      req.Stream,
	}
}

func (p *OpenAIProvider) toOpenAIToolCalls(calls []ToolCall) []openAIToolCall {
	if calls == nil {
		return nil
	}
	result := make([]openAIToolCall, len(calls))
	for i, call := range calls {
		result[i] = openAIToolCall{
			ID:   call.ID,
			Type: call.Type,
			Function: openAIToolCallFunction{
				Name:      call.Function.Name,
				Arguments: string(call.Function.Arguments),
			},
		}
	}
	return result
}

func (p *OpenAIProvider) fromOpenAIResponse(resp *openAIChatCompletionResponse) *ChatCompletionResponse {
	choices := make([]Choice, len(resp.Choices))
	for i, choice := range resp.Choices {
		choices[i] = Choice{
			Index: choice.Index,
			Message: Message{
				Role:      choice.Message.Role,
				Content:   choice.Message.Content,
				ToolCalls: p.fromOpenAIToolCalls(choice.Message.ToolCalls),
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

func (p *OpenAIProvider) fromOpenAIToolCalls(calls []openAIToolCall) []ToolCall {
	if calls == nil {
		return nil
	}
	result := make([]ToolCall, len(calls))
	for i, call := range calls {
		result[i] = ToolCall{
			ID:   call.ID,
			Type: call.Type,
			Function: ToolCallFunction{
				Name:      call.Function.Name,
				Arguments: json.RawMessage(call.Function.Arguments),
			},
		}
	}
	return result
}

func (p *OpenAIProvider) parseStream(body io.Reader, chunks chan<- StreamChunk) {
	// SSE parsing - simplified
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
			if chunk.Usage != nil {
				chunks <- StreamChunk{
					Usage: &Usage{
						PromptTokens:     chunk.Usage.PromptTokens,
						CompletionTokens: chunk.Usage.CompletionTokens,
						TotalTokens:      chunk.Usage.TotalTokens,
					},
				}
			}
		}
	}
}

// OpenAI API types
type openAIChatCompletionRequest struct {
	Model       string            `json:"model"`
	Messages    []openAIMessage   `json:"messages"`
	Tools       []openAITool      `json:"tools,omitempty"`
	ToolChoice  interface{}       `json:"tool_choice,omitempty"`
	Temperature *float64          `json:"temperature,omitempty"`
	MaxTokens   *int              `json:"max_tokens,omitempty"`
	Stream      bool              `json:"stream,omitempty"`
}

type openAIMessage struct {
	Role       string           `json:"role"`
	Content    string           `json:"content"`
	Name       string           `json:"name,omitempty"`
	ToolCalls  []openAIToolCall `json:"tool_calls,omitempty"`
	ToolCallID string           `json:"tool_call_id,omitempty"`
}

type openAITool struct {
	Type     string         `json:"type"`
	Function openAIFunction `json:"function"`
}

type openAIFunction struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	Parameters  json.RawMessage `json:"parameters"`
}

type openAIToolCall struct {
	ID       string                 `json:"id"`
	Type     string                 `json:"type"`
	Function openAIToolCallFunction `json:"function"`
}

type openAIToolCallFunction struct {
	Name      string `json:"name"`
	Arguments string `json:"arguments"`
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
	Usage   *openAIUsage         `json:"usage,omitempty"`
}

type openAIStreamChoice struct {
	Index        int                `json:"index"`
	Delta        openAIStreamDelta  `json:"delta"`
	FinishReason string             `json:"finish_reason"`
}

type openAIStreamDelta struct {
	Role      string `json:"role,omitempty"`
	Content   string `json:"content,omitempty"`
	ToolCalls []openAIToolCall `json:"tool_calls,omitempty"`
}