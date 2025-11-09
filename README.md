# automate-terminal

Automate opening of new tabs and windows in terminal programs. Currently supports iTerm2, Terminal.app, and Ghostty on macOS, with additional terminals and OSes added by request.

automate-terminal is a best-effort project. Some terminals do not support automation at all!

## Installation

```bash
pip install automate-terminal
```

```bash
mise install pip:automate-terminal
```

Or install from source:

```bash
git clone https://github.com/yourusername/automate-terminal.git
cd automate-terminal
pip install -e .
```

## Supported Terminals

| Terminal     | New Tabs/Windows | Switch by ID | Switch by Working Dir | List Sessions | Paste Commands |
| ------------ | ---------------- | ------------ | --------------------- | ------------- | -------------- |
| iTerm2       | ✅               | ✅           | ✅                    | ✅            | ✅             |
| Terminal.app | ✅               | ❌           | ✅                    | ✅            | ✅             |
| Ghostty      | ✅               | ❌           | ❌                    | ❌            | ✅             |
| VSCode       | ⚠️ (no tabs)     | ❌           | ✅                    | ❌            | ❌             |
| Cursor       | ⚠️ (no tabs)     | ❌           | ✅                    | ❌            | ❌             |

Other terminals are not supported; `automate-terminal` will exit with an error code in other terminals.

## Quick Start

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
```

## Commands

### check

Detect terminal capabilities.

```bash
automate-terminal check
automate-terminal check --output=json
```

### switch-to

Switch to existing session. Errors if not found.

```bash
# By working directory (or use --wd alias)
automate-terminal switch-to --working-directory=/path/to/dir

# By session ID (or use --id alias)
automate-terminal switch-to --session-id=w0t0p2:ABC123

# Both (session ID takes precedence)
automate-terminal switch-to \
  --session-id=w0t0p2:ABC123 \
  --working-directory=/path/to/dir

# Match sessions in subdirectories
automate-terminal switch-to --working-directory=/path/to/dir --subdirectory-ok
```

### new-tab

Create new tab.

```bash
automate-terminal new-tab /path/to/dir
```

### new-window

Create new window.

```bash
automate-terminal new-window /path/to/dir
```

### list-sessions

List all sessions.

```bash
automate-terminal list-sessions
automate-terminal list-sessions --output=json
```

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

Use `--dry-run` to see what AppleScript commands would be executed without actually running them. Useful for debugging and understanding what the tool will do.

## Environment Variables

### AUTOMATE_TERMINAL_OVERRIDE

Force `automate-terminal` to use a specific terminal implementation, bypassing automatic detection.

**Use case:** When running from VSCode/Cursor integrated terminal, you may want to manage the underlying terminal (iTerm2, Terminal.app) instead of VSCode/Cursor itself.

**Values:**
- `iterm2` - Force iTerm2 implementation
- `terminal` or `terminal.app` - Force Terminal.app implementation
- `ghostty` - Force Ghostty implementation
- `vscode` - Force VSCode implementation
- `cursor` - Force Cursor implementation

**Example:**
```bash
# From VSCode integrated terminal, list iTerm2 sessions instead of VSCode windows
export AUTOMATE_TERMINAL_OVERRIDE=iterm2
automate-terminal list-sessions

# Or inline
AUTOMATE_TERMINAL_OVERRIDE=terminal automate-terminal check
```
