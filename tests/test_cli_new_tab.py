"""Tests for cmd_new_tab CLI command."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from automate_terminal.cli import cmd_new_tab


def test_new_tab_success(mock_args, capsys):
    """Test new-tab returns 0 when tab created successfully."""
    with patch("automate_terminal.cli.TerminalService") as mock_service:
        mock_instance = Mock()
        mock_instance.new_tab.return_value = True
        mock_instance.get_terminal_name.return_value = "iTerm2"
        mock_instance.get_shell_name.return_value = "zsh"
        mock_service.return_value = mock_instance

        args = mock_args(
            output="json",
            working_directory="/tmp/test",
            paste_and_run=None,
        )
        result = cmd_new_tab(args)

    assert result == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["success"] is True
    assert data["action"] == "created_new_tab"


def test_new_tab_failed(mock_args, capsys):
    """Test new-tab returns 1 when tab creation fails."""
    with patch("automate_terminal.cli.TerminalService") as mock_service:
        mock_instance = Mock()
        mock_instance.new_tab.return_value = False
        mock_instance.get_terminal_name.return_value = "iTerm2"
        mock_service.return_value = mock_instance

        args = mock_args(
            output="json",
            working_directory="/tmp/test",
            paste_and_run=None,
        )
        result = cmd_new_tab(args)

    assert result == 1
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["success"] is False


def test_new_tab_capability_error(mock_args, capsys):
    """Test new-tab returns 1 when RuntimeError raised (missing capability)."""
    with patch("automate_terminal.cli.TerminalService") as mock_service:
        mock_instance = Mock()
        mock_instance.new_tab.side_effect = RuntimeError("not supported")
        mock_service.return_value = mock_instance

        args = mock_args(
            output="text",
            working_directory="/tmp/test",
            paste_and_run=None,
        )
        result = cmd_new_tab(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "Error:" in captured.err


def test_new_tab_passes_working_directory(mock_args):
    """Test new-tab passes working_directory to service."""
    with patch("automate_terminal.cli.TerminalService") as mock_service:
        mock_instance = Mock()
        mock_instance.new_tab.return_value = True
        mock_instance.get_terminal_name.return_value = "iTerm2"
        mock_instance.get_shell_name.return_value = "zsh"
        mock_service.return_value = mock_instance

        args = mock_args(
            working_directory="/tmp/mydir",
            paste_and_run=None,
        )
        cmd_new_tab(args)

        mock_instance.new_tab.assert_called_once()
        call_args = mock_instance.new_tab.call_args
        assert call_args[0][0] == Path("/tmp/mydir")
