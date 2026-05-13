package terminal

import (
	"os"
	"path/filepath"
	"strings"
)

// Capabilities describes what a terminal backend can do.
type Capabilities struct {
	CanCreateTabs             bool `json:"can_create_tabs"`
	CanCreateWindows          bool `json:"can_create_windows"`
	CanListSessions           bool `json:"can_list_sessions"`
	CanSwitchToSession        bool `json:"can_switch_to_session"`
	CanDetectSessionID        bool `json:"can_detect_session_id"`
	CanDetectWorkingDirectory bool `json:"can_detect_working_directory"`
	CanPasteCommands          bool `json:"can_paste_commands"`
	CanRunInActiveSession     bool `json:"can_run_in_active_session"`
}

// Session represents a terminal session returned by ListSessions.
type Session struct {
	SessionID        string `json:"session_id,omitempty"`
	WorkingDirectory string `json:"working_directory,omitempty"`
	Shell            string `json:"shell,omitempty"`
}

// Terminal is the interface every backend implements.
type Terminal interface {
	DisplayName() string
	Detect(termProgram string, platform string) bool
	GetCurrentSessionID() *string
	GetShellName() *string
	GetCapabilities() Capabilities
	SessionExists(sessionID string) bool
	SwitchToSession(sessionID string, pasteScript *string) bool
	SwitchToSessionByWorkingDirectory(dir string, pasteScript *string) bool
	OpenNewTab(dir string, pasteScript *string) bool
	OpenNewWindow(dir string, pasteScript *string) bool
	ListSessions() []Session
	FindSessionByWorkingDirectory(target string, subdirectoryOK bool) *string
	RunInActiveSession(command string) bool
}

// Base provides default no-op implementations for optional Terminal methods.
// Embed this in backend structs to avoid repeating boilerplate.
type Base struct{}

func (Base) GetCurrentSessionID() *string                           { return nil }
func (Base) SessionExists(string) bool                              { return false }
func (Base) SwitchToSession(string, *string) bool                   { return false }
func (Base) SwitchToSessionByWorkingDirectory(string, *string) bool { return false }
func (Base) OpenNewTab(string, *string) bool                        { return false }
func (Base) OpenNewWindow(string, *string) bool                     { return false }
func (Base) ListSessions() []Session                                { return nil }
func (Base) FindSessionByWorkingDirectory(string, bool) *string     { return nil }
func (Base) RunInActiveSession(string) bool                         { return false }

// GetShellName returns the basename of the SHELL environment variable.
func (Base) GetShellName() *string {
	shell := os.Getenv("SHELL")
	if shell == "" {
		return nil
	}
	name := filepath.Base(shell)
	return &name
}

// findSessionByDir matches sessions against a target directory path.
// Resolves symlinks before comparing. Tries exact match first, then
// subdirectory match if allowed.
func findSessionByDir(sessions []Session, target string, subdirectoryOK bool) *string {
	resolved, err := filepath.EvalSymlinks(target)
	if err != nil {
		resolved = target
	}
	resolved = filepath.Clean(resolved)

	for _, s := range sessions {
		sp := resolveClean(s.WorkingDirectory)
		if sp == resolved {
			id := s.SessionID
			return &id
		}
	}
	if subdirectoryOK {
		prefix := resolved + "/"
		for _, s := range sessions {
			sp := resolveClean(s.WorkingDirectory)
			if strings.HasPrefix(sp, prefix) {
				id := s.SessionID
				return &id
			}
		}
	}
	return nil
}

// shellQuote wraps a string in single quotes for use in shell commands.
// Interior single quotes are escaped via the '\'' idiom.
func shellQuote(s string) string {
	return "'" + strings.ReplaceAll(s, "'", `'\''`) + "'"
}

func resolveClean(path string) string {
	resolved, err := filepath.EvalSymlinks(path)
	if err != nil {
		return filepath.Clean(path)
	}
	return filepath.Clean(resolved)
}
