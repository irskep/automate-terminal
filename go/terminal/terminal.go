// Package terminal defines the Terminal interface and types shared by all
// terminal backends. Use [detect.Detect] to get a Terminal for the current
// environment.
package terminal

import (
	"os"
	"path/filepath"
	"strings"
)

// Capabilities reports which operations a terminal backend supports.
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

// Terminal is the interface every backend implements. Callers should use
// [detect.Detect] to obtain an appropriate implementation rather than
// constructing backends directly.
type Terminal interface {
	// DisplayName returns a human-readable name like "iTerm2" or "tmux".
	DisplayName() string

	// Detect reports whether this backend matches the current environment.
	// termProgram is the value of TERM_PROGRAM; platform is runtime.GOOS.
	Detect(termProgram string, platform string) bool

	// GetCurrentSessionID returns a unique identifier for the active session,
	// or nil if the backend cannot determine one.
	GetCurrentSessionID() *string

	// GetShellName returns the name of the running shell (e.g. "zsh"),
	// or nil if unknown.
	GetShellName() *string

	// GetCapabilities reports which operations this backend supports.
	GetCapabilities() Capabilities

	// SessionExists reports whether a session with the given ID is open.
	SessionExists(sessionID string) bool

	// SwitchToSession activates the session with the given ID.
	// If pasteScript is non-nil, the script is sent to the session after switching.
	SwitchToSession(sessionID string, pasteScript *string) bool

	// SwitchToSessionByWorkingDirectory activates a session whose working
	// directory matches dir. Used by backends like Terminal.app that lack
	// session IDs.
	SwitchToSessionByWorkingDirectory(dir string, pasteScript *string) bool

	// OpenNewTab creates a new tab in dir. If pasteScript is non-nil, the
	// script is sent to the new tab.
	OpenNewTab(dir string, pasteScript *string) bool

	// OpenNewWindow creates a new window in dir. If pasteScript is non-nil,
	// the script is sent to the new window.
	OpenNewWindow(dir string, pasteScript *string) bool

	// ListSessions returns all open sessions the backend knows about.
	ListSessions() []Session

	// FindSessionByWorkingDirectory returns the session ID of a session whose
	// working directory matches target (symlinks resolved). If subdirectoryOK
	// is true, sessions in subdirectories of target also match.
	// Returns nil if no match is found.
	FindSessionByWorkingDirectory(target string, subdirectoryOK bool) *string

	// RunInActiveSession sends command to the currently active session
	// as if the user typed it.
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
