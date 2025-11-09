"""Tests for cmd_check CLI command."""

import json
from unittest.mock import Mock, patch

from automate_terminal.cli import cmd_check
from automate_terminal.models import Capabilities
from automate_terminal.terminal_service import TerminalNotFoundError


def test_cmd_check_success(mock_args, capsys):
    """Test check command returns 0 and outputs capabilities when terminal found."""
    capabilities = Capabilities(
        can_create_tabs=True,
        can_create_windows=True,
        can_list_sessions=True,
        can_switch_to_session=True,
        can_detect_session_id=True,
        can_detect_working_directory=True,
        can_paste_commands=True,
        can_run_in_active_session=True,
    )

    # Mock TerminalService to return our fake
    with patch("automate_terminal.cli.TerminalService") as mock_service:
        mock_instance = Mock()
        mock_instance.get_terminal_name.return_value = "iTerm2"
        mock_instance.get_shell_name.return_value = "zsh"
        mock_instance.get_current_session_id.return_value = "session123"
        mock_instance.get_capabilities.return_value = capabilities
        mock_service.return_value = mock_instance

        args = mock_args(output="json")
        result = cmd_check(args)

    assert result == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["terminal"] == "iTerm2"
    assert "capabilities" in data


def test_cmd_check_terminal_not_found(mock_args, capsys):
    """Test check command returns 1 when terminal not supported."""
    with (
        patch("automate_terminal.cli.TerminalService") as mock_service,
        patch("os.getenv", return_value="unsupported"),
    ):
        mock_service.side_effect = TerminalNotFoundError()

        args = mock_args(output="json")
        result = cmd_check(args)

    assert result == 1
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "error" in data
    assert data["terminal"] == "unknown"


def test_cmd_check_text_output(mock_args, capsys):
    """Test check command text output format."""
    capabilities = Capabilities(
        can_create_tabs=True,
        can_create_windows=False,
        can_list_sessions=False,
        can_switch_to_session=False,
        can_detect_session_id=False,
        can_detect_working_directory=True,
        can_paste_commands=False,
        can_run_in_active_session=False,
    )

    with patch("automate_terminal.cli.TerminalService") as mock_service:
        mock_instance = Mock()
        mock_instance.get_terminal_name.return_value = "iTerm2"
        mock_instance.get_capabilities.return_value = capabilities
        mock_instance.get_shell_name.return_value = "zsh"
        mock_instance.get_current_session_id.return_value = None
        mock_service.return_value = mock_instance

        args = mock_args(output="text")
        result = cmd_check(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "Terminal: iTerm2" in captured.out
    assert "Shell: zsh" in captured.out
