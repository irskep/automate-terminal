"""
High-level function-based API for terminal automation.

This module provides simple, convenient functions for automating terminal operations
across different terminal emulators (iTerm2, Terminal.app, Ghostty, VSCode, Cursor).

Example usage:
    >>> from automate_terminal import check, new_tab, switch_to_session
    >>>
    >>> # Check terminal capabilities
    >>> info = check()
    >>> print(f"Terminal: {info['terminal']}")
    >>>
    >>> # Create a new tab
    >>> new_tab("/path/to/project")
    >>>
    >>> # Switch to an existing session
    >>> switch_to_session(working_directory="/path/to/project")
"""

from pathlib import Path
from typing import Optional

from .applescript_service import AppleScriptService
from .models import Capabilities
from .terminal_service import TerminalNotFoundError, TerminalService


def _get_terminal_service(dry_run: bool = False, debug: bool = False) -> TerminalService:
    """
    Create and return a TerminalService instance.

    This is an internal helper function that creates the necessary services
    and returns a configured TerminalService.

    Args:
        dry_run: If True, don't actually execute commands (for testing)
        debug: If True, enable debug logging

    Returns:
        A configured TerminalService instance

    Raises:
        TerminalNotFoundError: If terminal is not supported
    """
    applescript_service = AppleScriptService(dry_run=dry_run)
    return TerminalService(applescript_service=applescript_service)


def check(dry_run: bool = False, debug: bool = False) -> dict[str, str | Capabilities]:
    """
    Check terminal type and capabilities.

    Auto-detects the current terminal emulator and returns information about
    its capabilities.

    Args:
        dry_run: If True, don't actually execute commands
        debug: If True, enable debug logging

    Returns:
        Dictionary with keys:
            - 'terminal': Name of detected terminal (e.g., 'iTerm2', 'Terminal.app')
            - 'capabilities': Capabilities object describing what the terminal can do

    Example:
        >>> info = check()
        >>> print(f"Using {info['terminal']}")
        >>> if info['capabilities'].can_create_tabs:
        ...     print("This terminal supports creating tabs")
    """
    service = _get_terminal_service(dry_run=dry_run, debug=debug)
    return service.check()


def new_tab(
    working_directory: Path | str,
    paste_script: Optional[str] = None,
    dry_run: bool = False,
    debug: bool = False,
) -> bool:
    """
    Create a new tab in the current terminal window.

    Args:
        working_directory: Directory to open the new tab in
        paste_script: Optional script to execute after creating the tab
        dry_run: If True, don't actually execute commands
        debug: If True, enable debug logging

    Returns:
        True if successful, False otherwise

    Raises:
        RuntimeError: If the terminal doesn't support creating tabs

    Example:
        >>> new_tab("/Users/steve/projects/myapp")
        >>> new_tab("/Users/steve/projects/myapp", paste_script="npm start")
    """
    service = _get_terminal_service(dry_run=dry_run, debug=debug)
    working_directory = Path(working_directory)
    return service.new_tab(working_directory=working_directory, paste_script=paste_script)


def new_window(
    working_directory: Path | str,
    paste_script: Optional[str] = None,
    dry_run: bool = False,
    debug: bool = False,
) -> bool:
    """
    Create a new terminal window.

    Args:
        working_directory: Directory to open the new window in
        paste_script: Optional script to execute after creating the window
        dry_run: If True, don't actually execute commands
        debug: If True, enable debug logging

    Returns:
        True if successful, False otherwise

    Raises:
        RuntimeError: If the terminal doesn't support creating windows

    Example:
        >>> new_window("/Users/steve/projects/myapp")
        >>> new_window("/Users/steve/projects/myapp", paste_script="npm start")
    """
    service = _get_terminal_service(dry_run=dry_run, debug=debug)
    working_directory = Path(working_directory)
    return service.new_window(working_directory=working_directory, paste_script=paste_script)


def switch_to_session(
    session_id: Optional[str] = None,
    working_directory: Optional[Path | str] = None,
    paste_script: Optional[str] = None,
    subdirectory_ok: bool = False,
    dry_run: bool = False,
    debug: bool = False,
) -> bool:
    """
    Switch to an existing terminal session.

    You can switch by either session_id or working_directory. If both are provided,
    session_id takes precedence.

    Args:
        session_id: ID of the session to switch to (terminal-specific)
        working_directory: Find and switch to session with this working directory
        paste_script: Optional script to execute after switching
        subdirectory_ok: If True, match sessions in subdirectories of working_directory
        dry_run: If True, don't actually execute commands
        debug: If True, enable debug logging

    Returns:
        True if successful, False otherwise

    Raises:
        RuntimeError: If the terminal doesn't support session switching
        ValueError: If neither session_id nor working_directory is provided

    Example:
        >>> # Switch by working directory
        >>> switch_to_session(working_directory="/Users/steve/projects/myapp")
        >>>
        >>> # Switch by session ID (iTerm2)
        >>> switch_to_session(session_id="w0t0p0:12345678-ABCD-1234-ABCD-123456789ABC")
        >>>
        >>> # Switch and run a command
        >>> switch_to_session(
        ...     working_directory="/Users/steve/projects/myapp",
        ...     paste_script="git status"
        ... )
    """
    service = _get_terminal_service(dry_run=dry_run, debug=debug)

    if working_directory is not None:
        working_directory = Path(working_directory)

    return service.switch_to_session(
        session_id=session_id,
        working_directory=working_directory,
        paste_script=paste_script,
        subdirectory_ok=subdirectory_ok,
    )


def list_sessions(
    dry_run: bool = False,
    debug: bool = False,
) -> list[dict[str, str]]:
    """
    List all terminal sessions with their IDs and working directories.

    Args:
        dry_run: If True, don't actually execute commands
        debug: If True, enable debug logging

    Returns:
        List of dictionaries, each containing:
            - 'session_id': The session identifier
            - 'working_directory': Current working directory of the session

    Raises:
        RuntimeError: If the terminal doesn't support listing sessions

    Example:
        >>> sessions = list_sessions()
        >>> for session in sessions:
        ...     print(f"{session['session_id']}: {session['working_directory']}")
    """
    service = _get_terminal_service(dry_run=dry_run, debug=debug)
    return service.list_sessions()


def get_current_session_id(
    dry_run: bool = False,
    debug: bool = False,
) -> Optional[str]:
    """
    Get the current session ID.

    Args:
        dry_run: If True, don't actually execute commands
        debug: If True, enable debug logging

    Returns:
        The current session ID, or None if it cannot be determined

    Example:
        >>> session_id = get_current_session_id()
        >>> if session_id:
        ...     print(f"Current session: {session_id}")
    """
    service = _get_terminal_service(dry_run=dry_run, debug=debug)
    return service.get_current_session_id()


def get_shell_name(
    dry_run: bool = False,
    debug: bool = False,
) -> Optional[str]:
    """
    Get the name of the current shell.

    Args:
        dry_run: If True, don't actually execute commands
        debug: If True, enable debug logging

    Returns:
        Shell name (e.g., 'bash', 'zsh', 'fish'), or None if unknown

    Example:
        >>> shell = get_shell_name()
        >>> print(f"Using shell: {shell}")
    """
    service = _get_terminal_service(dry_run=dry_run, debug=debug)
    return service.get_shell_name()


__all__ = [
    "check",
    "new_tab",
    "new_window",
    "switch_to_session",
    "list_sessions",
    "get_current_session_id",
    "get_shell_name",
]
