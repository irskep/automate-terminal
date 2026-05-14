package terminal

import (
	"os"
	"path/filepath"
	"testing"
)

func TestFindSessionByDir_ExactMatch(t *testing.T) {
	sessions := []Session{
		{SessionID: "1", WorkingDirectory: "/home/user/project"},
		{SessionID: "2", WorkingDirectory: "/home/user/other"},
	}
	got := findSessionByDir(sessions, "/home/user/project", false)
	if got == nil || *got != "1" {
		t.Errorf("expected session 1, got %v", got)
	}
}

func TestFindSessionByDir_NoMatch(t *testing.T) {
	sessions := []Session{
		{SessionID: "1", WorkingDirectory: "/home/user/project"},
	}
	got := findSessionByDir(sessions, "/home/user/other", false)
	if got != nil {
		t.Errorf("expected nil, got %v", *got)
	}
}

func TestFindSessionByDir_SubdirectoryMatch(t *testing.T) {
	sessions := []Session{
		{SessionID: "1", WorkingDirectory: "/home/user/project/sub"},
	}
	got := findSessionByDir(sessions, "/home/user/project", true)
	if got == nil || *got != "1" {
		t.Errorf("expected session 1, got %v", got)
	}
}

func TestFindSessionByDir_SubdirectoryDisabled(t *testing.T) {
	sessions := []Session{
		{SessionID: "1", WorkingDirectory: "/home/user/project/sub"},
	}
	got := findSessionByDir(sessions, "/home/user/project", false)
	if got != nil {
		t.Errorf("expected nil, got %v", *got)
	}
}

func TestFindSessionByDir_ExactMatchBeforeSubdirectory(t *testing.T) {
	sessions := []Session{
		{SessionID: "sub", WorkingDirectory: "/home/user/project/sub"},
		{SessionID: "exact", WorkingDirectory: "/home/user/project"},
	}
	got := findSessionByDir(sessions, "/home/user/project", true)
	if got == nil || *got != "exact" {
		t.Errorf("expected exact match first, got %v", got)
	}
}

func TestFindSessionByDir_Symlink(t *testing.T) {
	dir := t.TempDir()
	real := filepath.Join(dir, "real")
	link := filepath.Join(dir, "link")
	os.Mkdir(real, 0o755)
	os.Symlink(real, link)

	sessions := []Session{
		{SessionID: "1", WorkingDirectory: real},
	}
	got := findSessionByDir(sessions, link, false)
	if got == nil || *got != "1" {
		t.Errorf("expected session 1 via symlink, got %v", got)
	}
}

func TestFindSessionByDir_SubdirectoryNoFalsePositive(t *testing.T) {
	sessions := []Session{
		{SessionID: "1", WorkingDirectory: "/home/user/project-extra"},
	}
	// "project-extra" should NOT match "project" as a subdirectory
	got := findSessionByDir(sessions, "/home/user/project", true)
	if got != nil {
		t.Errorf("expected nil (prefix without slash boundary), got %v", *got)
	}
}

func TestShellQuote(t *testing.T) {
	tests := []struct {
		in, want string
	}{
		{"simple", "'simple'"},
		{"/path/to/dir", "'/path/to/dir'"},
		{"it's here", `'it'\''s here'`},
		{"", "''"},
	}
	for _, tt := range tests {
		got := shellQuote(tt.in)
		if got != tt.want {
			t.Errorf("shellQuote(%q) = %q, want %q", tt.in, got, tt.want)
		}
	}
}

func TestGetShellName(t *testing.T) {
	b := Base{}

	orig := os.Getenv("SHELL")
	defer os.Setenv("SHELL", orig)

	os.Setenv("SHELL", "/bin/zsh")
	got := b.GetShellName()
	if got == nil || *got != "zsh" {
		t.Errorf("expected zsh, got %v", got)
	}

	os.Setenv("SHELL", "/usr/local/bin/fish")
	got = b.GetShellName()
	if got == nil || *got != "fish" {
		t.Errorf("expected fish, got %v", got)
	}

	os.Setenv("SHELL", "")
	got = b.GetShellName()
	if got != nil {
		t.Errorf("expected nil for empty SHELL, got %v", *got)
	}
}
