// Package detect identifies the terminal emulator hosting the current shell
// session and returns an appropriate [terminal.Terminal] implementation.
package detect

import (
	"log/slog"
	"os"
	"strings"

	"github.com/irskep/automate-terminal/exec"
	"github.com/irskep/automate-terminal/terminal"
)

// Detect returns the terminal backend for the current environment, or nil.
func Detect(runner *exec.Runner) terminal.Terminal {
	as := &exec.AppleScript{Runner: runner}
	termProgram := os.Getenv("TERM_PROGRAM")

	// Check for override first.
	if override := os.Getenv("AUTOMATE_TERMINAL_OVERRIDE"); override != "" {
		slog.Debug("Using AUTOMATE_TERMINAL_OVERRIDE", "value", override)
		if t := terminalFromOverride(strings.ToLower(override), runner, as); t != nil {
			slog.Debug("Overridden terminal", "name", t.DisplayName())
			return t
		}
		slog.Warn("Unknown AUTOMATE_TERMINAL_OVERRIDE value", "value", override)
		// Fall through to normal detection.
	}

	// Ordered detection. First match wins.
	for _, t := range allTerminals(runner, as) {
		if t.Detect(termProgram) {
			slog.Debug("Detected terminal", "name", t.DisplayName())
			return t
		}
	}

	slog.Warn("Unsupported terminal", "TERM_PROGRAM", termProgram)
	return nil
}

func terminalFromOverride(name string, runner *exec.Runner, as *exec.AppleScript) terminal.Terminal {
	m := overrideMap(runner, as)
	return m[name]
}

func overrideMap(runner *exec.Runner, as *exec.AppleScript) map[string]terminal.Terminal {
	return map[string]terminal.Terminal{
		"iterm2":       &terminal.ITerm2{AS: as, Runner: runner},
		"terminal":     &terminal.TerminalApp{AS: as, Runner: runner},
		"terminal.app": &terminal.TerminalApp{AS: as, Runner: runner},
		"ghostty":      &terminal.Ghostty{AS: as, Runner: runner},
		"tmux":         &terminal.Tmux{Runner: runner},
		"wezterm":      &terminal.WezTerm{Runner: runner},
		"kitty":        &terminal.Kitty{Runner: runner},
		"guake":        &terminal.Guake{Runner: runner},
		"vscode":       &terminal.VSCode{Runner: runner, Variant: "vscode"},
		"cursor":       &terminal.VSCode{Runner: runner, Variant: "cursor"},
	}
}

// allTerminals returns backends in detection priority order.
func allTerminals(runner *exec.Runner, as *exec.AppleScript) []terminal.Terminal {
	return []terminal.Terminal{
		// tmux first: it nests inside any other terminal.
		&terminal.Tmux{Runner: runner},
		// Guake sets GUAKE_TAB_UUID which is very specific.
		&terminal.Guake{Runner: runner},
		&terminal.WezTerm{Runner: runner},
		&terminal.Kitty{Runner: runner},
		&terminal.ITerm2{AS: as, Runner: runner},
		&terminal.TerminalApp{AS: as, Runner: runner},
		&terminal.Ghostty{AS: as, Runner: runner},
		// Cursor before VSCode since both use TERM_PROGRAM=vscode.
		&terminal.VSCode{Runner: runner, Variant: "cursor"},
		&terminal.VSCode{Runner: runner, Variant: "vscode"},
	}
}
