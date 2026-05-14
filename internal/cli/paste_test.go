package cli

import "testing"

func sp(s string) *string { return &s }

func TestResolvePasteScript_GenericOnly(t *testing.T) {
	got := ResolvePasteScript("bash", sp("generic"), map[string]*string{})
	if got == nil || *got != "generic" {
		t.Errorf("expected 'generic', got %v", got)
	}
}

func TestResolvePasteScript_ShellSpecificOnly(t *testing.T) {
	got := ResolvePasteScript("zsh", nil, map[string]*string{
		"zsh": sp("zsh script"),
	})
	if got == nil || *got != "zsh script" {
		t.Errorf("expected 'zsh script', got %v", got)
	}
}

func TestResolvePasteScript_BothJoined(t *testing.T) {
	got := ResolvePasteScript("zsh", sp("generic"), map[string]*string{
		"zsh": sp("specific"),
	})
	if got == nil || *got != "specific; generic" {
		t.Errorf("expected 'specific; generic', got %v", got)
	}
}

func TestResolvePasteScript_ShellMismatch(t *testing.T) {
	got := ResolvePasteScript("bash", sp("generic"), map[string]*string{
		"zsh": sp("zsh only"),
	})
	if got == nil || *got != "generic" {
		t.Errorf("expected 'generic' (zsh script ignored for bash), got %v", got)
	}
}

func TestResolvePasteScript_NoneProvided(t *testing.T) {
	got := ResolvePasteScript("bash", nil, map[string]*string{})
	if got != nil {
		t.Errorf("expected nil, got %v", *got)
	}
}

func TestResolvePasteScript_EmptyStrings(t *testing.T) {
	got := ResolvePasteScript("bash", sp(""), map[string]*string{
		"bash": sp(""),
	})
	if got != nil {
		t.Errorf("expected nil for empty strings, got %v", *got)
	}
}
