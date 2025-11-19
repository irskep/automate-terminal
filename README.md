# automate-terminal

Automate opening of new tabs and windows in terminal programs. Currently supports iTerm2, Terminal.app, Ghostty, Guake, tmux, WezTerm, Kitty, Cursor, and Visual Studio Code.

automate-terminal is a best-effort project. Some terminals do not support automation at all! It's also intended to be used as a component in other tools, so it errs on the side of strictness over fallbacks. See the command reference for specifics.

`automate-terminal` was originally part of [autowt](https://steveasleep.com/autowt/), the git worktree manager.

## Installation

```bash
pip install automate-terminal
```

```bash
mise install pip:automate-terminal
```

For Guake terminal support on Linux, install with the guake extra:

```bash
pip install automate-terminal[guake]
```

```bash
mise install pip:automate-terminal[guake]
```

## Supported Terminals

| Terminal     | Platform       | New Tabs/Windows | Switch by ID | Switch by Working Dir | List Sessions | Paste Commands | Run in Active Session |
| ------------ | -------------- | ---------------- | ------------ | --------------------- | ------------- | -------------- | --------------------- |
| iTerm2       | macOS          | ✅               | ✅           | ✅                    | ✅            | ✅             | ✅                    |
| Terminal.app | macOS          | ✅               | ❌           | ✅                    | ✅            | ✅             | ✅                    |
| Ghostty      | macOS          | ✅               | ❌           | ❌                    | ❌            | ✅             | ✅                    |
| Guake        | Linux          | ⚠️ (tabs only)   | ✅           | ✅                    | ✅            | ✅             | ✅                    |
| tmux         | Cross-platform | ✅               | ✅           | ✅                    | ✅            | ✅             | ✅                    |
| WezTerm      | Cross-platform | ✅               | ✅           | ✅                    | ✅            | ✅             | ✅                    |
| Kitty        | Cross-platform | ✅\*             | ✅\*         | ✅\*                  | ✅\*          | ✅\*           | ✅\*                  |
| VSCode       | Cross-platform | ⚠️ (no tabs)     | ❌           | ✅                    | ❌            | ❌             | ❌                    |
| Cursor       | Cross-platform | ⚠️ (no tabs)     | ❌           | ✅                    | ❌            | ❌             | ❌                    |

\* **Kitty requires `allow_remote_control yes` in `kitty.conf`** to enable automation features.

**Guake** requires the optional `guake` extra (`pip install automate-terminal[guake]`) which provides `dbus-python` and `psutil` for DBus communication.

Other terminals are not supported; `automate-terminal` will exit with an error code in unsupported terminals.

## Quick Start

### Command Line

```bash
# Check if your terminal is supported
automate-terminal check

# Create a new tab
automate-terminal new-tab /path/to/project

# Switch to existing session by directory
automate-terminal switch-to --working-directory=/path/to/project

# Create new window with initialization script
automate-terminal new-window /path/to/project \
  --paste-and-run="source .env && npm run dev"

# Run a command in the currently active session
automate-terminal run-in-active-session "git status"
```

## What is possible with terminal automation?

This is the "manage expectations" section of the README.

The scope of automation covered by `automate-terminal` is "create or navigate to a terminal session in a specific working directory."

### What is a terminal emulator?

A terminal emulator, for the purposes of this project, is the thing you type your terminal commands into. For the author, it's iTerm2. For many people, it's the built-in terminal in Visual Studio Code. For hipsters, it's Ghostty. Linux users have more options than I know of, including KConsole. And there's WezTerm, and the built-in terminals for macOS and Windows. Every few years, somebody spins up a new one.

Within terminal emulators, a _session_ is, for the purposes of this project, one specific terminal running a shell. Your sessions might be organized in windows, or tabs, or splits within a window or tab.

### How are they controlled?

In **many different ways**, which is why this problem is complex enough to warrant a library! The ability to open a new tab or window, or switch to a specific existing session based on some criteria, is not standardized _at all_ among terminal emulators. The spread of what is possible for a given terminal emulator is incredibly wide, as shown by the table at the top of this README.

macOS terminals are primarily controlled via AppleScript. iTerm2, for example, has a comprehensive AppleScript API, which is why it has the best support. Ghostty has _no_ AppleScript API at all, so `automate-terminal` uses the `SystemEvents` API to "click" its menu items, and we have no way of knowing which Ghostty tab is in a particular working directory. VSCode also has no AppleScript API, but it does have its `code <path>` command to open or switch to a specific window.

**tmux** uses its native CLI commands (`tmux list-panes`, `tmux select-window`, `tmux send-keys`, etc.) and works identically across all platforms where tmux is available.

**WezTerm** uses its native CLI commands (`wezterm cli list`, `wezterm cli activate-pane`, `wezterm cli send-text`, etc.) and works identically across all platforms where WezTerm is available.

**Kitty** uses its remote control protocol (`kitten @ ls`, `kitten @ focus-window`, `kitten @ send-text`, etc.) and works across all platforms where Kitty is available. **Note: Kitty requires `allow_remote_control yes` in your `kitty.conf` file to enable automation.**

All this is to say, if you are unhappy with the level of automation provided by `automate-terminal` on macOS, switch to another terminal emulator, or lobby the authors of your favorite one to add automation support.

## Commands

### check

Detect terminal capabilities.

```bash
automate-terminal check
automate-terminal check --output=json
```

Example output:

```
Terminal: iTerm2
Terminal Program: iTerm.app
Shell: zsh
Current session ID: w0t5p1:24AF055B-8BD2-4C7F-AB1E-B310FDCBCEA1
Current working directory: /Users/steve/dev/libraries/automate-terminal

Capabilities:
  can_create_tabs: True
  can_create_windows: True
  can_list_sessions: True
  can_switch_to_session: True
  can_detect_session_id: True
  can_detect_working_directory: True
  can_paste_commands: True
  can_run_in_active_session: True
```

### new-tab

Create new tab in a specific directory, optionally pasting content into the new tab.

The term "paste" here means it will be _as if_ the user pasted text into the new terminal and hit Enter. It doesn't use your system pasteboard.

```bash
automate-terminal new-tab /path/to/dir

automate-terminal new-tab /path/to/dir --paste-and-run="echo 'I am in the new directory!'"
```

There are options to run additional scripts only in specific shells. This is useful if your wrapper tool needs to support multiple shells for workflows that require nontrivial shell commands.

```bash
automate-terminal new-tab /path/to/dir --paste-and-run-fish="echo 'I am a fish shell user'"
```

### new-window

Create new window. Takes the same arguments as `automate-terminal new-tab`.

```bash
automate-terminal new-window /path/to/dir
```

### switch-to

Switch to an existing session, returning an error no matching session can be found or your terminal doesn't provide session information. You can either pass a working directory with `--working-directory`/`--wd`, or a session ID if the session ID is known.

If you pass session ID, working directory is ignored. `--wd` is likely what you want, though.

If you are using an unsupported terminal emulator and want to open a new terminal in a given directory as a fallback, use `new-tab` or `new-window`. `automate-terminal` doesn't do this automatically because it would create unpleasant edge cases for tools that use `automate-terminal`.

```bash
# By working directory (or use --wd alias)
automate-terminal switch-to --working-directory=/path/to/dir

# By session ID (or use --id alias)
automate-terminal switch-to --session-id=w0t0p2:ABC123
```

### list-sessions

List all sessions.

```bash
automate-terminal list-sessions
automate-terminal list-sessions --output=json
```

### run-in-active-session

Run a command in the currently active terminal session.

This command sends the specified command to the active terminal session without switching windows or tabs. It's useful for programmatically executing commands in the terminal session you're currently working in.

```bash
# Run a simple command
automate-terminal run-in-active-session "echo 'Hello World'"

# Run a git command
automate-terminal run-in-active-session "git status"

# Run multiple commands
automate-terminal run-in-active-session "cd /tmp && ls -la"
```

**Note:** This feature requires terminal support. VSCode and Cursor do not support running commands in the active session. Check capabilities with `automate-terminal check` to see if your terminal supports this feature.

## Options

### Output Format

- `--output=text` - Human-readable (default)
- `--output=json` - JSON for programmatic use
- `--output=none` - Silent

### Paste and Run

Execute commands after creating/switching sessions.

```bash
--paste-and-run="echo 'I run unconditionally'"
--paste-and-run-bash="echo 'I only run if the current shell is bash'"
--paste-and-run-zsh="echo 'I only run if the current shell is zsh'"
--paste-and-run-fish="echo 'I only run if the current shell is fish'"
```

Shell-specific flags override generic `--paste-and-run` when detected shell matches.

**Note:** Some terminals (VSCode, Cursor) cannot execute paste scripts programmatically. When using `--output=json`, check the `paste_script_executed` field to determine if you need to run the script manually:

- `true`: The paste script was executed by the terminal
- `false`: The paste script was provided but the terminal cannot execute it (you should run it manually)
- Field omitted: No paste script was provided

### Debug and Dry Run

```bash
--debug     # Enable debug logging to stderr
--dry-run   # Log actions instead of executing them
```

Use `--dry-run` to see what commands would be executed without actually running them (AppleScript for macOS terminals, tmux CLI commands for tmux). Useful for debugging and understanding what the tool will do.

## Python API

```python
from automate_terminal import (
    check,
    new_tab,
    new_window,
    switch_to_session,
    list_sessions,
    get_current_session_id,
    get_shell_name,
    run_in_active_session,
    TerminalNotFoundError,
)

check(dry_run=False, debug=False) -> dict[str, str | Capabilities]

new_tab(working_directory, paste_script=None, dry_run=False, debug=False) -> bool

new_window(
  working_directory,
  paste_script=None,
  dry_run=False,
  debug=False) -> bool

switch_to_session(
  session_id=None,
  working_directory=None,
  paste_script=None,
  subdirectory_ok=False,
  dry_run=False,
  debug=False) -> bool

list_sessions(dry_run=False, debug=False) -> list[dict[str, str]]

get_current_session_id(dry_run=False, debug=False) -> str | None

get_shell_name(dry_run=False, debug=False) -> str | None

run_in_active_session(command, dry_run=False, debug=False) -> bool
```

## References

- [iTerm2 AppleScript reference](https://iterm2.com/documentation-scripting.html)
- [Kitty automation reference](https://sw.kovidgoyal.net/kitty/remote-control/)
- [WezTerm automation reference](https://wezterm.org/cli/cli/index.html)
- [tmux man page](https://man.openbsd.org/OpenBSD-current/man1/tmux.1)
