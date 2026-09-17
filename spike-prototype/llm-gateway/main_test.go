package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestGatewayHealthCheck(t *testing.T) {
	cfg := &Config{
		AllowedModels: []string{"gpt-4o"},
		Port:          "8080",
	}
	gateway, err := NewGateway(cfg)
	if err != nil {
		t.Fatalf("Failed to create gateway: %v", err)
	}
	defer gateway.auditLogger.Close()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	gateway.HealthCheck(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "healthy" {
		t.Errorf("Expected status healthy, got %v", resp["status"])
	}
}

func TestGatewayModelAllowlist(t *testing.T) {
	cfg := &Config{
		AllowedModels: []string{"gpt-4o", "claude-3.5-sonnet"},
		Port:          "8080",
	}
	gateway, err := NewGateway(cfg)
	if err != nil {
		t.Fatalf("Failed to create gateway: %v", err)
	}
	defer gateway.auditLogger.Close()

	if !gateway.isModelAllowed("gpt-4o") {
		t.Error("gpt-4o should be allowed")
	}
	if !gateway.isModelAllowed("claude-3.5-sonnet") {
		t.Error("claude-3.5-sonnet should be allowed")
	}
	if gateway.isModelAllowed("gpt-3.5-turbo") {
		t.Error("gpt-3.5-turbo should not be allowed")
	}
}

func TestTokenBucket(t *testing.T) {
	tb := NewTokenBucket(60) // 60 per minute = 1 per second

	// Should allow first 60 requests
	for i := 0; i < 60; i++ {
		if !tb.Take() {
			t.Errorf("Request %d should be allowed", i)
		}
	}

	// 61st should be denied
	if tb.Take() {
		t.Error("61st request should be denied")
	}

	// Wait for refill
	time.Sleep(1100 * time.Millisecond)
	if !tb.Take() {
		t.Error("Request should be allowed after refill")
	}
}

func TestTokenBudget(t *testing.T) {
	tb := NewTokenBudget(100)

	// Should allow within budget
	if !tb.CheckAndConsume(50) {
		t.Error("First 50 tokens should be allowed")
	}
	if !tb.CheckAndConsume(40) {
		t.Error("Next 40 tokens should be allowed")
	}

	// Should deny over budget
	if tb.CheckAndConsume(20) {
		t.Error("Additional 20 tokens should be denied (over 100)")
	}

	// Remaining should be 10
	if tb.Remaining() != 10 {
		t.Errorf("Expected 10 remaining, got %d", tb.Remaining())
	}
}

func TestPIIRedactor(t *testing.T) {
	patterns := []string{
		`\b\d{3}-\d{2}-\d{4}\b`, // SSN
		`\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`, // Email
	}
	redactor := NewPIIRedactor(patterns)

	// Test SSN
	text := "My SSN is 123-45-6789"
	redacted := redactor.Redact(text)
	if redacted == text {
		t.Error("SSN should be redacted")
	}
	if !bytes.Contains([]byte(redacted), []byte("[REDACTED]")) {
		t.Error("Redacted text should contain [REDACTED]")
	}

	// Test email
	text = "Contact me at user@example.com"
	redacted = redactor.Redact(text)
	if redacted == text {
		t.Error("Email should be redacted")
	}

	// Test ContainsPII
	if !redactor.ContainsPII("SSN: 123-45-6789") {
		t.Error("Should detect SSN")
	}
	if redactor.ContainsPII("No PII here") {
		t.Error("Should not detect PII in clean text")
	}
}

func TestTokenCounter(t *testing.T) {
	tc := &TokenCounter{}

	// Roughly 4 chars per token
	count := tc.Count("Hello world")
	if count != 2 { // 11 chars / 4 = 2
		t.Errorf("Expected ~2 tokens, got %d", count)
	}

	count = tc.Count("This is a longer sentence with more words")
	if count < 8 || count > 10 {
		t.Errorf("Expected ~9 tokens, got %d", count)
	}
}

func TestLLMRequestParsing(t *testing.T) {
	jsonStr := `{
		"model": "gpt-4o",
		"messages": [
			{"role": "user", "content": "Hello"}
		],
		"max_tokens": 100
	}`

	var req LLMRequest
	err := json.Unmarshal([]byte(jsonStr), &req)
	if err != nil {
		t.Fatalf("Failed to unmarshal request: %v", err)
	}

	if req.Model != "gpt-4o" {
		t.Errorf("Expected model gpt-4o, got %s", req.Model)
	}
	if len(req.Messages) != 1 {
		t.Errorf("Expected 1 message, got %d", len(req.Messages))
	}
	if req.MaxTokens != 100 {
		t.Errorf("Expected max_tokens 100, got %d", req.MaxTokens)
	}
}

func TestAuditEntryJSON(t *testing.T) {
	entry := AuditEntry{
		Timestamp: time.Now(),
		RequestID: "test-123",
		AgentID:   "agent-1",
		Model:     "gpt-4o",
		Action:    "allow",
		TokensIn:  100,
		TokensOut: 50,
		LatencyMs: 150,
		Metadata: map[string]string{
			"pii_detected": "false",
		},
	}

	data, err := json.Marshal(entry)
	if err != nil {
		t.Fatalf("Failed to marshal audit entry: %v", err)
	}

	var parsed AuditEntry
	err = json.Unmarshal(data, &parsed)
	if err != nil {
		t.Fatalf("Failed to unmarshal audit entry: %v", err)
	}

	if parsed.RequestID != "test-123" {
		t.Errorf("RequestID mismatch: %s", parsed.RequestID)
	}
	if parsed.TokensIn != 100 {
		t.Errorf("TokensIn mismatch: %d", parsed.TokensIn)
	}
}