"""Tests for cmd_switch_to CLI command."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from automate_terminal.cli import cmd_switch_to


def test_switch_to_success(mock_args, capsys):
    """Test switch-to returns 0 when session found and switched."""
    with patch("automate_terminal.cli.TerminalService") as mock_service:
        mock_instance = Mock()
        mock_instance.switch_to_session.return_value = True
        mock_instance.get_terminal_name.return_value = "iTerm2"
        mock_instance.get_shell_name.return_value = "zsh"
        mock_service.return_value = mock_instance

        args = mock_args(
            output="json",
            session_id="session123",
            working_directory=None,
            paste_and_run=None,
        )
        result = cmd_switch_to(args)

    assert result == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["success"] is True


def test_switch_to_no_session_found(mock_args, capsys):
    """Test switch-to returns 1 when session not found."""
    with patch("automate_terminal.cli.TerminalService") as mock_service:
        mock_instance = Mock()
        mock_instance.switch_to_session.return_value = False
        mock_instance.get_terminal_name.return_value = "iTerm2"
        mock_service.return_value = mock_instance

        args = mock_args(
            output="json",
            session_id="nonexistent",
            working_directory=None,
            paste_and_run=None,
        )
        result = cmd_switch_to(args)

    assert result == 1
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["success"] is False


def test_switch_to_missing_args(mock_args, capsys):
    """Test switch-to returns 1 when neither session_id nor working_directory provided."""
    with patch("automate_terminal.cli.TerminalService") as mock_service:
        mock_instance = Mock()
        mock_service.return_value = mock_instance

        args = mock_args(
            output="text",
            session_id=None,
            working_directory=None,
        )
        result = cmd_switch_to(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "Error:" in captured.err


def test_switch_to_calls_service_with_session_id(mock_args):
    """Test switch-to passes session_id to service correctly."""
    with patch("automate_terminal.cli.TerminalService") as mock_service:
        mock_instance = Mock()
        mock_instance.switch_to_session.return_value = True
        mock_instance.get_terminal_name.return_value = "iTerm2"
        mock_instance.get_shell_name.return_value = "zsh"
        mock_service.return_value = mock_instance

        args = mock_args(
            session_id="test-session",
            working_directory=None,
            paste_and_run=None,
        )
        cmd_switch_to(args)

        mock_instance.switch_to_session.assert_called_once()
        call_args = mock_instance.switch_to_session.call_args
        assert call_args.kwargs["session_id"] == "test-session"


def test_switch_to_calls_service_with_working_directory(mock_args):
    """Test switch-to passes working_directory to service correctly."""
    with patch("automate_terminal.cli.TerminalService") as mock_service:
        mock_instance = Mock()
        mock_instance.switch_to_session.return_value = True
        mock_instance.get_terminal_name.return_value = "iTerm2"
        mock_instance.get_shell_name.return_value = "zsh"
        mock_service.return_value = mock_instance

        args = mock_args(
            session_id=None,
            working_directory="/tmp/test",
            paste_and_run=None,
        )
        cmd_switch_to(args)

        mock_instance.switch_to_session.assert_called_once()
        call_args = mock_instance.switch_to_session.call_args
        assert call_args.kwargs["working_directory"] == Path("/tmp/test")


def test_switch_to_passes_subdirectory_ok_flag(mock_args):
    """Test switch-to passes subdirectory_ok flag to service."""
    with patch("automate_terminal.cli.TerminalService") as mock_service:
        mock_instance = Mock()
        mock_instance.switch_to_session.return_value = True
        mock_instance.get_terminal_name.return_value = "iTerm2"
        mock_instance.get_shell_name.return_value = "zsh"
        mock_service.return_value = mock_instance

        args = mock_args(
            session_id=None,
            working_directory="/tmp/test",
            paste_and_run=None,
            subdirectory_ok=True,
        )
        cmd_switch_to(args)

        call_args = mock_instance.switch_to_session.call_args
        assert call_args.kwargs["subdirectory_ok"] is True


def test_switch_to_error_message_with_subdirectories(mock_args, capsys):
    """Test error message mentions --subdirectory-ok when subdirectories exist."""
    with patch("automate_terminal.cli.TerminalService") as mock_service:
        mock_instance = Mock()
        mock_instance.switch_to_session.return_value = False
        mock_instance.find_session_by_directory.return_value = "some-session-id"
        mock_instance.get_terminal_name.return_value = "iTerm2"
        mock_service.return_value = mock_instance

        args = mock_args(
            output="text",
            session_id=None,
            working_directory="/tmp/test",
            paste_and_run=None,
            subdirectory_ok=False,
        )
        result = cmd_switch_to(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "--subdirectory-ok" in captured.err
        assert "subdirectories" in captured.err


def test_switch_to_error_message_without_subdirectories(mock_args, capsys):
    """Test normal error message when no subdirectories exist."""
    with patch("automate_terminal.cli.TerminalService") as mock_service:
        mock_instance = Mock()
        mock_instance.switch_to_session.return_value = False
        mock_instance.find_session_by_directory.return_value = None
        mock_instance.get_terminal_name.return_value = "iTerm2"
        mock_service.return_value = mock_instance

        args = mock_args(
            output="text",
            session_id=None,
            working_directory="/tmp/test",
            paste_and_run=None,
            subdirectory_ok=False,
        )
        result = cmd_switch_to(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "No matching session found" in captured.err
        assert "--subdirectory-ok" not in captured.err
