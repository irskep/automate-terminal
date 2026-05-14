package exec

import (
	"log/slog"
	"os/exec"
	"strings"
)

// AppleScript runs AppleScript via osascript. Only functional when osascript
// is available on PATH.
type AppleScript struct {
	Runner *Runner
}

// Available reports whether osascript is on PATH.
func (a *AppleScript) Available() bool {
	_, err := exec.LookPath("osascript")
	return err == nil
}

// Execute runs an AppleScript and returns whether it succeeded.
func (a *AppleScript) Execute(script string) bool {
	if !a.Available() {
		slog.Warn("osascript not found on PATH")
		return false
	}
	if a.Runner.DryRun {
		slog.Info("DRY RUN - Would execute AppleScript", "script", script)
		return true
	}
	return a.Runner.ExecuteR([]string{"osascript", "-e", script})
}

// ExecuteWithResult runs an AppleScript and returns its output.
// Executes even in dry-run mode since it is a read-only query.
func (a *AppleScript) ExecuteWithResult(script string) (string, bool) {
	if !a.Available() {
		slog.Warn("osascript not found on PATH")
		return "", false
	}
	if a.Runner.DryRun {
		slog.Debug("DRY RUN - Executing query AppleScript", "script", script)
	}
	return a.Runner.ExecuteRWithOutput([]string{"osascript", "-e", script})
}

// Escape escapes a string for embedding in AppleScript double-quoted strings.
func Escape(val string) string {
	val = strings.ReplaceAll(val, `\`, `\\`)
	val = strings.ReplaceAll(val, `"`, `\"`)
	return val
}
