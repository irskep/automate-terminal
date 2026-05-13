package cli

import (
	"flag"
	"fmt"
	"log/slog"
	"os"

	"github.com/stevelandeyasleep/automate-terminal/detect"
	"github.com/stevelandeyasleep/automate-terminal/exec"
	"github.com/stevelandeyasleep/automate-terminal/terminal"
)

// Run is the main entry point. Returns an exit code.
func Run(args []string, version string) int {
	if len(args) > 0 && (args[0] == "--version" || args[0] == "-version") {
		fmt.Printf("automate-terminal %s\n", version)
		return 0
	}

	if len(args) == 0 {
		printUsage()
		return 1
	}

	command := args[0]
	rest := args[1:]

	switch command {
	case "check":
		return cmdCheck(rest, version)
	case "new-tab":
		return cmdNewTab(rest)
	case "new-window":
		return cmdNewWindow(rest)
	case "switch-to":
		return cmdSwitchTo(rest)
	case "list-sessions":
		return cmdListSessions(rest)
	case "run-in-active-session":
		return cmdRunInActiveSession(rest)
	default:
		printUsage()
		return 1
	}
}

func printUsage() {
	fmt.Fprintln(os.Stderr, "Usage: automate-terminal <command> [options]")
	fmt.Fprintln(os.Stderr, "")
	fmt.Fprintln(os.Stderr, "Commands:")
	fmt.Fprintln(os.Stderr, "  check                  Check terminal capabilities")
	fmt.Fprintln(os.Stderr, "  new-tab                Create new tab")
	fmt.Fprintln(os.Stderr, "  new-window             Create new window")
	fmt.Fprintln(os.Stderr, "  switch-to              Switch to existing session")
	fmt.Fprintln(os.Stderr, "  list-sessions          List all sessions")
	fmt.Fprintln(os.Stderr, "  run-in-active-session  Run command in active session")
}

// commonFlags are shared by most subcommands.
type commonFlags struct {
	output string
	debug  bool
	dryRun bool
}

func addCommonFlags(fs *flag.FlagSet) *commonFlags {
	f := &commonFlags{}
	fs.StringVar(&f.output, "output", "text", "Output format: text, json, none")
	fs.BoolVar(&f.debug, "debug", false, "Enable debug logging")
	fs.BoolVar(&f.dryRun, "dry-run", false, "Log actions instead of executing them")
	return f
}

// pasteFlags are shared by new-tab, new-window, switch-to.
type pasteFlags struct {
	pasteAndRun           string
	pasteAndRunBash       string
	pasteAndRunZsh        string
	pasteAndRunFish       string
	pasteAndRunPowershell string
	pasteAndRunNushell    string
}

func addPasteFlags(fs *flag.FlagSet) *pasteFlags {
	f := &pasteFlags{}
	fs.StringVar(&f.pasteAndRun, "paste-and-run", "", "Shell-agnostic script to paste")
	fs.StringVar(&f.pasteAndRunBash, "paste-and-run-bash", "", "Bash-specific script")
	fs.StringVar(&f.pasteAndRunZsh, "paste-and-run-zsh", "", "Zsh-specific script")
	fs.StringVar(&f.pasteAndRunFish, "paste-and-run-fish", "", "Fish-specific script")
	fs.StringVar(&f.pasteAndRunPowershell, "paste-and-run-powershell", "", "PowerShell-specific script")
	fs.StringVar(&f.pasteAndRunNushell, "paste-and-run-nushell", "", "Nushell-specific script")
	return f
}

func (pf *pasteFlags) resolve(shellName string) *string {
	specific := map[string]*string{
		"bash":       strPtr(pf.pasteAndRunBash),
		"zsh":        strPtr(pf.pasteAndRunZsh),
		"fish":       strPtr(pf.pasteAndRunFish),
		"powershell": strPtr(pf.pasteAndRunPowershell),
		"nushell":    strPtr(pf.pasteAndRunNushell),
	}
	generic := strPtr(pf.pasteAndRun)
	return ResolvePasteScript(shellName, generic, specific)
}

func strPtr(s string) *string {
	if s == "" {
		return nil
	}
	return &s
}

func setupLogging(debug, dryRun bool) {
	var level slog.Level
	if debug {
		level = slog.LevelDebug
	} else if dryRun {
		level = slog.LevelInfo
	} else {
		level = slog.LevelWarn
	}
	handler := slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: level})
	slog.SetDefault(slog.New(handler))
}

func detectTerminal(runner *exec.Runner, outputFmt string) terminal.Terminal {
	t := detect.Detect(runner)
	if t == nil {
		OutputError(outputFmt, "Terminal not supported", nil)
	}
	return t
}

func shellNameOrUnknown(t terminal.Terminal) string {
	if s := t.GetShellName(); s != nil {
		return *s
	}
	return "unknown"
}

func sessionIDOrNA(t terminal.Terminal) string {
	if s := t.GetCurrentSessionID(); s != nil {
		return *s
	}
	return "N/A"
}

// pasteScriptExecuted returns the value for the paste_script_executed JSON field.
// Returns nil (omit), true, or false.
func pasteScriptExecuted(pasteScript *string, caps terminal.Capabilities) *bool {
	if pasteScript == nil {
		return nil
	}
	v := caps.CanPasteCommands
	return &v
}

