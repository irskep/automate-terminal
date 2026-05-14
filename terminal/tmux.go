package terminal

import (
	"fmt"
	"os"
	"strings"

	"github.com/irskep/automate-terminal/exec"
)

// Tmux implements Terminal for tmux sessions.
type Tmux struct {
	Base
	Runner *exec.Runner
}

func (t *Tmux) DisplayName() string { return "tmux" }

func (t *Tmux) Detect(termProgram string) bool {
	return os.Getenv("TMUX") != ""
}

func (t *Tmux) GetCurrentSessionID() *string {
	pane := os.Getenv("TMUX_PANE")
	if pane == "" {
		return nil
	}
	return &pane
}

func (t *Tmux) GetCapabilities() Capabilities {
	return Capabilities{
		CanCreateTabs:             true,
		CanCreateWindows:          true,
		CanListSessions:           true,
		CanSwitchToSession:        true,
		CanDetectSessionID:        true,
		CanDetectWorkingDirectory: true,
		CanPasteCommands:          true,
		CanRunInActiveSession:     true,
	}
}

func (t *Tmux) SessionExists(sessionID string) bool {
	if sessionID == "" {
		return false
	}
	output, ok := t.Runner.RunOutput(
		[]string{"tmux", "list-panes", "-a", "-F", "#{pane_id}"},
	)
	if !ok {
		return false
	}
	for _, line := range strings.Split(output, "\n") {
		if strings.TrimSpace(line) == sessionID {
			return true
		}
	}
	return false
}

func (t *Tmux) SwitchToSession(sessionID string, pasteScript *string) error {
	windowID, ok := t.Runner.RunOutput(
		[]string{"tmux", "display-message", "-p", "-t", sessionID, "-F", "#{window_id}"},
	)
	if !ok {
		return fmt.Errorf("failed to get window for tmux pane %s", sessionID)
	}
	if err := t.Runner.RunMutating([]string{"tmux", "select-window", "-t", windowID}); err != nil {
		return fmt.Errorf("tmux select-window failed for window %s: %w", windowID, err)
	}
	if err := t.Runner.RunMutating([]string{"tmux", "select-pane", "-t", sessionID}); err != nil {
		return fmt.Errorf("tmux select-pane failed for pane %s: %w", sessionID, err)
	}
	if pasteScript != nil {
		if err := t.Runner.RunMutating([]string{"tmux", "send-keys", "-t", sessionID, *pasteScript, "Enter"}); err != nil {
			return fmt.Errorf("tmux send-keys failed: %w", err)
		}
	}
	return nil
}

func (t *Tmux) OpenNewTab(dir string, pasteScript *string) error {
	cmd := []string{"tmux", "new-window", "-c", dir}
	if pasteScript != nil {
		cmd = append(cmd, *pasteScript)
	}
	if err := t.Runner.RunMutating(cmd); err != nil {
		return fmt.Errorf("tmux new-window failed: %w", err)
	}
	return nil
}

func (t *Tmux) OpenNewWindow(dir string, pasteScript *string) error {
	if err := t.Runner.RunMutating([]string{"tmux", "new-session", "-d", "-c", dir}); err != nil {
		return fmt.Errorf("tmux new-session failed: %w", err)
	}
	if pasteScript != nil {
		sid, ok := t.Runner.RunOutput(
			[]string{"tmux", "display-message", "-p", "-t", "#{session_id}"},
		)
		if ok {
			_ = t.Runner.RunMutating(
				[]string{"tmux", "send-keys", "-t", sid, *pasteScript, "Enter"},
			)
		}
	}
	return nil
}

func (t *Tmux) ListSessions() []Session {
	output, ok := t.Runner.RunOutput(
		[]string{"tmux", "list-panes", "-a", "-F", "#{pane_id}|#{pane_current_path}"},
	)
	if !ok {
		return nil
	}
	var sessions []Session
	for _, line := range strings.Split(output, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		parts := strings.SplitN(line, "|", 2)
		if len(parts) != 2 {
			continue
		}
		sessions = append(sessions, Session{
			SessionID:        strings.TrimSpace(parts[0]),
			WorkingDirectory: strings.TrimSpace(parts[1]),
		})
	}
	return sessions
}

func (t *Tmux) FindSessionByWorkingDirectory(target string, subdirectoryOK bool) *string {
	return findSessionByDir(t.ListSessions(), target, subdirectoryOK)
}

func (t *Tmux) RunInActiveSession(command string) error {
	pane := t.GetCurrentSessionID()
	if pane == nil {
		return fmt.Errorf("could not determine current tmux pane (TMUX_PANE not set)")
	}
	if err := t.Runner.RunMutating([]string{"tmux", "send-keys", "-t", *pane, command, "Enter"}); err != nil {
		return fmt.Errorf("tmux send-keys failed: %w", err)
	}
	return nil
}

var _ Terminal = (*Tmux)(nil)
