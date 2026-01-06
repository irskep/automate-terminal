"""Tests for Guake terminal implementation."""

import pytest

from automate_terminal.terminals import guake as guake_module
from automate_terminal.terminals.guake import GuakeTerminal


@pytest.fixture
def guake_terminal(monkeypatch, fake_applescript, fake_command):
    """Create a GuakeTerminal with gdbus availability forced on."""
    monkeypatch.setattr(guake_module, "HAS_GDBUS", True)
    return GuakeTerminal(fake_applescript, fake_command)


def test_guake_detect_requires_env(monkeypatch, guake_terminal):
    """Guake detection succeeds only when environment and gdbus are present."""
    monkeypatch.delenv("GUAKE_TAB_UUID", raising=False)
    assert guake_terminal.detect(None, "Linux") is False

    monkeypatch.setenv("GUAKE_TAB_UUID", "tab-123")
    assert guake_terminal.detect(None, "Linux") is True

    # Simulate missing gdbus binary
    monkeypatch.setattr(guake_module, "HAS_GDBUS", False)
    assert guake_terminal.detect(None, "Linux") is False


def test_guake_get_shell_processes(
    tmp_path, monkeypatch, fake_applescript, fake_command
):
    """_get_shell_processes enumerates shells under a fake /proc tree."""
    proc_root = tmp_path / "proc"
    proc_root.mkdir()

    # Guake process
    guake_pid = 1000
    guake_dir = proc_root / str(guake_pid)
    guake_dir.mkdir()
    (guake_dir / "comm").write_text("guake\n")
    (guake_dir / "status").write_text("Name:\tguake\nPPid:\t1\n")
    (guake_dir / "environ").write_bytes(b"")
    (guake_dir / "cwd").symlink_to(tmp_path)

    # Shell process running under Guake
    shell_pid = 1001
    shell_dir = proc_root / str(shell_pid)
    shell_dir.mkdir()
    (shell_dir / "comm").write_text("bash\n")
    (shell_dir / "status").write_text(f"Name:\tbash\nPPid:\t{guake_pid}\n")
    environ = b"GUAKE_TAB_UUID=tab-abc\0SHELL=/bin/bash\0"
    (shell_dir / "environ").write_bytes(environ)
    target_cwd = tmp_path / "project"
    target_cwd.mkdir()
    (shell_dir / "cwd").symlink_to(target_cwd)

    # Unrelated process should be ignored
    other_dir = proc_root / "2000"
    other_dir.mkdir()
    (other_dir / "comm").write_text("python\n")
    (other_dir / "status").write_text("Name:\tpython\nPPid:\t1\n")
    (other_dir / "environ").write_bytes(b"")
    (other_dir / "cwd").symlink_to(tmp_path)

    monkeypatch.setattr(guake_module, "PROC_ROOT", proc_root)

    terminal = GuakeTerminal(fake_applescript, fake_command)
    sessions = terminal._get_shell_processes()

    assert sessions == [
        {
            "tab_uuid": "tab-abc",
            "cwd": str(target_cwd),
            "pid": shell_pid,
        }
    ]


def test_guake_run_in_active_session(monkeypatch, fake_applescript, fake_command):
    """run_in_active_session sends commands through gdbus helper."""
    monkeypatch.setattr(guake_module, "HAS_GDBUS", True)

    outputs = iter(["('true',)"])

    def fake_execute_r_with_output(cmd, timeout=10, description=None):
        fake_command.executed_commands.append(
            ("execute_r_with_output", cmd, timeout, description)
        )
        try:
            return next(outputs)
        except StopIteration:
            return "('true',)"

    monkeypatch.setattr(
        fake_command, "execute_r_with_output", fake_execute_r_with_output
    )

    terminal = GuakeTerminal(fake_applescript, fake_command)
    assert terminal.run_in_active_session("echo hi") is True

    # execute_command should have been invoked
    call = fake_command.executed_commands[-1]
    assert "execute_command" in " ".join(call[1])


def test_guake_open_new_tab(monkeypatch, fake_applescript, fake_command, tmp_path):
    """open_new_tab passes directory path directly without string: prefix."""
    monkeypatch.setattr(guake_module, "HAS_GDBUS", True)

    outputs = iter(["()", "(1,)"])

    def fake_execute_r_with_output(cmd, timeout=10, description=None):
        fake_command.executed_commands.append(
            ("execute_r_with_output", cmd, timeout, description)
        )
        try:
            return next(outputs)
        except StopIteration:
            return "()"

    monkeypatch.setattr(
        fake_command, "execute_r_with_output", fake_execute_r_with_output
    )

    terminal = GuakeTerminal(fake_applescript, fake_command)
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    assert terminal.open_new_tab(target_dir) is True

    # add_tab should have been invoked with the path directly
    add_tab_call = fake_command.executed_commands[0]
    cmd_list = add_tab_call[1]
    assert "add_tab" in " ".join(cmd_list)
    # Verify the path is passed directly without "string:" prefix
    assert str(target_dir) in cmd_list
    assert f'string:"{target_dir}"' not in cmd_list
