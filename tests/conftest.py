"""Shared fixtures and fakes for tests."""

import argparse
from dataclasses import dataclass

import pytest

from automate_terminal.models import Capabilities


class FakeAppleScriptService:
    """Fake AppleScript service for testing."""

    def __init__(self, dry_run=False, is_macos=True):
        self.dry_run = dry_run
        self.is_macos = is_macos
        self.executed_scripts = []
        self.result_to_return = None

    def execute(self, script: str) -> bool:
        """Record script execution, return True."""
        self.executed_scripts.append(("execute", script))
        return True

    def execute_with_result(self, script: str) -> str | None:
        """Record script execution, return configured result."""
        self.executed_scripts.append(("execute_with_result", script))
        return self.result_to_return


class FakeCommandService:
    """Fake command service for testing."""

    def __init__(self):
        self.executed_commands = []
        self.return_value = True

    def execute(
        self, cmd: list[str], timeout: int = 10, description: str | None = None
    ) -> bool:
        """Record command execution, return configured value."""
        self.executed_commands.append((cmd, timeout, description))
        return self.return_value


@dataclass
class FakeTerminal:
    """Fake terminal for testing TerminalService."""

    name: str
    capabilities: Capabilities
    should_detect: bool = True

    @property
    def display_name(self) -> str:
        return self.name

    def detect(self, term_program: str | None, platform_name: str) -> bool:
        return self.should_detect

    def get_current_session_id(self) -> str | None:
        return "fake-session-id"

    def get_shell_name(self) -> str | None:
        return "zsh"

    def get_capabilities(self) -> Capabilities:
        return self.capabilities

    def session_exists(self, session_id: str) -> bool:
        return True

    def switch_to_session(
        self, session_id: str, paste_script: str | None = None
    ) -> bool:
        return True

    def open_new_tab(self, working_directory, paste_script: str | None = None) -> bool:
        return True

    def open_new_window(
        self, working_directory, paste_script: str | None = None
    ) -> bool:
        return True

    def list_sessions(self) -> list[dict[str, str]]:
        return [{"session_id": "session1", "working_directory": "/home/user"}]

    def find_session_by_working_directory(
        self, path: str, subdirectory_ok: bool = False
    ) -> str | None:
        return "session1"


@pytest.fixture
def fake_applescript():
    """Provide a fake AppleScript service."""
    return FakeAppleScriptService()


@pytest.fixture
def fake_command():
    """Provide a fake command service."""
    return FakeCommandService()


@pytest.fixture
def mock_args():
    """Factory for creating mock argument namespaces."""

    def _make_args(**kwargs):
        defaults = {
            "output": "text",
            "debug": False,
            "dry_run": False,
            "paste_and_run": None,
            "paste_and_run_bash": None,
            "paste_and_run_zsh": None,
            "paste_and_run_fish": None,
            "paste_and_run_powershell": None,
            "paste_and_run_nushell": None,
            "subdirectory_ok": False,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    return _make_args
