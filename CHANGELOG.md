# Changelog

<!-- loosely based on https://keepachangelog.com/en/1.0.0/ -->

## 0.1.8 - 2025-11-18

### Added

### Changed

- Guake dependencies (`dbus-python` and `psutil`) are now optional; install with `pip install automate-terminal[guake]`

### Fixed

## 0.1.7 - 2025-11-15

### Added

- Support for Guake, courtesy of @fprochazka

### Changed

### Fixed

## 0.1.6 - 2025-11-09

### Added

### Changed

### Fixed

- Fixed `TypeError` in Python API when calling `check()` and other API functions due to incorrect service initialization

## 0.1.5 - 2025-11-09

### Added

### Changed

- Tweaked how Terminal.app reports capabilities

### Fixed

## 0.1.4 - 2025-11-09

### Added

- WezTerm terminal support
  - Full support for all capabilities: create tabs/windows, switch by ID or directory, list sessions, paste commands, run in active session
  - Uses `$WEZTERM_PANE` for session identification
  - Works cross-platform (macOS, Linux, BSD, Windows)
- Kitty terminal support
  - Full support for all capabilities: create tabs/windows, switch by ID or directory, list sessions, paste commands, run in active session
  - Uses `$KITTY_WINDOW_ID` for session identification
  - Works cross-platform (macOS, Linux, BSD)
  - Requires `allow_remote_control yes` in `kitty.conf`

### Changed

### Fixed

## 0.1.3 - 2025-11-09

### Added

- tmux terminal support
  - Full support for all capabilities: create tabs/windows, switch by ID or directory, list sessions, paste commands, run in active session
  - Uses `$TMUX_PANE` for session identification
  - Works cross-platform (macOS, Linux, etc.)

### Changed

### Fixed

## 0.1.2 - 2025-11-08

### Added

- Python API
  - `check()` - Check terminal type and capabilities
  - `new_tab()` - Create new tab
  - `new_window()` - Create new window
  - `switch_to_session()` - Switch to existing session
  - `list_sessions()` - List all sessions
  - `get_current_session_id()` - Get current session ID
  - `get_shell_name()` - Get shell name
  - `TerminalNotFoundError` exception for unsupported terminals
- Improve `check` output

### Changed

### Fixed

- Terminal.app `list_sessions()` no longer duplicates working directory as session_id

## 0.1.1 - 2025-01-08

### Added

- VSCode and Cursor terminal support
  - `new-window` command (automatically switches to existing window or opens new one)
  - `switch-to` command
  - Limitations: no session listing, no command pasting, no tab creation
- `AUTOMATE_TERMINAL_OVERRIDE` environment variable to force specific terminal implementation
- `paste_script_executed` field in JSON output to indicate whether paste scripts were executed

### Changed

### Fixed

## 0.1.0 - 2025-11-08

Initial release.
