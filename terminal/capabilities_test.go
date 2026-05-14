package terminal

import (
	"testing"

	"github.com/irskep/automate-terminal/exec"
)

func TestTmuxCapabilities(t *testing.T) {
	tmux := &Tmux{Runner: &exec.Runner{}}
	caps := tmux.GetCapabilities()
	assertAllTrue(t, caps)
}

func TestWeztermCapabilities(t *testing.T) {
	wez := &WezTerm{Runner: &exec.Runner{}}
	caps := wez.GetCapabilities()
	assertAllTrue(t, caps)
}

func TestKittyCapabilities(t *testing.T) {
	kitty := &Kitty{Runner: &exec.Runner{}}
	caps := kitty.GetCapabilities()
	assertAllTrue(t, caps)
}

func TestVSCodeCapabilities(t *testing.T) {
	vscode := &VSCode{Runner: &exec.Runner{}, Variant: "vscode"}
	caps := vscode.GetCapabilities()

	if caps.CanCreateTabs {
		t.Error("VSCode should not support tab creation")
	}
	if !caps.CanCreateWindows {
		t.Error("VSCode should support window creation")
	}
	if caps.CanListSessions {
		t.Error("VSCode should not support session listing")
	}
	if !caps.CanSwitchToSession {
		t.Error("VSCode should support switch-to")
	}
	if caps.CanDetectSessionID {
		t.Error("VSCode should not detect session ID")
	}
	if caps.CanPasteCommands {
		t.Error("VSCode should not support paste commands")
	}
	if caps.CanRunInActiveSession {
		t.Error("VSCode should not support run-in-active")
	}
}

func TestGuakeCapabilities(t *testing.T) {
	guake := &Guake{Runner: &exec.Runner{}}
	caps := guake.GetCapabilities()

	if !caps.CanCreateTabs {
		t.Error("Guake should support tab creation")
	}
	if caps.CanCreateWindows {
		t.Error("Guake should not support window creation")
	}
	if !caps.CanListSessions {
		t.Error("Guake should support session listing")
	}
}

func TestVSCodeProperties(t *testing.T) {
	vscode := &VSCode{Runner: &exec.Runner{}, Variant: "vscode"}
	cursor := &VSCode{Runner: &exec.Runner{}, Variant: "cursor"}

	if vscode.DisplayName() != "VSCode" {
		t.Errorf("expected VSCode, got %s", vscode.DisplayName())
	}
	if vscode.cliCommand() != "code" {
		t.Errorf("expected code, got %s", vscode.cliCommand())
	}

	if cursor.DisplayName() != "Cursor" {
		t.Errorf("expected Cursor, got %s", cursor.DisplayName())
	}
	if cursor.cliCommand() != "cursor" {
		t.Errorf("expected cursor, got %s", cursor.cliCommand())
	}
}

func assertAllTrue(t *testing.T, caps Capabilities) {
	t.Helper()
	if !caps.CanCreateTabs {
		t.Error("expected CanCreateTabs")
	}
	if !caps.CanCreateWindows {
		t.Error("expected CanCreateWindows")
	}
	if !caps.CanListSessions {
		t.Error("expected CanListSessions")
	}
	if !caps.CanSwitchToSession {
		t.Error("expected CanSwitchToSession")
	}
	if !caps.CanDetectSessionID {
		t.Error("expected CanDetectSessionID")
	}
	if !caps.CanDetectWorkingDirectory {
		t.Error("expected CanDetectWorkingDirectory")
	}
	if !caps.CanPasteCommands {
		t.Error("expected CanPasteCommands")
	}
	if !caps.CanRunInActiveSession {
		t.Error("expected CanRunInActiveSession")
	}
}
