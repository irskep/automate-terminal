package terminal

import "testing"

func TestParseCwdURI(t *testing.T) {
	tests := []struct {
		in, want string
	}{
		{"file://localhost/home/user", "/home/user"},
		{"file:///home/user", "/home/user"},
		{"/home/user", "/home/user"},
		{"", ""},
	}
	for _, tt := range tests {
		got := parseCwdURI(tt.in)
		if got != tt.want {
			t.Errorf("parseCwdURI(%q) = %q, want %q", tt.in, got, tt.want)
		}
	}
}
