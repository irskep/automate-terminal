"""Tests for terminal detect() methods."""

import pytest

from automate_terminal.terminals.apple import TerminalAppTerminal
from automate_terminal.terminals.ghostty import GhosttyMacTerminal
from automate_terminal.terminals.iterm2 import ITerm2Terminal


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
