package detect

import (
	"os"
	"testing"

	"github.com/irskep/automate-terminal/exec"
)

func TestDetect_OverrideRespected(t *testing.T) {
	orig := os.Getenv("AUTOMATE_TERMINAL_OVERRIDE")
	defer os.Setenv("AUTOMATE_TERMINAL_OVERRIDE", orig)

	os.Setenv("AUTOMATE_TERMINAL_OVERRIDE", "tmux")
	runner := &exec.Runner{}
	term := Detect(runner)
	if term == nil {
		t.Fatal("expected terminal from override")
	}
	if term.DisplayName() != "tmux" {
		t.Errorf("expected tmux, got %s", term.DisplayName())
	}
}

func TestDetect_OverrideCaseInsensitive(t *testing.T) {
	orig := os.Getenv("AUTOMATE_TERMINAL_OVERRIDE")
	defer os.Setenv("AUTOMATE_TERMINAL_OVERRIDE", orig)

	os.Setenv("AUTOMATE_TERMINAL_OVERRIDE", "TMUX")
	runner := &exec.Runner{}
	term := Detect(runner)
	if term == nil {
		t.Fatal("expected terminal from override")
	}
	if term.DisplayName() != "tmux" {
		t.Errorf("expected tmux, got %s", term.DisplayName())
	}
}

func TestDetect_OverrideUnknownFallsThrough(t *testing.T) {
	origOverride := os.Getenv("AUTOMATE_TERMINAL_OVERRIDE")
	origTmux := os.Getenv("TMUX")
	defer func() {
		os.Setenv("AUTOMATE_TERMINAL_OVERRIDE", origOverride)
		os.Setenv("TMUX", origTmux)
	}()

	os.Setenv("AUTOMATE_TERMINAL_OVERRIDE", "unknown_terminal")
	os.Setenv("TMUX", "/tmp/tmux-501/default,12345,0")

	runner := &exec.Runner{}
	term := Detect(runner)
	if term == nil {
		t.Fatal("expected fallthrough to tmux detection")
	}
	if term.DisplayName() != "tmux" {
		t.Errorf("expected tmux from fallthrough, got %s", term.DisplayName())
	}
}

func TestDetect_UnsupportedReturnsNil(t *testing.T) {
	// Clear all terminal env vars to force unsupported.
	vars := []string{
		"AUTOMATE_TERMINAL_OVERRIDE", "TMUX", "GUAKE_TAB_UUID",
		"WEZTERM_PANE", "KITTY_WINDOW_ID", "TERM_PROGRAM",
		"ITERM_SESSION_ID", "CURSOR_TRACE_ID",
	}
	originals := make(map[string]string)
	for _, v := range vars {
		originals[v] = os.Getenv(v)
		os.Unsetenv(v)
	}
	defer func() {
		for k, v := range originals {
			os.Setenv(k, v)
		}
	}()

	runner := &exec.Runner{}
	term := Detect(runner)
	if term != nil {
		t.Errorf("expected nil for unsupported terminal, got %s", term.DisplayName())
	}
}
