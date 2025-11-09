"""Tests for TerminalService."""

from unittest.mock import patch

import pytest
from conftest import FakeTerminal

from automate_terminal.models import Capabilities
from automate_terminal.terminal_service import (
    TerminalNotFoundError,
    TerminalService,
    create_terminal_implementation,
)


def test_create_terminal_implementation_finds_matching_terminal(fake_applescript):
    """Test that create_terminal_implementation returns first matching terminal."""
    terminal = create_terminal_implementation("Darwin", "iTerm.app", fake_applescript)
    assert terminal is not None
    assert terminal.display_name == "iTerm2"


def test_create_terminal_implementation_returns_none_unsupported(fake_applescript):
    """Test that unsupported terminal returns None."""
    terminal = create_terminal_implementation("Darwin", "unsupported", fake_applescript)
    assert terminal is None


def test_create_terminal_implementation_returns_none_non_macos(fake_applescript):
    """Test that non-macOS platform returns None."""
    terminal = create_terminal_implementation("Linux", "iTerm.app", fake_applescript)
    assert terminal is None


def test_terminal_service_raises_not_found_error(fake_applescript):
    """Test TerminalService raises TerminalNotFoundError when no terminal found."""
    with patch(
        "automate_terminal.terminal_service.create_terminal_implementation",
        return_value=None,
    ):
        with pytest.raises(TerminalNotFoundError):
            TerminalService(fake_applescript)


def test_terminal_service_delegates_to_terminal(fake_applescript):
    """Test TerminalService delegates methods to underlying terminal."""
    fake_terminal = FakeTerminal(
        name="FakeTerminal",
        capabilities=Capabilities(
            can_create_tabs=True,
            can_create_windows=True,
            can_list_sessions=True,
            can_switch_to_session=True,
            can_detect_session_id=True,
            can_detect_working_directory=True,
            can_paste_commands=True,
            can_run_in_active_session=True,
        ),
    )

    with patch(
        "automate_terminal.terminal_service.create_terminal_implementation",
        return_value=fake_terminal,
    ):
        service = TerminalService(fake_applescript)
        assert service.get_terminal_name() == "FakeTerminal"
        assert service.get_current_session_id() == "fake-session-id"
        assert service.get_shell_name() == "zsh"


def test_terminal_service_new_tab_checks_capability(fake_applescript):
    """Test new_tab raises RuntimeError when capability missing."""
    fake_terminal = FakeTerminal(
        name="NoTabTerminal",
        capabilities=Capabilities(
            can_create_tabs=False,
            can_create_windows=False,
            can_list_sessions=False,
            can_switch_to_session=False,
            can_detect_session_id=False,
            can_detect_working_directory=True,
            can_paste_commands=False,
            can_run_in_active_session=False,
        ),
    )

    with patch(
        "automate_terminal.terminal_service.create_terminal_implementation",
        return_value=fake_terminal,
    ):
        service = TerminalService(fake_applescript)
        with pytest.raises(RuntimeError, match="does not support tab creation"):
            service.new_tab("/tmp")


def test_terminal_service_new_window_checks_capability(fake_applescript):
    """Test new_window raises RuntimeError when capability missing."""
    fake_terminal = FakeTerminal(
        name="NoWindowTerminal",
        capabilities=Capabilities(
            can_create_tabs=False,
            can_create_windows=False,
            can_list_sessions=False,
            can_switch_to_session=False,
            can_detect_session_id=False,
            can_detect_working_directory=True,
            can_paste_commands=False,
            can_run_in_active_session=False,
        ),
    )

    with patch(
        "automate_terminal.terminal_service.create_terminal_implementation",
        return_value=fake_terminal,
    ):
        service = TerminalService(fake_applescript)
        with pytest.raises(RuntimeError, match="does not support window creation"):
            service.new_window("/tmp")


def test_create_terminal_implementation_respects_override(
    fake_applescript, monkeypatch
):
    """Test that AUTOMATE_TERMINAL_OVERRIDE env var forces specific terminal."""
    monkeypatch.setenv("AUTOMATE_TERMINAL_OVERRIDE", "iterm2")

    # Even though we pass vscode as TERM_PROGRAM, should get iTerm2
    terminal = create_terminal_implementation("Darwin", "vscode", fake_applescript)
    assert terminal is not None
    assert terminal.display_name == "iTerm2"


def test_create_terminal_implementation_override_case_insensitive(
    fake_applescript, monkeypatch
):
    """Test that override is case insensitive."""
    monkeypatch.setenv("AUTOMATE_TERMINAL_OVERRIDE", "TERMINAL")

    terminal = create_terminal_implementation("Darwin", "iTerm.app", fake_applescript)
    assert terminal is not None
    assert terminal.display_name == "Apple Terminal.app"


def test_create_terminal_implementation_override_unknown_value(
    fake_applescript, monkeypatch
):
    """Test that unknown override value falls back to normal detection."""
    monkeypatch.setenv("AUTOMATE_TERMINAL_OVERRIDE", "unknown_terminal")

    # Should fall back to normal detection
    terminal = create_terminal_implementation("Darwin", "iTerm.app", fake_applescript)
    assert terminal is not None
    assert terminal.display_name == "iTerm2"
