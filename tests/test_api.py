"""Tests for the high-level function-based API."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from automate_terminal import api
from automate_terminal.models import Capabilities


@pytest.fixture
def mock_terminal_service():
    """Create a mock TerminalService with default behavior."""
    mock = MagicMock()
    mock.get_terminal_name.return_value = "iTerm2"
    mock.get_capabilities.return_value = Capabilities(
        can_create_tabs=True,
        can_create_windows=True,
        can_list_sessions=True,
        can_switch_to_session=True,
        can_detect_session_id=True,
        can_detect_working_directory=True,
        can_paste_commands=True,
        can_run_in_active_session=True,
    )
    mock.get_current_session_id.return_value = "session-123"
    mock.get_shell_name.return_value = "zsh"
    mock.new_tab.return_value = True
    mock.new_window.return_value = True
    mock.switch_to_session.return_value = True
    mock.list_sessions.return_value = [
        {"session_id": "session1", "working_directory": "/path/to/dir"}
    ]
    return mock


def test_check(mock_terminal_service):
    """Test check() calls TerminalService methods to build result."""
    with patch(
        "automate_terminal.api._get_terminal_service",
        return_value=mock_terminal_service,
    ):
        result = api.check()

    assert result["terminal"] == "iTerm2"
    assert result["capabilities"]["can_create_tabs"] is True
    mock_terminal_service.get_terminal_name.assert_called_once()
    mock_terminal_service.get_capabilities.assert_called_once()
    mock_terminal_service.get_shell_name.assert_called_once()
    mock_terminal_service.get_current_session_id.assert_called_once()


def test_check_with_debug_and_dry_run(mock_terminal_service):
    """Test check() passes debug and dry_run to service creation."""
    with patch(
        "automate_terminal.api._get_terminal_service",
        return_value=mock_terminal_service,
    ) as mock_get:
        api.check(debug=True, dry_run=True)

    mock_get.assert_called_once_with(dry_run=True, debug=True)


def test_new_tab_with_path_string(mock_terminal_service):
    """Test new_tab() with string path."""
    with patch(
        "automate_terminal.api._get_terminal_service",
        return_value=mock_terminal_service,
    ):
        result = api.new_tab("/path/to/project")

    assert result is True
    mock_terminal_service.new_tab.assert_called_once()
    call_args = mock_terminal_service.new_tab.call_args
    assert call_args.kwargs["working_directory"] == Path("/path/to/project")
    assert call_args.kwargs["paste_script"] is None


def test_new_tab_with_path_object(mock_terminal_service):
    """Test new_tab() with Path object."""
    working_dir = Path("/path/to/project")
    with patch(
        "automate_terminal.api._get_terminal_service",
        return_value=mock_terminal_service,
    ):
        result = api.new_tab(working_dir)

    assert result is True
    mock_terminal_service.new_tab.assert_called_once()
    call_args = mock_terminal_service.new_tab.call_args
    assert call_args.kwargs["working_directory"] == working_dir


def test_new_tab_with_paste_script(mock_terminal_service):
    """Test new_tab() with paste script."""
    with patch(
        "automate_terminal.api._get_terminal_service",
        return_value=mock_terminal_service,
    ):
        result = api.new_tab("/path/to/project", paste_script="npm start")

    assert result is True
    mock_terminal_service.new_tab.assert_called_once()
    call_args = mock_terminal_service.new_tab.call_args
    assert call_args.kwargs["paste_script"] == "npm start"


def test_new_window_with_path_string(mock_terminal_service):
    """Test new_window() with string path."""
    with patch(
        "automate_terminal.api._get_terminal_service",
        return_value=mock_terminal_service,
    ):
        result = api.new_window("/path/to/project")

    assert result is True
    mock_terminal_service.new_window.assert_called_once()
    call_args = mock_terminal_service.new_window.call_args
    assert call_args.kwargs["working_directory"] == Path("/path/to/project")
    assert call_args.kwargs["paste_script"] is None


def test_new_window_with_paste_script(mock_terminal_service):
    """Test new_window() with paste script."""
    with patch(
        "automate_terminal.api._get_terminal_service",
        return_value=mock_terminal_service,
    ):
        result = api.new_window(
            "/path/to/project", paste_script="source venv/bin/activate"
        )

    assert result is True
    mock_terminal_service.new_window.assert_called_once()
    call_args = mock_terminal_service.new_window.call_args
    assert call_args.kwargs["paste_script"] == "source venv/bin/activate"


def test_switch_to_session_by_id(mock_terminal_service):
    """Test switch_to_session() with session ID."""
    with patch(
        "automate_terminal.api._get_terminal_service",
        return_value=mock_terminal_service,
    ):
        result = api.switch_to_session(session_id="session-123")

    assert result is True
    mock_terminal_service.switch_to_session.assert_called_once()
    call_args = mock_terminal_service.switch_to_session.call_args
    assert call_args.kwargs["session_id"] == "session-123"
    assert call_args.kwargs["working_directory"] is None


def test_switch_to_session_by_working_directory(mock_terminal_service):
    """Test switch_to_session() with working directory."""
    with patch(
        "automate_terminal.api._get_terminal_service",
        return_value=mock_terminal_service,
    ):
        result = api.switch_to_session(working_directory="/path/to/project")

    assert result is True
    mock_terminal_service.switch_to_session.assert_called_once()
    call_args = mock_terminal_service.switch_to_session.call_args
    assert call_args.kwargs["working_directory"] == Path("/path/to/project")
    assert call_args.kwargs["session_id"] is None


def test_switch_to_session_with_paste_script(mock_terminal_service):
    """Test switch_to_session() with paste script."""
    with patch(
        "automate_terminal.api._get_terminal_service",
        return_value=mock_terminal_service,
    ):
        result = api.switch_to_session(
            working_directory="/path/to/project", paste_script="git status"
        )

    assert result is True
    mock_terminal_service.switch_to_session.assert_called_once()
    call_args = mock_terminal_service.switch_to_session.call_args
    assert call_args.kwargs["paste_script"] == "git status"


def test_switch_to_session_with_subdirectory_ok(mock_terminal_service):
    """Test switch_to_session() with subdirectory_ok flag."""
    with patch(
        "automate_terminal.api._get_terminal_service",
        return_value=mock_terminal_service,
    ):
        result = api.switch_to_session(
            working_directory="/path/to/project", subdirectory_ok=True
        )

    assert result is True
    mock_terminal_service.switch_to_session.assert_called_once()
    call_args = mock_terminal_service.switch_to_session.call_args
    assert call_args.kwargs["subdirectory_ok"] is True


def test_list_sessions(mock_terminal_service):
    """Test list_sessions() delegates to TerminalService."""
    with patch(
        "automate_terminal.api._get_terminal_service",
        return_value=mock_terminal_service,
    ):
        result = api.list_sessions()

    assert len(result) == 1
    assert result[0]["session_id"] == "session1"
    assert result[0]["working_directory"] == "/path/to/dir"
    mock_terminal_service.list_sessions.assert_called_once()


def test_get_current_session_id(mock_terminal_service):
    """Test get_current_session_id() delegates to TerminalService."""
    with patch(
        "automate_terminal.api._get_terminal_service",
        return_value=mock_terminal_service,
    ):
        result = api.get_current_session_id()

    assert result == "session-123"
    mock_terminal_service.get_current_session_id.assert_called_once()


def test_get_current_session_id_returns_none(mock_terminal_service):
    """Test get_current_session_id() returns None when service returns None."""
    mock_terminal_service.get_current_session_id.return_value = None
    with patch(
        "automate_terminal.api._get_terminal_service",
        return_value=mock_terminal_service,
    ):
        result = api.get_current_session_id()

    assert result is None


def test_get_shell_name(mock_terminal_service):
    """Test get_shell_name() delegates to TerminalService."""
    with patch(
        "automate_terminal.api._get_terminal_service",
        return_value=mock_terminal_service,
    ):
        result = api.get_shell_name()

    assert result == "zsh"
    mock_terminal_service.get_shell_name.assert_called_once()


def test_get_shell_name_returns_none(mock_terminal_service):
    """Test get_shell_name() returns None when service returns None."""
    mock_terminal_service.get_shell_name.return_value = None
    with patch(
        "automate_terminal.api._get_terminal_service",
        return_value=mock_terminal_service,
    ):
        result = api.get_shell_name()

    assert result is None


def test_get_terminal_service_creates_services():
    """Test _get_terminal_service creates CommandService, AppleScriptService and TerminalService."""
    with (
        patch("automate_terminal.api.CommandService") as mock_command_cls,
        patch("automate_terminal.api.AppleScriptService") as mock_applescript_cls,
        patch("automate_terminal.api.TerminalService") as mock_terminal_cls,
    ):
        api._get_terminal_service(dry_run=True, debug=True)

    # Verify services were created with correct parameters
    mock_command_cls.assert_called_once_with(dry_run=True)
    mock_applescript_cls.assert_called_once_with(
        command_service=mock_command_cls.return_value
    )
    mock_terminal_cls.assert_called_once_with(
        applescript_service=mock_applescript_cls.return_value
    )


def test_api_functions_pass_debug_and_dry_run():
    """Test that all API functions accept and pass through debug and dry_run parameters."""
    with patch("automate_terminal.api._get_terminal_service") as mock_get:
        mock_service = MagicMock()
        mock_get.return_value = mock_service
        mock_service.get_terminal_name.return_value = "test"
        mock_service.get_capabilities.return_value = Capabilities(
            can_create_tabs=True,
            can_create_windows=True,
            can_list_sessions=True,
            can_switch_to_session=True,
            can_detect_session_id=True,
            can_detect_working_directory=True,
            can_paste_commands=True,
            can_run_in_active_session=True,
        )
        mock_service.get_shell_name.return_value = "zsh"
        mock_service.get_current_session_id.return_value = "session-123"

        # Test each function with debug=True, dry_run=True
        api.check(debug=True, dry_run=True)
        assert mock_get.call_args.kwargs == {"debug": True, "dry_run": True}

        api.new_tab("/tmp", debug=True, dry_run=True)
        assert mock_get.call_args.kwargs == {"debug": True, "dry_run": True}

        api.new_window("/tmp", debug=True, dry_run=True)
        assert mock_get.call_args.kwargs == {"debug": True, "dry_run": True}

        api.switch_to_session(session_id="test", debug=True, dry_run=True)
        assert mock_get.call_args.kwargs == {"debug": True, "dry_run": True}

        api.list_sessions(debug=True, dry_run=True)
        assert mock_get.call_args.kwargs == {"debug": True, "dry_run": True}

        api.get_current_session_id(debug=True, dry_run=True)
        assert mock_get.call_args.kwargs == {"debug": True, "dry_run": True}

        api.get_shell_name(debug=True, dry_run=True)
        assert mock_get.call_args.kwargs == {"debug": True, "dry_run": True}
