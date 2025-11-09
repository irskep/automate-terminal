"""Tests for terminal detect() methods."""

import pytest

from automate_terminal.terminals.apple import TerminalAppTerminal
from automate_terminal.terminals.ghostty import GhosttyMacTerminal
from automate_terminal.terminals.iterm2 import ITerm2Terminal
from automate_terminal.terminals.vscode import VSCodeTerminal


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
    terminal_cls, term_program, platform, expected, fake_applescript
):
    """Test terminal detection based on TERM_PROGRAM and platform."""
    terminal = terminal_cls(fake_applescript)
    assert terminal.detect(term_program, platform) == expected


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
    assert caps.can_switch_to_session is True  # CLI works everywhere
    assert caps.can_detect_session_id is False
    assert caps.can_paste_commands is False
