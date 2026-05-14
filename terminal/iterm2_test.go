package terminal

import (
	"strings"
	"testing"

	"github.com/irskep/automate-terminal/exec"
)

type fakeAppleScript struct {
	scripts []string
}

func (f *fakeAppleScript) toExecAppleScript() *exec.AppleScript {
	// We can't easily fake exec.AppleScript since it's a concrete struct.
	// Instead, test escaping at the exec.Escape level.
	return nil
}

func TestITerm2_ExtractUUID(t *testing.T) {
	tests := []struct {
		in, want string
	}{
		{"w0t0p2:ABC123", "ABC123"},
		{"ABC123", "ABC123"},
		{"w0t0p2:ABC:123", "123"},
		{"", ""},
	}
	for _, tt := range tests {
		got := extractUUID(tt.in)
		if got != tt.want {
			t.Errorf("extractUUID(%q) = %q, want %q", tt.in, got, tt.want)
		}
	}
}

func TestITerm2_AppleScriptEscaping(t *testing.T) {
	// Verify that quotes in paste scripts are properly escaped for AppleScript.
	escaped := exec.Escape(`echo "hello world"`)
	if !strings.Contains(escaped, `\"hello world\"`) {
		t.Errorf("expected escaped quotes, got %q", escaped)
	}
	// Should NOT contain unescaped quotes.
	if strings.Contains(escaped, `"hello world"`) {
		t.Errorf("found unescaped quotes in %q", escaped)
	}

	escaped2 := exec.Escape(`source ".venv/bin/activate"`)
	if !strings.Contains(escaped2, `\".venv/bin/activate\"`) {
		t.Errorf("expected escaped quotes, got %q", escaped2)
	}
}
