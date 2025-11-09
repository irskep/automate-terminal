"""Tests for CLI helper functions."""

import json

from automate_terminal.cli import (
    get_paste_script,
    output,
    output_error,
    will_paste_script_execute,
)
from automate_terminal.models import Capabilities


def test_output_json(capsys):
    """Test JSON output goes to stdout."""
    data = {"key": "value"}
    output("json", data, "ignored text")
    captured = capsys.readouterr()
    assert json.loads(captured.out) == data
    assert captured.err == ""


def test_output_text(capsys):
    """Test text output goes to stdout."""
    output("text", {}, "hello world")
    captured = capsys.readouterr()
    assert captured.out == "hello world\n"
    assert captured.err == ""


def test_output_none(capsys):
    """Test none output produces no output."""
    output("none", {"key": "value"}, "hello")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_output_error_json(capsys):
    """Test error JSON output goes to stderr with success=False."""
    output_error("test error", "json")
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["success"] is False
    assert data["error"] == "test error"


def test_output_error_text(capsys):
    """Test error text output goes to stderr with Error: prefix."""
    output_error("test error", "text")
    captured = capsys.readouterr()
    assert "Error: test error" in captured.err


def test_output_error_with_extra_data(capsys):
    """Test error output includes extra kwargs in JSON."""
    output_error("test error", "json", terminal="iTerm2", code=123)
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["success"] is False
    assert data["error"] == "test error"
    assert data["terminal"] == "iTerm2"
    assert data["code"] == 123


def test_get_paste_script_shell_specific(mock_args):
    """Test shell-specific script is used when available."""

    class FakeService:
        def get_shell_name(self):
            return "zsh"

    args = mock_args(paste_and_run_zsh="zsh script", paste_and_run=None)
    result = get_paste_script(args, FakeService())
    assert result == "zsh script"


def test_get_paste_script_generic_only(mock_args):
    """Test generic script is used when no shell-specific script."""

    class FakeService:
        def get_shell_name(self):
            return "bash"

    args = mock_args(
        paste_and_run="generic script",
        paste_and_run_bash=None,
        paste_and_run_zsh=None,
        paste_and_run_fish=None,
        paste_and_run_powershell=None,
        paste_and_run_nushell=None,
    )
    result = get_paste_script(args, FakeService())
    assert result == "generic script"


def test_get_paste_script_both_joined(mock_args):
    """Test both shell-specific and generic scripts are joined."""

    class FakeService:
        def get_shell_name(self):
            return "zsh"

    args = mock_args(paste_and_run="generic", paste_and_run_zsh="specific")
    result = get_paste_script(args, FakeService())
    assert result == "specific; generic"


def test_get_paste_script_none(mock_args):
    """Test returns None when no scripts provided."""

    class FakeService:
        def get_shell_name(self):
            return "bash"

    args = mock_args(
        paste_and_run=None,
        paste_and_run_bash=None,
        paste_and_run_zsh=None,
        paste_and_run_fish=None,
        paste_and_run_powershell=None,
        paste_and_run_nushell=None,
    )
    result = get_paste_script(args, FakeService())
    assert result is None


def test_will_paste_script_execute_returns_none_when_no_script():
    """Test will_paste_script_execute returns None when no script provided."""

    class FakeService:
        def get_capabilities(self):
            return Capabilities(
                can_create_tabs=True,
                can_create_windows=True,
                can_list_sessions=True,
                can_switch_to_session=True,
                can_detect_session_id=True,
                can_detect_working_directory=True,
                can_paste_commands=True,
                can_run_in_active_session=True,
            )

    result = will_paste_script_execute(None, FakeService())
    assert result is None


def test_will_paste_script_execute_returns_true_when_supported():
    """Test will_paste_script_execute returns True when terminal supports pasting."""

    class FakeService:
        def get_capabilities(self):
            return Capabilities(
                can_create_tabs=True,
                can_create_windows=True,
                can_list_sessions=True,
                can_switch_to_session=True,
                can_detect_session_id=True,
                can_detect_working_directory=True,
                can_paste_commands=True,
                can_run_in_active_session=True,
            )

    result = will_paste_script_execute("echo hello", FakeService())
    assert result is True


def test_will_paste_script_execute_returns_false_when_not_supported():
    """Test will_paste_script_execute returns False when terminal doesn't support pasting."""

    class FakeService:
        def get_capabilities(self):
            return Capabilities(
                can_create_tabs=False,
                can_create_windows=True,
                can_list_sessions=False,
                can_switch_to_session=False,
                can_detect_session_id=False,
                can_detect_working_directory=True,
                can_paste_commands=False,  # VSCode/Cursor case
                can_run_in_active_session=False,
            )

    result = will_paste_script_execute("echo hello", FakeService())
    assert result is False
