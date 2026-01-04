"""Tests for iTerm2 terminal implementation."""

from pathlib import Path

import pytest

from automate_terminal.terminals.iterm2 import ITerm2Terminal


@pytest.fixture
def iterm2_terminal(fake_applescript, fake_command):
    return ITerm2Terminal(fake_applescript, fake_command)


def test_open_new_tab_escapes_session_init_script(iterm2_terminal, fake_applescript):
    """session_init_script with quotes should be escaped in AppleScript."""
    iterm2_terminal.open_new_tab(
        Path("/tmp/test"),
        session_init_script='echo "hello world"',
    )

    assert len(fake_applescript.executed_scripts) == 1
    _, script = fake_applescript.executed_scripts[0]

    # The script should contain the escaped quotes
    assert r'echo \"hello world\"' in script
    # And should NOT contain unescaped quotes that would break AppleScript
    assert 'echo "hello world"' not in script


def test_open_new_window_escapes_session_init_script(iterm2_terminal, fake_applescript):
    """session_init_script with quotes should be escaped in AppleScript."""
    iterm2_terminal.open_new_window(
        Path("/tmp/test"),
        session_init_script='source ".venv/bin/activate"',
    )

    assert len(fake_applescript.executed_scripts) == 1
    _, script = fake_applescript.executed_scripts[0]

    # The script should contain the escaped quotes
    assert r'source \".venv/bin/activate\"' in script
