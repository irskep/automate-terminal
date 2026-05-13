package terminal

import (
	"log/slog"
	"os"
	"os/exec"

	runner "github.com/stevelandeyasleep/automate-terminal/internal/exec"
)

// VSCode implements Terminal for Visual Studio Code and Cursor.
type VSCode struct {
	Base
	Runner  *runner.Runner
	Variant string // "vscode" or "cursor"
}

func (v *VSCode) DisplayName() string {
	if v.Variant == "cursor" {
		return "Cursor"
	}
	return "VSCode"
}

func (v *VSCode) cliCommand() string {
	if v.Variant == "cursor" {
		return "cursor"
	}
	return "code"
}

func (v *VSCode) Detect(termProgram string, platform string) bool {
	if termProgram != "vscode" {
		return false
	}
	hasCursorID := os.Getenv("CURSOR_TRACE_ID") != ""
	if v.Variant == "cursor" {
		return hasCursorID
	}
	return !hasCursorID
}

func (v *VSCode) GetCapabilities() Capabilities {
	return Capabilities{
		CanCreateTabs:             false,
		CanCreateWindows:          true,
		CanListSessions:           false,
		CanSwitchToSession:        true,
		CanDetectSessionID:        false,
		CanDetectWorkingDirectory: false,
		CanPasteCommands:          false,
		CanRunInActiveSession:     false,
	}
}

func (v *VSCode) SwitchToSessionByWorkingDirectory(dir string, pasteScript *string) bool {
	if pasteScript != nil {
		slog.Warn(v.DisplayName() + " cannot execute init scripts in integrated terminal")
	}
	return v.runCLI(dir)
}

func (v *VSCode) OpenNewWindow(dir string, pasteScript *string) bool {
	if pasteScript != nil {
		slog.Warn(v.DisplayName() + " cannot execute init scripts via CLI")
	}
	return v.runCLI(dir)
}

func (v *VSCode) runCLI(dir string) bool {
	cli := v.cliCommand()
	if _, err := exec.LookPath(cli); err != nil {
		slog.Error(cli+" CLI not found",
			"hint", "Install via "+v.DisplayName()+" Command Palette: 'Shell Command: Install "+cli+" command in PATH'")
		return false
	}
	return v.Runner.ExecuteRW([]string{cli, dir})
}

var _ Terminal = (*VSCode)(nil)
