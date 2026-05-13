package terminal

import (
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/url"
	"os"
	"strconv"

	"github.com/irskep/automate-terminal/exec"
)

// WezTerm implements Terminal for WezTerm.
type WezTerm struct {
	Base
	Runner *exec.Runner
}

func (w *WezTerm) DisplayName() string { return "WezTerm" }

func (w *WezTerm) Detect(termProgram string) bool {
	return os.Getenv("WEZTERM_PANE") != ""
}

func (w *WezTerm) GetCurrentSessionID() *string {
	pane := os.Getenv("WEZTERM_PANE")
	if pane == "" {
		return nil
	}
	return &pane
}

func (w *WezTerm) GetCapabilities() Capabilities {
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

func (w *WezTerm) SessionExists(sessionID string) bool {
	if sessionID == "" {
		return false
	}
	for _, p := range w.listPanes() {
		if strconv.Itoa(p.PaneID) == sessionID {
			return true
		}
	}
	return false
}

func (w *WezTerm) SwitchToSession(sessionID string, pasteScript *string) error {
	if !w.Runner.ExecuteRW([]string{"wezterm", "cli", "activate-pane", "--pane-id", sessionID}) {
		return fmt.Errorf("wezterm cli activate-pane failed for pane %s", sessionID)
	}
	if pasteScript != nil {
		if !w.Runner.ExecuteRW([]string{
			"wezterm", "cli", "send-text", "--pane-id", sessionID, "--no-paste",
			*pasteScript + "\n",
		}) {
			return errors.New("wezterm cli send-text failed")
		}
	}
	return nil
}

func (w *WezTerm) OpenNewTab(dir string, pasteScript *string) error {
	output, ok := w.Runner.ExecuteRWithOutput(
		[]string{"wezterm", "cli", "spawn", "--cwd", dir},
	)
	if !ok {
		return errors.New("wezterm cli spawn failed")
	}
	if pasteScript != nil {
		paneID := output
		if !w.Runner.ExecuteRW([]string{
			"wezterm", "cli", "send-text", "--pane-id", paneID, "--no-paste",
			*pasteScript + "\n",
		}) {
			return errors.New("wezterm cli send-text failed after creating tab")
		}
	}
	return nil
}

func (w *WezTerm) OpenNewWindow(dir string, pasteScript *string) error {
	output, ok := w.Runner.ExecuteRWithOutput(
		[]string{"wezterm", "cli", "spawn", "--new-window", "--cwd", dir},
	)
	if !ok {
		return errors.New("wezterm cli spawn --new-window failed")
	}
	if pasteScript != nil {
		paneID := output
		if !w.Runner.ExecuteRW([]string{
			"wezterm", "cli", "send-text", "--pane-id", paneID, "--no-paste",
			*pasteScript + "\n",
		}) {
			return errors.New("wezterm cli send-text failed after creating window")
		}
	}
	return nil
}

func (w *WezTerm) ListSessions() []Session {
	var sessions []Session
	for _, p := range w.listPanes() {
		cwd := parseCwdURI(p.Cwd)
		if cwd == "" {
			continue
		}
		sessions = append(sessions, Session{
			SessionID:        strconv.Itoa(p.PaneID),
			WorkingDirectory: cwd,
		})
	}
	return sessions
}

func (w *WezTerm) FindSessionByWorkingDirectory(target string, subdirectoryOK bool) *string {
	return findSessionByDir(w.ListSessions(), target, subdirectoryOK)
}

func (w *WezTerm) RunInActiveSession(command string) error {
	pane := w.GetCurrentSessionID()
	if pane == nil {
		return errors.New("could not determine current WezTerm pane (WEZTERM_PANE not set)")
	}
	if !w.Runner.ExecuteRW([]string{
		"wezterm", "cli", "send-text", "--pane-id", *pane, "--no-paste",
		command + "\n",
	}) {
		return errors.New("wezterm cli send-text failed")
	}
	return nil
}

type weztermPane struct {
	PaneID int    `json:"pane_id"`
	Cwd    string `json:"cwd"`
}

func (w *WezTerm) listPanes() []weztermPane {
	output, ok := w.Runner.ExecuteRWithOutput(
		[]string{"wezterm", "cli", "list", "--format", "json"},
	)
	if !ok {
		return nil
	}
	var panes []weztermPane
	if err := json.Unmarshal([]byte(output), &panes); err != nil {
		slog.Error("Failed to parse WezTerm pane list", "err", err)
		return nil
	}
	return panes
}

var _ Terminal = (*WezTerm)(nil)

// parseCwdURI extracts a filesystem path from a file:// URI or plain path.
func parseCwdURI(raw string) string {
	if raw == "" {
		return ""
	}
	if len(raw) > 7 && raw[:7] == "file://" {
		u, err := url.Parse(raw)
		if err != nil {
			return raw
		}
		return u.Path
	}
	return raw
}
