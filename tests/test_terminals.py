"""Tests for terminal detect() methods."""

import pytest

from automate_terminal.terminals.apple import TerminalAppTerminal
from automate_terminal.terminals.ghostty import GhosttyMacTerminal
from automate_terminal.terminals.iterm2 import ITerm2Terminal
from automate_terminal.terminals.kitty import KittyTerminal
from automate_terminal.terminals.tmux import TmuxTerminal
from automate_terminal.terminals.vscode import VSCodeTerminal
from automate_terminal.terminals.wezterm import WeztermTerminal


@pytest.mark.parametrize(
    "terminal_cls,term_program,platform,expected",
    [
        # iTerm2
        (ITerm2Terminal, "iTerm.app", "Darwin", True),
        (ITerm2Terminal, "Apple_Terminal", "Darwin", False),
        (ITerm2Terminal, "iTerm.app", "Linux", False),
        (ITerm2Terminal, None, "Darwin", False),
        # Terminal.app
        (TerminalAppTerminal, "Apple_Terminal", "Darwin", True),
        (TerminalAppTerminal, "iTerm.app", "Darwin", False),
        (TerminalAppTerminal, "Apple_Terminal", "Linux", False),
        # Ghostty
        (GhosttyMacTerminal, "ghostty", "Darwin", True),
        (GhosttyMacTerminal, "iTerm.app", "Darwin", False),
        (GhosttyMacTerminal, "ghostty", "Linux", False),
    ],
)
def test_terminal_detect(
    terminal_cls, term_program, platform, expected, fake_applescript, fake_command
):
    """Test terminal detection based on TERM_PROGRAM and platform."""
    terminal = terminal_cls(fake_applescript, fake_command)
    assert terminal.detect(term_program, platform) == expected


def test_tmux_terminal_detect(fake_applescript, fake_command, monkeypatch):
    """Test tmux detection based on TMUX environment variable."""
    terminal = TmuxTerminal(fake_applescript, fake_command)

    # tmux is detected when TMUX env var is set
    monkeypatch.setenv("TMUX", "/tmp/tmux-501/default,12345,0")
    assert terminal.detect(None, "Darwin") is True
    assert terminal.detect(None, "Linux") is True
    assert terminal.detect("iTerm.app", "Darwin") is True  # Can be nested

    # tmux is not detected when TMUX env var is not set
    monkeypatch.delenv("TMUX", raising=False)
    assert terminal.detect(None, "Darwin") is False
    assert terminal.detect(None, "Linux") is False


def test_wezterm_terminal_detect(fake_applescript, fake_command, monkeypatch):
    """Test WezTerm detection based on WEZTERM_PANE environment variable."""
    terminal = WeztermTerminal(fake_applescript, fake_command)

    # WezTerm is detected when WEZTERM_PANE env var is set
    monkeypatch.setenv("WEZTERM_PANE", "0")
    assert terminal.detect(None, "Darwin") is True
    assert terminal.detect(None, "Linux") is True
    assert terminal.detect(None, "Windows") is True
    assert terminal.detect("iTerm.app", "Darwin") is True  # Can be nested

    # WezTerm is not detected when WEZTERM_PANE env var is not set
    monkeypatch.delenv("WEZTERM_PANE", raising=False)
    assert terminal.detect(None, "Darwin") is False
    assert terminal.detect(None, "Linux") is False


def test_kitty_terminal_detect(fake_applescript, fake_command, monkeypatch):
    """Test Kitty detection based on KITTY_WINDOW_ID environment variable."""
    terminal = KittyTerminal(fake_applescript, fake_command)

    # Kitty is detected when KITTY_WINDOW_ID env var is set
    monkeypatch.setenv("KITTY_WINDOW_ID", "1")
    assert terminal.detect(None, "Darwin") is True
    assert terminal.detect(None, "Linux") is True
    assert terminal.detect("iTerm.app", "Darwin") is True  # Can be nested

    # Kitty is not detected when KITTY_WINDOW_ID env var is not set
    monkeypatch.delenv("KITTY_WINDOW_ID", raising=False)
    assert terminal.detect(None, "Darwin") is False
    assert terminal.detect(None, "Linux") is False


@pytest.mark.parametrize(
    "variant,term_program,cursor_trace_id,expected",
    [
        # VSCode variant
        ("vscode", "vscode", None, True),
        ("vscode", "vscode", "some-id", False),  # Cursor detected
        ("vscode", "iTerm.app", None, False),
        ("vscode", None, None, False),
        # Cursor variant
        ("cursor", "vscode", "some-id", True),
        ("cursor", "vscode", None, False),  # VSCode detected
        ("cursor", "iTerm.app", "some-id", False),
        ("cursor", None, "some-id", False),
    ],
)
def test_vscode_terminal_detect(
    variant,
    term_program,
    cursor_trace_id,
    expected,
    fake_applescript,
    fake_command,
    monkeypatch,
):
    """Test VSCode/Cursor detection based on TERM_PROGRAM and CURSOR_TRACE_ID."""
    # Set or unset CURSOR_TRACE_ID environment variable
    if cursor_trace_id is not None:
        monkeypatch.setenv("CURSOR_TRACE_ID", cursor_trace_id)
    else:
        monkeypatch.delenv("CURSOR_TRACE_ID", raising=False)

    terminal = VSCodeTerminal(fake_applescript, fake_command, variant=variant)
    assert terminal.detect(term_program, "Darwin") == expected


def test_vscode_terminal_properties(fake_applescript, fake_command):
    """Test that VSCode terminal properties vary by variant."""
    vscode = VSCodeTerminal(fake_applescript, fake_command, variant="vscode")
    assert vscode.cli_command == "code"
    assert vscode.display_name == "VSCode"
    assert "Code" in vscode.app_names or "Visual Studio Code" in vscode.app_names

    cursor = VSCodeTerminal(fake_applescript, fake_command, variant="cursor")
    assert cursor.cli_command == "cursor"
    assert cursor.display_name == "Cursor"
    assert "Cursor" in cursor.app_names


def test_vscode_terminal_capabilities(fake_applescript, fake_command):
    """Test that VSCode terminal reports correct capabilities."""
    terminal = VSCodeTerminal(fake_applescript, fake_command, variant="vscode")
    caps = terminal.get_capabilities()

    assert caps.can_create_tabs is False
    assert caps.can_create_windows is True
    assert caps.can_list_sessions is False  # VSCode doesn't expose workspace paths
    assert caps.can_switch_to_session is True  # Can switch by working directory via CLI
    assert caps.can_detect_session_id is False  # No session IDs
    assert caps.can_paste_commands is False


def test_tmux_terminal_capabilities(fake_applescript, fake_command):
    """Test that tmux terminal reports correct capabilities."""
    terminal = TmuxTerminal(fake_applescript, fake_command)
    caps = terminal.get_capabilities()

    assert caps.can_create_tabs is True
    assert caps.can_create_windows is True
    assert caps.can_list_sessions is True
    assert caps.can_switch_to_session is True
    assert caps.can_detect_session_id is True
    assert caps.can_detect_working_directory is True
    assert caps.can_paste_commands is True
    assert caps.can_run_in_active_session is True


def test_wezterm_terminal_capabilities(fake_applescript, fake_command):
    """Test that WezTerm terminal reports correct capabilities."""
    terminal = WeztermTerminal(fake_applescript, fake_command)
    caps = terminal.get_capabilities()

    assert caps.can_create_tabs is True
    assert caps.can_create_windows is True
    assert caps.can_list_sessions is True
    assert caps.can_switch_to_session is True
    assert caps.can_detect_session_id is True
    assert caps.can_detect_working_directory is True
    assert caps.can_paste_commands is True
    assert caps.can_run_in_active_session is True


def test_kitty_terminal_capabilities(fake_applescript, fake_command):
    """Test that Kitty terminal reports correct capabilities."""
    terminal = KittyTerminal(fake_applescript, fake_command)
    caps = terminal.get_capabilities()

    assert caps.can_create_tabs is True
    assert caps.can_create_windows is True
    assert caps.can_list_sessions is True
    assert caps.can_switch_to_session is True
    assert caps.can_detect_session_id is True
    assert caps.can_detect_working_directory is True
    assert caps.can_paste_commands is True
    assert caps.can_run_in_active_session is True
