package terminal

import (
	"os"
	"testing"

	"github.com/irskep/automate-terminal/exec"
)

func TestTmuxDetect(t *testing.T) {
	tmux := &Tmux{Runner: &exec.Runner{}}

	orig := os.Getenv("TMUX")
	defer os.Setenv("TMUX", orig)

	os.Setenv("TMUX", "/tmp/tmux-501/default,12345,0")
	if !tmux.Detect("") {
		t.Error("expected tmux detected when TMUX is set")
	}

	os.Unsetenv("TMUX")
	if tmux.Detect("") {
		t.Error("expected tmux not detected when TMUX is unset")
	}
}

func TestWeztermDetect(t *testing.T) {
	wez := &WezTerm{Runner: &exec.Runner{}}

	orig := os.Getenv("WEZTERM_PANE")
	defer os.Setenv("WEZTERM_PANE", orig)

	os.Setenv("WEZTERM_PANE", "0")
	if !wez.Detect("") {
		t.Error("expected WezTerm detected when WEZTERM_PANE is set")
	}

	os.Unsetenv("WEZTERM_PANE")
	if wez.Detect("") {
		t.Error("expected WezTerm not detected when WEZTERM_PANE is unset")
	}
}

func TestKittyDetect(t *testing.T) {
	kitty := &Kitty{Runner: &exec.Runner{}}

	orig := os.Getenv("KITTY_WINDOW_ID")
	defer os.Setenv("KITTY_WINDOW_ID", orig)

	os.Setenv("KITTY_WINDOW_ID", "1")
	if !kitty.Detect("") {
		t.Error("expected Kitty detected when KITTY_WINDOW_ID is set")
	}

	os.Unsetenv("KITTY_WINDOW_ID")
	if kitty.Detect("") {
		t.Error("expected Kitty not detected when KITTY_WINDOW_ID is unset")
	}
}

func TestVSCodeDetect(t *testing.T) {
	origCursor := os.Getenv("CURSOR_TRACE_ID")
	defer os.Setenv("CURSOR_TRACE_ID", origCursor)

	vscode := &VSCode{Runner: &exec.Runner{}, Variant: "vscode"}
	cursor := &VSCode{Runner: &exec.Runner{}, Variant: "cursor"}

	// VSCode: TERM_PROGRAM=vscode, no CURSOR_TRACE_ID
	os.Unsetenv("CURSOR_TRACE_ID")
	if !vscode.Detect("vscode") {
		t.Error("expected VSCode detected")
	}
	if cursor.Detect("vscode") {
		t.Error("expected Cursor not detected without CURSOR_TRACE_ID")
	}

	// Cursor: TERM_PROGRAM=vscode, with CURSOR_TRACE_ID
	os.Setenv("CURSOR_TRACE_ID", "some-id")
	if vscode.Detect("vscode") {
		t.Error("expected VSCode not detected when CURSOR_TRACE_ID is set")
	}
	if !cursor.Detect("vscode") {
		t.Error("expected Cursor detected")
	}

	// Neither: wrong TERM_PROGRAM
	if vscode.Detect("iTerm.app") {
		t.Error("expected VSCode not detected for iTerm.app")
	}
}
