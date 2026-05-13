package terminal

import (
	"log/slog"
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
	output, ok := t.Runner.ExecuteRWithOutput(
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

func (t *Tmux) SwitchToSession(sessionID string, pasteScript *string) bool {
	// Get the window containing this pane.
	windowID, ok := t.Runner.ExecuteRWithOutput(
		[]string{"tmux", "display-message", "-p", "-t", sessionID, "-F", "#{window_id}"},
	)
	if !ok {
		slog.Error("Failed to get window for pane", "pane", sessionID)
		return false
	}
	if !t.Runner.ExecuteRW([]string{"tmux", "select-window", "-t", windowID}) {
		return false
	}
	if !t.Runner.ExecuteRW([]string{"tmux", "select-pane", "-t", sessionID}) {
		return false
	}
	if pasteScript != nil {
		return t.Runner.ExecuteRW(
			[]string{"tmux", "send-keys", "-t", sessionID, *pasteScript, "Enter"},
		)
	}
	return true
}

func (t *Tmux) OpenNewTab(dir string, pasteScript *string) bool {
	cmd := []string{"tmux", "new-window", "-c", dir}
	if pasteScript != nil {
		cmd = append(cmd, *pasteScript)
	}
	return t.Runner.ExecuteRW(cmd)
}

func (t *Tmux) OpenNewWindow(dir string, pasteScript *string) bool {
	cmd := []string{"tmux", "new-session", "-d", "-c", dir}
	if !t.Runner.ExecuteRW(cmd) {
		return false
	}
	if pasteScript != nil {
		sid, ok := t.Runner.ExecuteRWithOutput(
			[]string{"tmux", "display-message", "-p", "-t", "#{session_id}"},
		)
		if ok {
			t.Runner.ExecuteRW(
				[]string{"tmux", "send-keys", "-t", sid, *pasteScript, "Enter"},
			)
		}
	}
	return true
}

func (t *Tmux) ListSessions() []Session {
	output, ok := t.Runner.ExecuteRWithOutput(
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

func (t *Tmux) RunInActiveSession(command string) bool {
	pane := t.GetCurrentSessionID()
	if pane == nil {
		slog.Error("Could not determine current tmux pane")
		return false
	}
	return t.Runner.ExecuteRW(
		[]string{"tmux", "send-keys", "-t", *pane, command, "Enter"},
	)
}

var _ Terminal = (*Tmux)(nil)
