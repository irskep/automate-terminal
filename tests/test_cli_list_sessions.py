"""Tests for cmd_list_sessions CLI command."""

import json
from unittest.mock import Mock, patch

from automate_terminal.cli import cmd_list_sessions


def test_list_sessions_success(mock_args, capsys):
    """Test list-sessions returns 0 and outputs sessions."""
    with patch("automate_terminal.cli.TerminalService") as mock_service:
        mock_instance = Mock()
        mock_instance.list_sessions.return_value = [
            {"session_id": "s1", "working_directory": "/home", "shell": "zsh"},
            {"session_id": "s2", "working_directory": "/tmp", "shell": "bash"},
        ]
        mock_instance.get_terminal_name.return_value = "iTerm2"
        mock_service.return_value = mock_instance

        args = mock_args(output="json")
        result = cmd_list_sessions(args)

    assert result == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["terminal"] == "iTerm2"
    assert len(data["sessions"]) == 2


def test_list_sessions_text_output(mock_args, capsys):
    """Test list-sessions text output format."""
    with patch("automate_terminal.cli.TerminalService") as mock_service:
        mock_instance = Mock()
        mock_instance.list_sessions.return_value = [
            {"session_id": "s1", "working_directory": "/home", "shell": "zsh"},
        ]
        mock_instance.get_terminal_name.return_value = "iTerm2"
        mock_service.return_value = mock_instance

        args = mock_args(output="text")
        result = cmd_list_sessions(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "iTerm2 Sessions:" in captured.out
    assert "s1" in captured.out
    assert "/home" in captured.out


def test_list_sessions_capability_error(mock_args, capsys):
    """Test list-sessions returns 1 when RuntimeError raised (missing capability)."""
    with patch("automate_terminal.cli.TerminalService") as mock_service:
        mock_instance = Mock()
        mock_instance.list_sessions.side_effect = RuntimeError("not supported")
        mock_service.return_value = mock_instance

        args = mock_args(output="text")
        result = cmd_list_sessions(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "Error:" in captured.err
