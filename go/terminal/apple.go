package terminal

import (
	"log/slog"
	"strings"

	"github.com/stevelandeyasleep/automate-terminal/exec"
)

// TerminalApp implements Terminal for macOS Terminal.app.
type TerminalApp struct {
	Base
	AS     *exec.AppleScript
	Runner *exec.Runner
}

func (t *TerminalApp) DisplayName() string { return "Apple Terminal.app" }

func (t *TerminalApp) Detect(termProgram string, platform string) bool {
	return platform == "darwin" && termProgram == "Apple_Terminal"
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

func (t *TerminalApp) SwitchToSessionByWorkingDirectory(dir string, pasteScript *string) bool {
	escaped := exec.Escape(dir)

	// Find the window containing a tab whose shell is in the target directory.
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
	windowName, ok := t.AS.ExecuteWithResult(findScript)
	if !ok || windowName == "" {
		return false
	}

	// Run init script if provided.
	if pasteScript != nil {
		t.AS.Execute(`
tell application "Terminal"
    do script "` + exec.Escape(*pasteScript) + `" in front window
end tell`)
	}

	// Use System Events to click the window menu item.
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
	result, ok := t.AS.ExecuteWithResult(switchScript)
	return ok && strings.HasPrefix(result, "success")
}

func (t *TerminalApp) OpenNewTab(dir string, pasteScript *string) bool {
	commands := "cd " + shellQuote(dir)
	if pasteScript != nil {
		commands += "; " + *pasteScript
	}
	escaped := exec.Escape(commands)

	// Check if any windows exist.
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
		return t.AS.Execute(`
tell application "Terminal"
    do script "` + escaped + `"
end tell`)
	}

	// Try creating a tab via System Events (requires accessibility).
	success := t.AS.Execute(`
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
		slog.Warn("Failed to create tab (missing accessibility permissions). " +
			"Creating new window instead. To fix: Enable Terminal in " +
			"System Settings -> Privacy & Security -> Accessibility")
		return t.AS.Execute(`
tell application "Terminal"
    do script "` + escaped + `"
end tell`)
	}
	return true
}

func (t *TerminalApp) OpenNewWindow(dir string, pasteScript *string) bool {
	commands := "cd " + shellQuote(dir)
	if pasteScript != nil {
		commands += "; " + *pasteScript
	}
	return t.AS.Execute(`
tell application "Terminal"
    do script "` + exec.Escape(commands) + `"
end tell`)
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
	output, ok := t.AS.ExecuteWithResult(script)
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

func (t *TerminalApp) RunInActiveSession(command string) bool {
	return t.AS.Execute(`
tell application "Terminal"
    do script "` + exec.Escape(command) + `" in selected tab of front window
end tell`)
}

var _ Terminal = (*TerminalApp)(nil)
