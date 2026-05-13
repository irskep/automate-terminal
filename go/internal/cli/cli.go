package cli

import (
	"flag"
	"fmt"
	"log/slog"
	"os"
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

// Stub subcommand handlers. Each will be fleshed out in stage 4.

func cmdCheck(args []string, version string) int {
	fs := flag.NewFlagSet("check", flag.ContinueOnError)
	output := fs.String("output", "text", "Output format: text, json, none")
	debug := fs.Bool("debug", false, "Enable debug logging")
	if err := fs.Parse(args); err != nil {
		return 1
	}
	setupLogging(*debug, false)
	_ = output
	_ = version
	// TODO: detect terminal + output capabilities
	return 0
}

func cmdNewTab(args []string) int {
	fs := flag.NewFlagSet("new-tab", flag.ContinueOnError)
	cf := addCommonFlags(fs)
	pf := addPasteFlags(fs)
	if err := fs.Parse(args); err != nil {
		return 1
	}
	setupLogging(cf.debug, cf.dryRun)
	_ = pf
	// TODO
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
	_ = pf
	// TODO
	return 0
}

func cmdSwitchTo(args []string) int {
	fs := flag.NewFlagSet("switch-to", flag.ContinueOnError)
	cf := addCommonFlags(fs)
	pf := addPasteFlags(fs)
	sessionID := fs.String("session-id", "", "Target session ID")
	fs.StringVar(sessionID, "id", "", "Target session ID (alias)")
	workingDir := fs.String("working-directory", "", "Target working directory")
	fs.StringVar(workingDir, "wd", "", "Target working directory (alias)")
	subdirOK := fs.Bool("subdirectory-ok", false, "Allow matching sessions in subdirectories")
	if err := fs.Parse(args); err != nil {
		return 1
	}
	setupLogging(cf.debug, cf.dryRun)
	_ = pf
	_ = sessionID
	_ = workingDir
	_ = subdirOK
	// TODO
	return 0
}

func cmdListSessions(args []string) int {
	fs := flag.NewFlagSet("list-sessions", flag.ContinueOnError)
	cf := addCommonFlags(fs)
	if err := fs.Parse(args); err != nil {
		return 1
	}
	setupLogging(cf.debug, cf.dryRun)
	// TODO
	return 0
}

func cmdRunInActiveSession(args []string) int {
	fs := flag.NewFlagSet("run-in-active-session", flag.ContinueOnError)
	cf := addCommonFlags(fs)
	if err := fs.Parse(args); err != nil {
		return 1
	}
	setupLogging(cf.debug, cf.dryRun)
	// TODO
	return 0
}
