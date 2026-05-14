"""Tests for Kitty terminal implementation."""

from pathlib import Path


from automate_terminal.terminals.kitty import KittyTerminal


def test_open_new_tab_shell_quotes_directory(fake_applescript, fake_command):
    """Directories with spaces should be shell-quoted in the sh -c command."""
    fake_command.return_value = True
    terminal = KittyTerminal(fake_applescript, fake_command)
    terminal.open_new_tab(
        Path("/tmp/my project"),
        session_init_script="echo hi",
    )

    # Find the execute_rw call
    rw_calls = [c for c in fake_command.executed_commands if c[0] == "execute_rw"]
    assert len(rw_calls) == 1
    cmd = rw_calls[0][1]

    # The sh -c argument should contain a shell-quoted path
    sh_c_arg = cmd[-1]
    assert "'/tmp/my project'" in sh_c_arg


def test_open_new_window_shell_quotes_directory(fake_applescript, fake_command):
    """Directories with spaces should be shell-quoted in the sh -c command."""
    fake_command.return_value = True
    terminal = KittyTerminal(fake_applescript, fake_command)
    terminal.open_new_window(
        Path("/tmp/my project"),
        session_init_script="echo hi",
    )

    rw_calls = [c for c in fake_command.executed_commands if c[0] == "execute_rw"]
    assert len(rw_calls) == 1
    cmd = rw_calls[0][1]

    sh_c_arg = cmd[-1]
    assert "'/tmp/my project'" in sh_c_arg
