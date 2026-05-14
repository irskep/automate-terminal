package exec

import "testing"

func TestEscape(t *testing.T) {
	tests := []struct {
		in, want string
	}{
		{`hello`, `hello`},
		{`say "hi"`, `say \"hi\"`},
		{`path\to\file`, `path\\to\\file`},
		{`both "and" \`, `both \"and\" \\`},
		{``, ``},
	}
	for _, tt := range tests {
		got := Escape(tt.in)
		if got != tt.want {
			t.Errorf("Escape(%q) = %q, want %q", tt.in, got, tt.want)
		}
	}
}
