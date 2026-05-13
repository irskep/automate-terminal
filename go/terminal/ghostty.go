package terminal

import (
	"log/slog"

	"github.com/irskep/automate-terminal/exec"
)

// Ghostty implements Terminal for Ghostty on macOS.
// Ghostty has no AppleScript API; everything goes through System Events keyboard simulation.
type Ghostty struct {
	Base
	AS     *exec.AppleScript
	Runner *exec.Runner
}

func (g *Ghostty) DisplayName() string { return "Ghostty" }

func (g *Ghostty) Detect(termProgram string, platform string) bool {
	return platform == "darwin" && termProgram == "ghostty"
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

func (g *Ghostty) OpenNewTab(dir string, pasteScript *string) bool {
	commands := "cd " + shellQuote(dir)
	if pasteScript != nil {
		commands += "; " + *pasteScript
	}

	success := g.AS.Execute(`
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
end tell`)

	if !success {
		slog.Warn("Failed to create tab (missing accessibility permissions). " +
			"To fix: Enable Terminal in " +
			"System Settings -> Privacy & Security -> Accessibility")
	}
	return success
}

func (g *Ghostty) OpenNewWindow(dir string, pasteScript *string) bool {
	commands := "cd " + shellQuote(dir)
	if pasteScript != nil {
		commands += "; " + *pasteScript
	}

	return g.AS.Execute(`
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
end tell`)
}

func (g *Ghostty) RunInActiveSession(command string) bool {
	return g.AS.Execute(`
tell application "System Events"
    tell process "Ghostty"
        keystroke "` + exec.Escape(command) + `"
        key code 36
    end tell
end tell`)
}

var _ Terminal = (*Ghostty)(nil)
