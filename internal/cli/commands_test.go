package cli

import (
	"encoding/json"
	"os"
	"strings"
	"testing"

	"github.com/irskep/automate-terminal/terminal"
)

// withOverride sets AUTOMATE_TERMINAL_OVERRIDE for the duration of a test,
// so detection succeeds in environments with no real terminal (like CI).
func withOverride(t *testing.T, value string) {
	t.Helper()
	orig := os.Getenv("AUTOMATE_TERMINAL_OVERRIDE")
	os.Setenv("AUTOMATE_TERMINAL_OVERRIDE", value)
	t.Cleanup(func() { os.Setenv("AUTOMATE_TERMINAL_OVERRIDE", orig) })
}

func TestCmdCheck_JSON(t *testing.T) {
	withOverride(t, "tmux")
	got := captureStdout(t, func() {
		rc := cmdCheck([]string{"--output=json"}, "1.0.0")
		if rc != 0 {
			t.Errorf("expected exit 0, got %d", rc)
		}
	})
	var parsed map[string]any
	if err := json.Unmarshal([]byte(got), &parsed); err != nil {
		t.Fatalf("invalid JSON: %v\noutput: %s", err, got)
	}
	if parsed["version"] != "1.0.0" {
		t.Errorf("expected version=1.0.0, got %v", parsed["version"])
	}
	if _, ok := parsed["capabilities"]; !ok {
		t.Error("expected capabilities in output")
	}
}

func TestCmdCheck_UnsupportedTerminal_JSON(t *testing.T) {
	vars := []string{
		"AUTOMATE_TERMINAL_OVERRIDE", "TMUX", "GUAKE_TAB_UUID",
		"WEZTERM_PANE", "KITTY_WINDOW_ID", "CURSOR_TRACE_ID",
	}
	originals := make(map[string]string)
	for _, v := range vars {
		originals[v] = os.Getenv(v)
		os.Unsetenv(v)
	}
	origTP := os.Getenv("TERM_PROGRAM")
	os.Setenv("TERM_PROGRAM", "unsupported")
	t.Cleanup(func() {
		for k, v := range originals {
			os.Setenv(k, v)
		}
		os.Setenv("TERM_PROGRAM", origTP)
	})

	got := captureStdout(t, func() {
		rc := cmdCheck([]string{"--output=json"}, "1.0.0")
		if rc != 1 {
			t.Errorf("expected exit 1, got %d", rc)
		}
	})
	var parsed map[string]any
	if err := json.Unmarshal([]byte(got), &parsed); err != nil {
		t.Fatalf("invalid JSON: %v\noutput: %s", err, got)
	}
	if parsed["terminal"] != "unknown" {
		t.Errorf("expected terminal=unknown, got %v", parsed["terminal"])
	}
	if _, ok := parsed["error"]; !ok {
		t.Error("expected error in output")
	}
}

func TestCmdCheck_TextOutput(t *testing.T) {
	withOverride(t, "tmux")
	got := captureStdout(t, func() {
		rc := cmdCheck([]string{"--output=text"}, "1.0.0")
		if rc != 0 {
			t.Errorf("expected exit 0, got %d", rc)
		}
	})
	if !strings.Contains(got, "Terminal:") {
		t.Errorf("expected 'Terminal:' in text output, got %q", got)
	}
	if !strings.Contains(got, "Capabilities:") {
		t.Errorf("expected 'Capabilities:' in text output")
	}
}

func TestCmdNewTab_MissingDir(t *testing.T) {
	got := captureStderr(t, func() {
		rc := cmdNewTab([]string{"--output=text"})
		if rc != 1 {
			t.Errorf("expected exit 1, got %d", rc)
		}
	})
	if !strings.Contains(got, "Missing required argument") {
		t.Errorf("expected missing argument error, got %q", got)
	}
}

func TestCmdNewWindow_MissingDir(t *testing.T) {
	got := captureStderr(t, func() {
		rc := cmdNewWindow([]string{"--output=text"})
		if rc != 1 {
			t.Errorf("expected exit 1, got %d", rc)
		}
	})
	if !strings.Contains(got, "Missing required argument") {
		t.Errorf("expected missing argument error, got %q", got)
	}
}

func TestCmdSwitchTo_MissingArgs(t *testing.T) {
	withOverride(t, "tmux")
	got := captureStderr(t, func() {
		rc := cmdSwitchTo([]string{"--output=text"})
		if rc != 1 {
			t.Errorf("expected exit 1, got %d", rc)
		}
	})
	if !strings.Contains(got, "Must provide") {
		t.Errorf("expected 'Must provide' error, got %q", got)
	}
}

func TestCmdRunInActiveSession_MissingScript(t *testing.T) {
	got := captureStderr(t, func() {
		rc := cmdRunInActiveSession([]string{"--output=text"})
		if rc != 1 {
			t.Errorf("expected exit 1, got %d", rc)
		}
	})
	if !strings.Contains(got, "Missing required argument") {
		t.Errorf("expected missing argument error, got %q", got)
	}
}

func TestPasteScriptExecuted(t *testing.T) {
	capsWithPaste := terminal.Capabilities{CanPasteCommands: true}
	capsWithoutPaste := terminal.Capabilities{CanPasteCommands: false}

	if v := pasteScriptExecuted(nil, capsWithPaste); v != nil {
		t.Errorf("expected nil when no paste script, got %v", *v)
	}

	script := "echo hi"
	v := pasteScriptExecuted(&script, capsWithPaste)
	if v == nil || !*v {
		t.Error("expected true when terminal supports paste")
	}

	v = pasteScriptExecuted(&script, capsWithoutPaste)
	if v == nil || *v {
		t.Error("expected false when terminal doesn't support paste")
	}
}
