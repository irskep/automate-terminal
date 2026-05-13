package detect

import (
	"log/slog"
	"os"
	"runtime"
	"strings"

	"github.com/stevelandeyasleep/automate-terminal/internal/exec"
	"github.com/stevelandeyasleep/automate-terminal/internal/terminal"
)

// Detect returns the terminal backend for the current environment, or nil.
func Detect(runner *exec.Runner) terminal.Terminal {
	as := &exec.AppleScript{Runner: runner}
	termProgram := os.Getenv("TERM_PROGRAM")
	platform := runtime.GOOS

	// Check for override first.
	if override := os.Getenv("AUTOMATE_TERMINAL_OVERRIDE"); override != "" {
		slog.Debug("Using AUTOMATE_TERMINAL_OVERRIDE", "value", override)
		if t := terminalFromOverride(strings.ToLower(override), runner, as); t != nil {
			return t
		}
		slog.Warn("Unknown AUTOMATE_TERMINAL_OVERRIDE value", "value", override)
	}

	// Ordered detection. First match wins.
	candidates := allTerminals(runner, as)
	for _, t := range candidates {
		if t.Detect(termProgram, platform) {
			slog.Debug("Detected terminal", "name", t.DisplayName())
			return t
		}
	}

	slog.Warn("Unsupported terminal", "TERM_PROGRAM", termProgram, "platform", platform)
	return nil
}

func terminalFromOverride(name string, runner *exec.Runner, as *exec.AppleScript) terminal.Terminal {
	// TODO: return the matching backend
	_ = runner
	_ = as
	_ = name
	return nil
}

func allTerminals(runner *exec.Runner, as *exec.AppleScript) []terminal.Terminal {
	// TODO: return all backends in detection order
	_ = runner
	_ = as
	return nil
}
