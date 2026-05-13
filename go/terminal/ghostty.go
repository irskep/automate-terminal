package terminal

import (
	"errors"

	"github.com/irskep/automate-terminal/exec"
)

// Ghostty implements Terminal for Ghostty on macOS.
// Ghostty has no AppleScript API; everything goes through System Events keyboard simulation.
type Ghostty struct {
	Base
	AppleScript *exec.AppleScript
	Runner      *exec.Runner
}

func (g *Ghostty) DisplayName() string { return "Ghostty" }

func (g *Ghostty) Detect(termProgram string) bool {
	return termProgram == "ghostty" && g.AppleScript.Available()
}

func (g *Ghostty) GetCapabilities() Capabilities {
	return Capabilities{
		CanCreateTabs:             true,
		CanCreateWindows:          true,
		CanListSessions:           false,
		CanSwitchToSession:        false,
		CanDetectSessionID:        false,
		CanDetectWorkingDirectory: false,
		CanPasteCommands:          true,
		CanRunInActiveSession:     true,
	}
}

func (g *Ghostty) OpenNewTab(dir string, pasteScript *string) error {
	commands := "cd " + shellQuote(dir)
	if pasteScript != nil {
		commands += "; " + *pasteScript
	}

	if !g.AppleScript.Execute(`
tell application "Ghostty"
    activate
    tell application "System Events"
        tell process "Ghostty"
            keystroke "t" using command down
            delay 0.3
            keystroke "` + exec.Escape(commands) + `"
            key code 36 -- Return
        end tell
    end tell
end tell`) {
		return errors.New("Ghostty failed to create tab (missing accessibility permissions? grant accessibility permissions to the calling application in System Settings -> Privacy & Security -> Accessibility)")
	}
	return nil
}

func (g *Ghostty) OpenNewWindow(dir string, pasteScript *string) error {
	commands := "cd " + shellQuote(dir)
	if pasteScript != nil {
		commands += "; " + *pasteScript
	}

	if !g.AppleScript.Execute(`
tell application "Ghostty"
    activate
    tell application "System Events"
        tell process "Ghostty"
            keystroke "n" using command down
            delay 0.3
            keystroke "` + exec.Escape(commands) + `"
            key code 36 -- Return
        end tell
    end tell
end tell`) {
		return errors.New("Ghostty failed to create window (missing accessibility permissions? grant accessibility permissions to the calling application in System Settings -> Privacy & Security -> Accessibility)")
	}
	return nil
}

func (g *Ghostty) RunInActiveSession(command string) error {
	if !g.AppleScript.Execute(`
tell application "System Events"
    tell process "Ghostty"
        keystroke "` + exec.Escape(command) + `"
        key code 36
    end tell
end tell`) {
		return errors.New("Ghostty failed to send command (missing accessibility permissions? grant accessibility permissions to the calling application in System Settings -> Privacy & Security -> Accessibility)")
	}
	return nil
}

var _ Terminal = (*Ghostty)(nil)
