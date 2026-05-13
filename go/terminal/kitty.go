package terminal

import (
	"encoding/json"
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

func (k *Kitty) SwitchToSession(sessionID string, pasteScript *string) bool {
	match := "id:" + sessionID
	if !k.Runner.ExecuteRW([]string{"kitten", "@", "focus-window", "--match", match}) {
		return false
	}
	if pasteScript != nil {
		return k.Runner.ExecuteRW([]string{
			"kitten", "@", "send-text", "--match", match, *pasteScript + "\n",
		})
	}
	return true
}

func (k *Kitty) OpenNewTab(dir string, pasteScript *string) bool {
	cmd := []string{"kitten", "@", "launch", "--type=tab", "--cwd", dir}
	if pasteScript != nil {
		cmd = append(cmd, "sh", "-c", "cd "+dir+" && "+*pasteScript)
	}
	return k.Runner.ExecuteRW(cmd)
}

func (k *Kitty) OpenNewWindow(dir string, pasteScript *string) bool {
	cmd := []string{"kitten", "@", "launch", "--type=os-window", "--cwd", dir}
	if pasteScript != nil {
		cmd = append(cmd, "sh", "-c", "cd "+dir+" && "+*pasteScript)
	}
	return k.Runner.ExecuteRW(cmd)
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

func (k *Kitty) RunInActiveSession(command string) bool {
	wid := k.GetCurrentSessionID()
	if wid == nil {
		slog.Error("Could not determine current Kitty window")
		return false
	}
	return k.Runner.ExecuteRW([]string{
		"kitten", "@", "send-text", "--match", "id:" + *wid, command + "\n",
	})
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
	output, ok := k.Runner.ExecuteRWithOutput([]string{"kitten", "@", "ls"})
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
