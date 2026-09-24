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

// AnthropicProvider implements the Provider interface for Anthropic API
type AnthropicProvider struct {
	config  ProviderConfig
	client  *http.Client
	baseURL string
	apiKey  string
	models  []string
}

var _ Provider = (*AnthropicProvider)(nil)

// NewAnthropicProvider creates a new Anthropic provider
func NewAnthropicProvider(config ProviderConfig) *AnthropicProvider {
	baseURL := config.BaseURL
	if baseURL == "" {
		baseURL = "https://api.anthropic.com/v1"
	}
	baseURL = strings.TrimSuffix(baseURL, "/")

	return &AnthropicProvider{
		config:  config,
		client:  &http.Client{Timeout: 120 * time.Second},
		baseURL: baseURL,
		apiKey:  config.APIKey,
		models:  config.Models,
	}
}

func (p *AnthropicProvider) Name() string {
	return p.config.Name
}

func (p *AnthropicProvider) Models() []string {
	return p.models
}

func (p *AnthropicProvider) SupportsStreaming() bool {
	return true
}

func (p *AnthropicProvider) SupportsTools() bool {
	return true
}

func (p *AnthropicProvider) SupportsVision() bool {
	for _, m := range p.models {
		if strings.Contains(strings.ToLower(m), "vision") || strings.Contains(m, "claude-3") || strings.Contains(m, "claude-3.5") {
			return true
		}
	}
	return false
}

func (p *AnthropicProvider) ChatCompletion(ctx context.Context, req *ChatCompletionRequest) (*ChatCompletionResponse, error) {
	anthropicReq := p.toAnthropicRequest(req)
	
	body, err := json.Marshal(anthropicReq)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", p.baseURL+"/messages", bytes.NewReader(body))
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

	var anthropicResp anthropicMessagesResponse
	if err := json.Unmarshal(respBody, &anthropicResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return p.fromAnthropicResponse(&anthropicResp), nil
}

func (p *AnthropicProvider) ChatCompletionStream(ctx context.Context, req *ChatCompletionRequest) (<-chan StreamChunk, error) {
	anthropicReq := p.toAnthropicRequest(req)
	anthropicReq.Stream = true

	body, err := json.Marshal(anthropicReq)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", p.baseURL+"/messages", bytes.NewReader(body))
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

func (p *AnthropicProvider) EstimateTokens(req *ChatCompletionRequest) int {
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

func (p *AnthropicProvider) HealthCheck(ctx context.Context) error {
	// Anthropic doesn't have a simple models endpoint, try a minimal request
	req := &ChatCompletionRequest{
		Model:    p.models[0],
		Messages: []Message{{Role: "user", Content: "Hi"}},
		MaxTokens: intPtr(1),
	}
	_, err := p.ChatCompletion(ctx, req)
	return err
}

func (p *AnthropicProvider) setHeaders(req *http.Request) {
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("x-api-key", p.apiKey)
	req.Header.Set("anthropic-version", "2023-06-01")
	for k, v := range p.config.Headers {
		req.Header.Set(k, v)
	}
}

func (p *AnthropicProvider) toAnthropicRequest(req *ChatCompletionRequest) *anthropicMessagesRequest {
	var systemPrompt string
	var messages []anthropicMessage
	
	for _, msg := range req.Messages {
		if msg.Role == "system" {
			systemPrompt = msg.Content
		} else {
			messages = append(messages, anthropicMessage{
				Role:    msg.Role,
				Content: []anthropicContent{{Type: "text", Text: msg.Content}},
			})
		}
	}

	var tools []anthropicTool
	if req.Tools != nil {
		tools = make([]anthropicTool, len(req.Tools))
		for i, tool := range req.Tools {
			tools[i] = anthropicTool{
				Name:        tool.Function.Name,
				Description: tool.Function.Description,
				InputSchema: tool.Function.Parameters,
			}
		}
	}

	return &anthropicMessagesRequest{
		Model:       req.Model,
		System:      systemPrompt,
		Messages:    messages,
		Tools:       tools,
		ToolChoice:  req.ToolChoice,
		Temperature: req.Temperature,
		MaxTokens:   req.MaxTokens,
		Stream:      req.Stream,
	}
}

func (p *AnthropicProvider) fromAnthropicResponse(resp *anthropicMessagesResponse) *ChatCompletionResponse {
	var content string
	var toolCalls []ToolCall

	for _, block := range resp.Content {
		if block.Type == "text" {
			content = block.Text
		} else if block.Type == "tool_use" {
			toolCalls = append(toolCalls, ToolCall{
				ID: block.ID,
				Type: "function",
				Function: ToolCallFunction{
					Name:      block.Name,
					Arguments: block.Input,
				},
			})
		}
	}

	return &ChatCompletionResponse{
		ID:      resp.ID,
		Object:  "chat.completion",
		Created: time.Now().Unix(),
		Model:   resp.Model,
		Choices: []Choice{{
			Index: 0,
			Message: Message{
				Role:      "assistant",
				Content:   content,
				ToolCalls: toolCalls,
			},
			FinishReason: resp.StopReason,
		}},
		Usage: Usage{
			PromptTokens:     resp.Usage.InputTokens,
			CompletionTokens: resp.Usage.OutputTokens,
			TotalTokens:      resp.Usage.InputTokens + resp.Usage.OutputTokens,
		},
	}
}

func (p *AnthropicProvider) parseStream(body io.Reader, chunks chan<- StreamChunk) {
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

			var event anthropicStreamEvent
			if err := json.Unmarshal(line, &event); err != nil {
				continue
			}

			switch event.Type {
			case "content_block_delta":
				if event.Delta.Type == "text_delta" && event.Delta.Text != "" {
					chunks <- StreamChunk{Delta: event.Delta.Text}
				}
			case "message_delta":
				if event.Delta.StopReason != "" {
					chunks <- StreamChunk{FinishReason: event.Delta.StopReason}
				}
				if event.Usage != nil {
					chunks <- StreamChunk{
						Usage: &Usage{
							PromptTokens:     event.Usage.InputTokens,
							CompletionTokens: event.Usage.OutputTokens,
							TotalTokens:      event.Usage.InputTokens + event.Usage.OutputTokens,
						},
					}
				}
			}
		}
	}
}

// Anthropic API types
type anthropicMessagesRequest struct {
	Model       string            `json:"model"`
	System      string            `json:"system,omitempty"`
	Messages    []anthropicMessage `json:"messages"`
	Tools       []anthropicTool    `json:"tools,omitempty"`
	ToolChoice  interface{}       `json:"tool_choice,omitempty"`
	Temperature *float64          `json:"temperature,omitempty"`
	MaxTokens   *int              `json:"max_tokens"`
	Stream      bool              `json:"stream,omitempty"`
}

type anthropicMessage struct {
	Role    string               `json:"role"`
	Content []anthropicContent   `json:"content"`
}

type anthropicContent struct {
	Type string `json:"type"`
	Text string `json:"text,omitempty"`
}

type anthropicTool struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	InputSchema json.RawMessage `json:"input_schema"`
}

type anthropicMessagesResponse struct {
	ID           string             `json:"id"`
	Type         string             `json:"type"`
	Role         string             `json:"role"`
	Content      []anthropicContent `json:"content"`
	Model        string             `json:"model"`
	StopReason   string             `json:"stop_reason"`
	StopSequence string             `json:"stop_sequence"`
	Usage        anthropicUsage     `json:"usage"`
}

type anthropicUsage struct {
	InputTokens  int `json:"input_tokens"`
	OutputTokens int `json:"output_tokens"`
}

type anthropicStreamEvent struct {
	Type  string                    `json:"type"`
	Index int                       `json:"index"`
	Delta anthropicStreamDelta      `json:"delta"`
	Usage *anthropicUsage           `json:"usage,omitempty"`
}

type anthropicStreamDelta struct {
	Type       string `json:"type"`
	Text       string `json:"text,omitempty"`
	StopReason string `json:"stop_reason,omitempty"`
}

func intPtr(i int) *int {
	return &i
}