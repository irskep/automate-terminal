package cli

import (
	"encoding/json"
	"io"
	"os"
	"strings"
	"testing"
)

func captureStdout(t *testing.T, fn func()) string {
	t.Helper()
	r, w, _ := os.Pipe()
	old := os.Stdout
	os.Stdout = w
	fn()
	w.Close()
	os.Stdout = old
	out, _ := io.ReadAll(r)
	return string(out)
}

func captureStderr(t *testing.T, fn func()) string {
	t.Helper()
	r, w, _ := os.Pipe()
	old := os.Stderr
	os.Stderr = w
	fn()
	w.Close()
	os.Stderr = old
	out, _ := io.ReadAll(r)
	return string(out)
}

func TestOutput_JSON(t *testing.T) {
	data := map[string]any{"key": "value"}
	got := captureStdout(t, func() { Output("json", data, "ignored") })
	var parsed map[string]any
	if err := json.Unmarshal([]byte(got), &parsed); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if parsed["key"] != "value" {
		t.Errorf("expected key=value, got %v", parsed)
	}
}

func TestOutput_Text(t *testing.T) {
	got := captureStdout(t, func() { Output("text", nil, "hello world") })
	if strings.TrimSpace(got) != "hello world" {
		t.Errorf("expected 'hello world', got %q", got)
	}
}

func TestOutput_None(t *testing.T) {
	got := captureStdout(t, func() { Output("none", map[string]any{"key": "value"}, "hello") })
	if got != "" {
		t.Errorf("expected empty output for none, got %q", got)
	}
}

func TestOutputError_JSON(t *testing.T) {
	got := captureStderr(t, func() { OutputError("json", "test error", nil) })
	var parsed map[string]any
	if err := json.Unmarshal([]byte(got), &parsed); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if parsed["success"] != false {
		t.Error("expected success=false")
	}
	if parsed["error"] != "test error" {
		t.Errorf("expected error='test error', got %v", parsed["error"])
	}
}

func TestOutputError_Text(t *testing.T) {
	got := captureStderr(t, func() { OutputError("text", "test error", nil) })
	if !strings.Contains(got, "Error: test error") {
		t.Errorf("expected 'Error: test error', got %q", got)
	}
}

func TestOutputError_JSON_WithExtraData(t *testing.T) {
	got := captureStderr(t, func() {
		OutputError("json", "test error", map[string]any{"terminal": "iTerm2", "code": 123})
	})
	var parsed map[string]any
	if err := json.Unmarshal([]byte(got), &parsed); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if parsed["success"] != false {
		t.Error("expected success=false")
	}
	if parsed["terminal"] != "iTerm2" {
		t.Errorf("expected terminal=iTerm2, got %v", parsed["terminal"])
	}
	if parsed["code"] != float64(123) {
		t.Errorf("expected code=123, got %v", parsed["code"])
	}
}
