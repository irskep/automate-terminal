// Package exec runs external commands (shell processes, osascript, CLI tools)
// with support for dry-run mode and structured logging.
package exec

import (
	"fmt"
	"log/slog"
	"os/exec"
	"strings"
)

// Runner executes shell commands, respecting dry-run mode.
type Runner struct {
	DryRun bool
}

// Run executes a read-only command and returns whether it succeeded.
// Read-only commands always execute, even in dry-run mode.
func (r *Runner) Run(cmd []string) bool {
	_, err := r.run(cmd)
	return err == nil
}

// RunOutput executes a read-only command and returns its trimmed stdout.
// Read-only commands always execute, even in dry-run mode.
func (r *Runner) RunOutput(cmd []string) (string, bool) {
	out, err := r.run(cmd)
	if err != nil {
		return "", false
	}
	return out, true
}

// RunMutating executes a command that changes state. In dry-run mode it logs
// the command and returns nil without executing.
func (r *Runner) RunMutating(cmd []string) error {
	if r.DryRun {
		slog.Info("DRY RUN - Would execute", "cmd", strings.Join(cmd, " "))
		return nil
	}
	_, err := r.run(cmd)
	return err
}

func (r *Runner) run(cmd []string) (string, error) {
	if len(cmd) == 0 {
		return "", fmt.Errorf("empty command")
	}
	slog.Debug("Running", "cmd", strings.Join(cmd, " "))
	c := exec.Command(cmd[0], cmd[1:]...)
	out, err := c.Output()
	if err != nil {
		stderr := ""
		if exitErr, ok := err.(*exec.ExitError); ok && len(exitErr.Stderr) > 0 {
			stderr = strings.TrimSpace(string(exitErr.Stderr))
		}
		if stderr != "" {
			slog.Warn("Command failed", "cmd", strings.Join(cmd, " "), "err", err, "stderr", stderr)
		} else {
			slog.Warn("Command failed", "cmd", strings.Join(cmd, " "), "err", err)
		}
		return "", fmt.Errorf("%s failed: %w", cmd[0], err)
	}
	return strings.TrimSpace(string(out)), nil
}
