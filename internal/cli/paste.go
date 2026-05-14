package cli

import "strings"

// ResolvePasteScript picks the right paste script based on the detected shell
// and the flags the user provided. Returns nil if no script applies.
func ResolvePasteScript(shellName string, generic *string, shellSpecific map[string]*string) *string {
	var scripts []string

	if s, ok := shellSpecific[shellName]; ok && s != nil && *s != "" {
		scripts = append(scripts, *s)
	}
	if generic != nil && *generic != "" {
		scripts = append(scripts, *generic)
	}
	if len(scripts) == 0 {
		return nil
	}
	joined := strings.Join(scripts, "; ")
	return &joined
}
