package exec

import (
	"log/slog"
	"os/exec"
	"strings"
)

// Runner executes shell commands, respecting dry-run mode.
type Runner struct {
	DryRun bool
}

// ExecuteR runs a read-only command and returns whether it succeeded.
// Read-only commands always execute, even in dry-run mode.
func (r *Runner) ExecuteR(cmd []string) bool {
	_, ok := r.run(cmd)
	return ok
}

// ExecuteRWithOutput runs a read-only command and returns its stdout.
// Read-only commands always execute, even in dry-run mode.
func (r *Runner) ExecuteRWithOutput(cmd []string) (string, bool) {
	return r.run(cmd)
}

// ExecuteRW runs a read-write command. In dry-run mode it logs and returns true.
func (r *Runner) ExecuteRW(cmd []string) bool {
	if r.DryRun {
		slog.Info("DRY RUN - Would execute", "cmd", strings.Join(cmd, " "))
		return true
	}
	_, ok := r.run(cmd)
	return ok
}

func (r *Runner) run(cmd []string) (string, bool) {
	if len(cmd) == 0 {
		return "", false
	}
	slog.Debug("Running", "cmd", strings.Join(cmd, " "))
	c := exec.Command(cmd[0], cmd[1:]...)
	out, err := c.Output()
	if err != nil {
		slog.Warn("Command failed", "cmd", strings.Join(cmd, " "), "err", err)
		return "", false
	}
	return strings.TrimSpace(string(out)), true
}
