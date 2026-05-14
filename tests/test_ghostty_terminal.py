"""Tests for Ghostty terminal implementation."""

from pathlib import Path

from automate_terminal.terminals.ghostty import GhosttyMacTerminal


def test_open_new_tab_no_double_escape(fake_applescript, fake_command):
    """The keystroke command should not double-escape the text."""
    terminal = GhosttyMacTerminal(fake_applescript, fake_command)
    terminal.open_new_tab(
        Path("/tmp/test"),
        session_init_script='echo "hello"',
    )

    assert len(fake_applescript.executed_scripts) == 1
    _, script = fake_applescript.executed_scripts[0]

    # A single backslash before the quote = correctly escaped once.
    # Double-escaped would produce \\\".
    assert r'echo \"hello\"' in script
    assert r'echo \\\"hello\\\"' not in script


def test_open_new_window_no_double_escape(fake_applescript, fake_command):
    """The keystroke command should not double-escape the text."""
    terminal = GhosttyMacTerminal(fake_applescript, fake_command)
    terminal.open_new_window(
        Path("/tmp/test"),
        session_init_script='echo "hello"',
    )

    assert len(fake_applescript.executed_scripts) == 1
    _, script = fake_applescript.executed_scripts[0]

    assert r'echo \"hello\"' in script
    assert r'echo \\\"hello\\\"' not in script
