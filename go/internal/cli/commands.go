package cli

import (
	"flag"
	"fmt"
	"os"
	"strings"

	"github.com/irskep/automate-terminal/exec"
	"github.com/irskep/automate-terminal/terminal"
)

func cmdCheck(args []string, version string) int {
	fs := flag.NewFlagSet("check", flag.ContinueOnError)
	output := fs.String("output", "text", "Output format: text, json, none")
	debug := fs.Bool("debug", false, "Enable debug logging")
	if err := fs.Parse(args); err != nil {
		return 1
	}
	setupLogging(*debug, false)

	runner := &exec.Runner{}
	t := detectTerminal(runner, *output)
	if t == nil {
		termProgram := os.Getenv("TERM_PROGRAM")
		cwd, _ := os.Getwd()
		emptyCaps := terminal.Capabilities{CanDetectWorkingDirectory: true}

		data := map[string]any{
			"terminal":                  "unknown",
			"term_program":              termProgram,
			"shell":                     "unknown",
			"current_session_id":        nil,
			"current_working_directory": cwd,
			"capabilities":              emptyCaps,
			"error":                     fmt.Sprintf("Terminal '%s' is not supported", termProgram),
		}
		text := fmt.Sprintf("Error: Terminal '%s' is not supported\n"+
			"Supported terminals: iTerm2, Terminal.app, Ghostty, Guake, tmux, WezTerm, Kitty, VSCode, Cursor",
			termProgram)
		Output(*output, data, text)
		return 1
	}

	caps := t.GetCapabilities()
	cwd, _ := os.Getwd()
	override := os.Getenv("AUTOMATE_TERMINAL_OVERRIDE")

	data := map[string]any{
		"terminal":                  t.DisplayName(),
		"term_program":              os.Getenv("TERM_PROGRAM"),
		"shell":                     shellNameOrUnknown(t),
		"current_session_id":        t.GetCurrentSessionID(),
		"current_working_directory": cwd,
		"capabilities":              caps,
		"version":                   version,
	}
	if override != "" {
		data["override"] = override
	}

	var textLines []string
	termLine := "Terminal: " + t.DisplayName()
	if override != "" {
		termLine += " (overridden: " + override + ")"
	}
	textLines = append(textLines,
		termLine,
		"Terminal Program: "+os.Getenv("TERM_PROGRAM"),
		"Shell: "+shellNameOrUnknown(t),
		"Current session ID: "+sessionIDOrNA(t),
		"Current working directory: "+cwd,
		"",
		"Capabilities:",
		capabilitiesText(caps),
	)

	Output(*output, data, strings.Join(textLines, "\n"))
	return 0
}

func capabilitiesText(caps terminal.Capabilities) string {
	b := func(v bool) string {
		if v {
			return "True"
		}
		return "False"
	}
	return fmt.Sprintf("  can_create_tabs: %s\n"+
		"  can_create_windows: %s\n"+
		"  can_list_sessions: %s\n"+
		"  can_switch_to_session: %s\n"+
		"  can_detect_session_id: %s\n"+
		"  can_detect_working_directory: %s\n"+
		"  can_paste_commands: %s\n"+
		"  can_run_in_active_session: %s",
		b(caps.CanCreateTabs),
		b(caps.CanCreateWindows),
		b(caps.CanListSessions),
		b(caps.CanSwitchToSession),
		b(caps.CanDetectSessionID),
		b(caps.CanDetectWorkingDirectory),
		b(caps.CanPasteCommands),
		b(caps.CanRunInActiveSession))
}

func cmdNewTab(args []string) int {
	fs := flag.NewFlagSet("new-tab", flag.ContinueOnError)
	cf := addCommonFlags(fs)
	pf := addPasteFlags(fs)
	if err := fs.Parse(args); err != nil {
		return 1
	}
	setupLogging(cf.debug, cf.dryRun)

	positional := fs.Args()
	if len(positional) == 0 {
		OutputError(cf.output, "Missing required argument: working_directory", nil)
		return 1
	}
	dir := positional[0]

	runner := &exec.Runner{DryRun: cf.dryRun}
	t := detectTerminal(runner, cf.output)
	if t == nil {
		return 1
	}

	caps := t.GetCapabilities()
	if !caps.CanCreateTabs {
		OutputError(cf.output, "Terminal does not support tab creation",
			map[string]any{"terminal": t.DisplayName()})
		return 1
	}

	pasteScript := pf.resolve(shellNameOrUnknown(t))
	if err := t.OpenNewTab(dir, pasteScript); err != nil {
		OutputError(cf.output, err.Error(),
			map[string]any{"terminal": t.DisplayName()})
		return 1
	}

	data := map[string]any{
		"success":           true,
		"action":            "created_new_tab",
		"working_directory": dir,
		"terminal":          t.DisplayName(),
		"shell":             shellNameOrUnknown(t),
	}
	if v := pasteScriptExecuted(pasteScript, caps); v != nil {
		data["paste_script_executed"] = *v
	}
	Output(cf.output, data, "Created new tab in "+dir)
	return 0
}

func cmdNewWindow(args []string) int {
	fs := flag.NewFlagSet("new-window", flag.ContinueOnError)
	cf := addCommonFlags(fs)
	pf := addPasteFlags(fs)
	if err := fs.Parse(args); err != nil {
		return 1
	}
	setupLogging(cf.debug, cf.dryRun)

	positional := fs.Args()
	if len(positional) == 0 {
		OutputError(cf.output, "Missing required argument: working_directory", nil)
		return 1
	}
	dir := positional[0]

	runner := &exec.Runner{DryRun: cf.dryRun}
	t := detectTerminal(runner, cf.output)
	if t == nil {
		return 1
	}

	caps := t.GetCapabilities()
	if !caps.CanCreateWindows {
		OutputError(cf.output, "Terminal does not support window creation",
			map[string]any{"terminal": t.DisplayName()})
		return 1
	}

	pasteScript := pf.resolve(shellNameOrUnknown(t))
	if err := t.OpenNewWindow(dir, pasteScript); err != nil {
		OutputError(cf.output, err.Error(),
			map[string]any{"terminal": t.DisplayName()})
		return 1
	}

	data := map[string]any{
		"success":           true,
		"action":            "created_new_window",
		"working_directory": dir,
		"terminal":          t.DisplayName(),
		"shell":             shellNameOrUnknown(t),
	}
	if v := pasteScriptExecuted(pasteScript, caps); v != nil {
		data["paste_script_executed"] = *v
	}
	Output(cf.output, data, "Created new window in "+dir)
	return 0
}

func cmdSwitchTo(args []string) int {
	fs := flag.NewFlagSet("switch-to", flag.ContinueOnError)
	cf := addCommonFlags(fs)
	pf := addPasteFlags(fs)
	var sessionID, workingDir string
	fs.StringVar(&sessionID, "session-id", "", "Target session ID")
	fs.StringVar(&sessionID, "id", "", "Target session ID (alias)")
	fs.StringVar(&workingDir, "working-directory", "", "Target working directory")
	fs.StringVar(&workingDir, "wd", "", "Target working directory (alias)")
	subdirOK := fs.Bool("subdirectory-ok", false, "Allow matching sessions in subdirectories")
	if err := fs.Parse(args); err != nil {
		return 1
	}
	setupLogging(cf.debug, cf.dryRun)

	runner := &exec.Runner{DryRun: cf.dryRun}
	t := detectTerminal(runner, cf.output)
	if t == nil {
		return 1
	}

	if sessionID == "" && workingDir == "" {
		OutputError(cf.output, "Must provide --session-id or --working-directory", nil)
		return 1
	}

	pasteScript := pf.resolve(shellNameOrUnknown(t))

	var switchErr error

	if sessionID != "" && t.SessionExists(sessionID) {
		switchErr = t.SwitchToSession(sessionID, pasteScript)
	} else if workingDir != "" {
		foundID := t.FindSessionByWorkingDirectory(workingDir, *subdirOK)
		if foundID != nil {
			switchErr = t.SwitchToSession(*foundID, pasteScript)
		} else {
			switchErr = t.SwitchToSessionByWorkingDirectory(workingDir, pasteScript)
		}
	} else {
		switchErr = fmt.Errorf("session %s not found", sessionID)
	}

	if switchErr == nil {
		caps := t.GetCapabilities()
		data := map[string]any{
			"success":  true,
			"action":   "switched_to_existing",
			"terminal": t.DisplayName(),
			"shell":    shellNameOrUnknown(t),
		}
		if sessionID != "" {
			data["session_id"] = sessionID
		}
		if workingDir != "" {
			data["working_directory"] = workingDir
		}
		if v := pasteScriptExecuted(pasteScript, caps); v != nil {
			data["paste_script_executed"] = *v
		}
		Output(cf.output, data, "Switched to existing session")
		return 0
	}

	// Build helpful error message.
	errMsg := switchErr.Error()
	if !*subdirOK && workingDir != "" {
		if found := t.FindSessionByWorkingDirectory(workingDir, true); found != nil {
			errMsg = fmt.Sprintf("No session found in %s, but sessions exist in subdirectories. "+
				"Use --subdirectory-ok to match them.", workingDir)
		}
	}
	OutputError(cf.output, errMsg,
		map[string]any{"terminal": t.DisplayName()})
	return 1
}

func cmdListSessions(args []string) int {
	fs := flag.NewFlagSet("list-sessions", flag.ContinueOnError)
	cf := addCommonFlags(fs)
	if err := fs.Parse(args); err != nil {
		return 1
	}
	setupLogging(cf.debug, cf.dryRun)

	runner := &exec.Runner{DryRun: cf.dryRun}
	t := detectTerminal(runner, cf.output)
	if t == nil {
		return 1
	}

	caps := t.GetCapabilities()
	if !caps.CanListSessions {
		OutputError(cf.output, "Terminal does not support session listing",
			map[string]any{"terminal": t.DisplayName()})
		return 1
	}

	sessions := t.ListSessions()
	data := map[string]any{
		"terminal": t.DisplayName(),
		"sessions": sessions,
	}

	var lines []string
	lines = append(lines, t.DisplayName()+" Sessions:")
	for _, s := range sessions {
		var components []string
		if s.SessionID != "" {
			components = append(components, s.SessionID+" ->")
		}
		if s.WorkingDirectory != "" {
			components = append(components, s.WorkingDirectory)
		}
		if s.Shell != "" {
			components = append(components, "("+s.Shell+")")
		}
		if len(components) > 0 {
			lines = append(lines, strings.Join(components, " "))
		} else {
			lines = append(lines, "(unknown)")
		}
	}

	Output(cf.output, data, strings.Join(lines, "\n"))
	return 0
}

func cmdRunInActiveSession(args []string) int {
	fs := flag.NewFlagSet("run-in-active-session", flag.ContinueOnError)
	cf := addCommonFlags(fs)
	if err := fs.Parse(args); err != nil {
		return 1
	}
	setupLogging(cf.debug, cf.dryRun)

	positional := fs.Args()
	if len(positional) == 0 {
		OutputError(cf.output, "Missing required argument: script", nil)
		return 1
	}
	script := positional[0]

	runner := &exec.Runner{DryRun: cf.dryRun}
	t := detectTerminal(runner, cf.output)
	if t == nil {
		return 1
	}

	caps := t.GetCapabilities()
	if !caps.CanRunInActiveSession {
		OutputError(cf.output, "Terminal does not support running commands in active session",
			map[string]any{"terminal": t.DisplayName()})
		return 1
	}

	if err := t.RunInActiveSession(script); err != nil {
		OutputError(cf.output, err.Error(),
			map[string]any{"terminal": t.DisplayName()})
		return 1
	}

	data := map[string]any{
		"success":  true,
		"terminal": t.DisplayName(),
		"command":  script,
	}
	Output(cf.output, data, "Command sent to active session")
	return 0
}
