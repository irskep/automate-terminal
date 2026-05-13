package terminal

import (
	"fmt"
	"os"
	"os/exec"

	runner "github.com/irskep/automate-terminal/exec"
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

func (v *VSCode) Detect(termProgram string) bool {
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

func (v *VSCode) SwitchToSessionByWorkingDirectory(dir string, pasteScript *string) error {
	return v.runCLI(dir)
}

func (v *VSCode) OpenNewWindow(dir string, pasteScript *string) error {
	return v.runCLI(dir)
}

func (v *VSCode) runCLI(dir string) error {
	cli := v.cliCommand()
	if _, err := exec.LookPath(cli); err != nil {
		return fmt.Errorf("%s CLI not found on PATH (install via %s Command Palette: 'Shell Command: Install %s command in PATH')",
			cli, v.DisplayName(), cli)
	}
	if !v.Runner.ExecuteRW([]string{cli, dir}) {
		return fmt.Errorf("%s %s failed", cli, dir)
	}
	return nil
}

var _ Terminal = (*VSCode)(nil)
