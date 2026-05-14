package terminal

import (
	"errors"
	"strings"

	"github.com/irskep/automate-terminal/exec"
)

// TerminalApp implements Terminal for macOS Terminal.app.
type TerminalApp struct {
	Base
	AppleScript *exec.AppleScript
	Runner      *exec.Runner
}

func (t *TerminalApp) DisplayName() string { return "Apple Terminal.app" }

func (t *TerminalApp) Detect(termProgram string) bool {
	return termProgram == "Apple_Terminal" && t.AppleScript.Available()
}

func (t *TerminalApp) GetCapabilities() Capabilities {
	return Capabilities{
		CanCreateTabs:             true,
		CanCreateWindows:          true,
		CanListSessions:           true,
		CanSwitchToSession:        true,
		CanDetectSessionID:        false,
		CanDetectWorkingDirectory: true,
		CanPasteCommands:          true,
		CanRunInActiveSession:     true,
	}
}

func (t *TerminalApp) SwitchToSessionByWorkingDirectory(dir string, pasteScript *string) error {
	escaped := exec.Escape(dir)

	findScript := `
tell application "Terminal"
    repeat with theWindow in windows
        repeat with theTab in tabs of theWindow
            try
                set tabTTY to tty of theTab
                set shellCmd to "lsof " & tabTTY & " | grep -E '(zsh|bash|fish|osh|nu|pwsh|sh)' | head -1 | awk '{print $2}'"
                set shellPid to do shell script shellCmd
                if shellPid is not "" then
                    set cwdCmd to "lsof -p " & shellPid & " | grep cwd | awk '{print $9}'"
                    set workingDir to do shell script cwdCmd
                    if workingDir is "` + escaped + `" then
                        return name of theWindow
                    end if
                end if
            end try
        end repeat
    end repeat
    return ""
end tell`
	windowName, ok := t.AppleScript.ExecuteWithResult(findScript)
	if !ok || windowName == "" {
		return errors.New("no Terminal.app window found with that working directory")
	}

	if pasteScript != nil {
		t.AppleScript.Execute(`
tell application "Terminal"
    do script "` + exec.Escape(*pasteScript) + `" in front window
end tell`)
	}

	escapedName := exec.Escape(windowName)
	switchScript := `
tell application "System Events"
    tell process "Terminal"
        try
            click menu item "` + escapedName + `" of menu "Window" of menu bar 1
            return "success"
        on error errMsg
            return "error: " & errMsg
        end try
    end tell
end tell`
	result, ok := t.AppleScript.ExecuteWithResult(switchScript)
	if !ok || !strings.HasPrefix(result, "success") {
		return errors.New("failed to switch Terminal.app window (missing accessibility permissions? grant accessibility permissions to the calling application in System Settings -> Privacy & Security -> Accessibility)")
	}
	return nil
}

func (t *TerminalApp) OpenNewTab(dir string, pasteScript *string) error {
	commands := "cd " + shellQuote(dir)
	if pasteScript != nil {
		commands += "; " + *pasteScript
	}
	escaped := exec.Escape(commands)

	countResult, ok := t.Runner.ExecuteRWithOutput(
		[]string{"osascript", "-e", `tell application "Terminal" to return count of windows`},
	)
	windowCount := 0
	if ok && countResult != "" {
		for _, c := range countResult {
			if c >= '0' && c <= '9' {
				windowCount = windowCount*10 + int(c-'0')
			}
		}
	}

	if windowCount == 0 {
		if !t.AppleScript.Execute(`
tell application "Terminal"
    do script "` + escaped + `"
end tell`) {
			return errors.New("Terminal.app AppleScript failed to create window")
		}
		return nil
	}

	success := t.AppleScript.Execute(`
tell application "Terminal"
    activate
    tell application "System Events"
        tell process "Terminal"
            keystroke "t" using command down
        end tell
    end tell
    delay 0.3
    do script "` + escaped + `" in selected tab of front window
end tell`)

	if !success {
		// Fall back to creating a window instead of a tab.
		if !t.AppleScript.Execute(`
tell application "Terminal"
    do script "` + escaped + `"
end tell`) {
			return errors.New("Terminal.app failed to create tab or window (missing accessibility permissions? grant accessibility permissions to the calling application in System Settings -> Privacy & Security -> Accessibility)")
		}
	}
	return nil
}

func (t *TerminalApp) OpenNewWindow(dir string, pasteScript *string) error {
	commands := "cd " + shellQuote(dir)
	if pasteScript != nil {
		commands += "; " + *pasteScript
	}
	if !t.AppleScript.Execute(`
tell application "Terminal"
    do script "` + exec.Escape(commands) + `"
end tell`) {
		return errors.New("Terminal.app AppleScript failed to create window")
	}
	return nil
}

func (t *TerminalApp) ListSessions() []Session {
	script := `
tell application "Terminal"
    set sessionData to ""
    repeat with theWindow in windows
        repeat with theTab in tabs of theWindow
            try
                set tabTTY to tty of theTab
                set shellCmd to "lsof " & tabTTY & " | grep -E '(zsh|bash|fish|osh|nu|pwsh|sh)' | head -1 | awk '{print $2}'"
                set shellPid to do shell script shellCmd
                if shellPid is not "" then
                    set cwdCmd to "lsof -p " & shellPid & " | grep cwd | awk '{print $9}'"
                    set workingDir to do shell script cwdCmd
                    if sessionData is not "" then
                        set sessionData to sessionData & return
                    end if
                    set sessionData to sessionData & workingDir
                end if
            end try
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
		if line != "" {
			sessions = append(sessions, Session{WorkingDirectory: line})
		}
	}
	return sessions
}

func (t *TerminalApp) RunInActiveSession(command string) error {
	if !t.AppleScript.Execute(`
tell application "Terminal"
    do script "` + exec.Escape(command) + `" in selected tab of front window
end tell`) {
		return errors.New("Terminal.app AppleScript failed to send command to active session")
	}
	return nil
}

var _ Terminal = (*TerminalApp)(nil)
