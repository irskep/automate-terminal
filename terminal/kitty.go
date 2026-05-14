package terminal

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"strconv"

	"github.com/irskep/automate-terminal/exec"
)

// Kitty implements Terminal for Kitty.
// Requires allow_remote_control=yes in kitty.conf.
type Kitty struct {
	Base
	Runner *exec.Runner
}

func (k *Kitty) DisplayName() string { return "Kitty" }

func (k *Kitty) Detect(termProgram string) bool {
	return os.Getenv("KITTY_WINDOW_ID") != ""
}

func (k *Kitty) GetCurrentSessionID() *string {
	id := os.Getenv("KITTY_WINDOW_ID")
	if id == "" {
		return nil
	}
	return &id
}

func (k *Kitty) GetCapabilities() Capabilities {
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

func (k *Kitty) SessionExists(sessionID string) bool {
	if sessionID == "" {
		return false
	}
	for _, w := range k.getAllWindows() {
		if strconv.Itoa(w.ID) == sessionID {
			return true
		}
	}
	return false
}

func (k *Kitty) SwitchToSession(sessionID string, pasteScript *string) error {
	match := "id:" + sessionID
	if err := k.Runner.RunMutating([]string{"kitten", "@", "focus-window", "--match", match}); err != nil {
		return fmt.Errorf("kitten @ focus-window failed for window %s (is allow_remote_control enabled in kitty.conf?): %w", sessionID, err)
	}
	if pasteScript != nil {
		if err := k.Runner.RunMutating([]string{
			"kitten", "@", "send-text", "--match", match, *pasteScript + "\n",
		}); err != nil {
			return fmt.Errorf("kitten @ send-text failed: %w", err)
		}
	}
	return nil
}

func (k *Kitty) OpenNewTab(dir string, pasteScript *string) error {
	cmd := []string{"kitten", "@", "launch", "--type=tab", "--cwd", dir}
	if pasteScript != nil {
		cmd = append(cmd, "sh", "-c", "cd "+shellQuote(dir)+" && "+*pasteScript)
	}
	if err := k.Runner.RunMutating(cmd); err != nil {
		return fmt.Errorf("kitten @ launch --type=tab failed (is allow_remote_control enabled in kitty.conf?): %w", err)
	}
	return nil
}

func (k *Kitty) OpenNewWindow(dir string, pasteScript *string) error {
	cmd := []string{"kitten", "@", "launch", "--type=os-window", "--cwd", dir}
	if pasteScript != nil {
		cmd = append(cmd, "sh", "-c", "cd "+shellQuote(dir)+" && "+*pasteScript)
	}
	if err := k.Runner.RunMutating(cmd); err != nil {
		return fmt.Errorf("kitten @ launch --type=os-window failed (is allow_remote_control enabled in kitty.conf?): %w", err)
	}
	return nil
}

func (k *Kitty) ListSessions() []Session {
	var sessions []Session
	for _, w := range k.getAllWindows() {
		if w.Cwd == "" {
			continue
		}
		sessions = append(sessions, Session{
			SessionID:        strconv.Itoa(w.ID),
			WorkingDirectory: w.Cwd,
		})
	}
	return sessions
}

func (k *Kitty) FindSessionByWorkingDirectory(target string, subdirectoryOK bool) *string {
	return findSessionByDir(k.ListSessions(), target, subdirectoryOK)
}

func (k *Kitty) RunInActiveSession(command string) error {
	wid := k.GetCurrentSessionID()
	if wid == nil {
		return fmt.Errorf("could not determine current Kitty window (KITTY_WINDOW_ID not set)")
	}
	if err := k.Runner.RunMutating([]string{
		"kitten", "@", "send-text", "--match", "id:" + *wid, command + "\n",
	}); err != nil {
		return fmt.Errorf("kitten @ send-text failed (is allow_remote_control enabled in kitty.conf?): %w", err)
	}
	return nil
}

var _ Terminal = (*Kitty)(nil)

type kittyWindow struct {
	ID  int    `json:"id"`
	Cwd string `json:"cwd"`
}

type kittyTab struct {
	Windows []kittyWindow `json:"windows"`
}

type kittyOSWindow struct {
	Tabs []kittyTab `json:"tabs"`
}

func (k *Kitty) getAllWindows() []kittyWindow {
	output, ok := k.Runner.RunOutput([]string{"kitten", "@", "ls"})
	if !ok {
		return nil
	}
	var osWindows []kittyOSWindow
	if err := json.Unmarshal([]byte(output), &osWindows); err != nil {
		slog.Error("Failed to parse Kitty window list", "err", err)
		return nil
	}
	var all []kittyWindow
	for _, osw := range osWindows {
		for _, tab := range osw.Tabs {
			all = append(all, tab.Windows...)
		}
	}
	return all
}
