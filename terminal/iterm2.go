package terminal

import (
	"fmt"
	"os"
	"strings"

	"github.com/irskep/automate-terminal/exec"
)

// ITerm2 implements Terminal for iTerm2 on macOS.
type ITerm2 struct {
	Base
	AppleScript *exec.AppleScript
	Runner      *exec.Runner
}

func (t *ITerm2) DisplayName() string { return "iTerm2" }

func (t *ITerm2) Detect(termProgram string) bool {
	return termProgram == "iTerm.app" && t.AppleScript.Available()
}

func (t *ITerm2) GetCurrentSessionID() *string {
	id := os.Getenv("ITERM_SESSION_ID")
	if id == "" {
		return nil
	}
	return &id
}

func (t *ITerm2) GetCapabilities() Capabilities {
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

// extractUUID returns the UUID portion of an iTerm2 session ID (w0t0p2:UUID -> UUID).
func extractUUID(sessionID string) string {
	if i := strings.LastIndex(sessionID, ":"); i >= 0 {
		return sessionID[i+1:]
	}
	return sessionID
}

func (t *ITerm2) SessionExists(sessionID string) bool {
	if sessionID == "" {
		return false
	}
	uuid := extractUUID(sessionID)
	script := `
tell application "iTerm2"
    repeat with theWindow in windows
        repeat with theTab in tabs of theWindow
            repeat with theSession in sessions of theTab
                if id of theSession is "` + exec.Escape(uuid) + `" then
                    return true
                end if
            end repeat
        end repeat
    end repeat
    return false
end tell`
	result, ok := t.AppleScript.ExecuteWithResult(script)
	return ok && result == "true"
}

func (t *ITerm2) SwitchToSession(sessionID string, pasteScript *string) error {
	uuid := extractUUID(sessionID)
	script := `
tell application "iTerm2"
    repeat with theWindow in windows
        repeat with theTab in tabs of theWindow
            repeat with theSession in sessions of theTab
                if id of theSession is "` + exec.Escape(uuid) + `" then
                    select theTab
                    select theWindow`
	if pasteScript != nil {
		script += `
                    tell theSession
                        write text "` + exec.Escape(*pasteScript) + `"
                    end tell`
	}
	script += `
                    return
                end if
            end repeat
        end repeat
    end repeat
end tell`
	if err := t.AppleScript.Execute(script); err != nil {
		return fmt.Errorf("iTerm2 AppleScript failed to switch session: %w", err)
	}
	return nil
}

func (t *ITerm2) OpenNewTab(dir string, pasteScript *string) error {
	commands := "cd " + shellQuote(dir)
	if pasteScript != nil {
		commands += "; " + *pasteScript
	}
	script := `
tell application "iTerm2"
    tell current window
        create tab with default profile
        tell current session of current tab
            write text "` + exec.Escape(commands) + `"
        end tell
    end tell
end tell`
	if err := t.AppleScript.Execute(script); err != nil {
		return fmt.Errorf("iTerm2 AppleScript failed to create tab: %w", err)
	}
	return nil
}

func (t *ITerm2) OpenNewWindow(dir string, pasteScript *string) error {
	commands := "cd " + shellQuote(dir)
	if pasteScript != nil {
		commands += "; " + *pasteScript
	}
	script := `
tell application "iTerm2"
    create window with default profile
    tell current session of current window
        write text "` + exec.Escape(commands) + `"
    end tell
end tell`
	if err := t.AppleScript.Execute(script); err != nil {
		return fmt.Errorf("iTerm2 AppleScript failed to create window: %w", err)
	}
	return nil
}

func (t *ITerm2) ListSessions() []Session {
	script := `
tell application "iTerm2"
    set sessionData to ""
    repeat with theWindow in windows
        repeat with theTab in tabs of theWindow
            repeat with theSession in sessions of theTab
                try
                    set sessionId to id of theSession
                    set sessionPath to (variable named "session.path") of theSession
                    if sessionData is not "" then
                        set sessionData to sessionData & return
                    end if
                    set sessionData to sessionData & sessionId & "|" & sessionPath
                on error
                    if sessionData is not "" then
                        set sessionData to sessionData & return
                    end if
                    set sessionData to sessionData & sessionId & "|unknown"
                end try
            end repeat
        end repeat
    end repeat
    return sessionData
end tell`
	output, ok := t.AppleScript.ExecuteWithResult(script)
	if !ok || output == "" {
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

func (t *ITerm2) FindSessionByWorkingDirectory(target string, subdirectoryOK bool) *string {
	return findSessionByDir(t.ListSessions(), target, subdirectoryOK)
}

func (t *ITerm2) RunInActiveSession(command string) error {
	script := `
tell application "iTerm2"
    tell current session of current window
        write text "` + exec.Escape(command) + `"
    end tell
end tell`
	if err := t.AppleScript.Execute(script); err != nil {
		return fmt.Errorf("iTerm2 AppleScript failed to send command to active session: %w", err)
	}
	return nil
}

var _ Terminal = (*ITerm2)(nil)
