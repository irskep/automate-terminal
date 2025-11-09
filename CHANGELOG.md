# Changelog

<!-- loosely based on https://keepachangelog.com/en/1.0.0/ -->

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
