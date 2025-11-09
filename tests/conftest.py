"""Shared fixtures and fakes for tests."""

import argparse
from dataclasses import dataclass
from pathlib import Path

import pytest

from automate_terminal.models import Capabilities


class FakeAppleScriptService:
    def __init__(self, command_service=None, dry_run=False, is_macos=True):
        self.command_service = command_service or FakeCommandService(dry_run=dry_run)
        self.dry_run = dry_run
        self.is_macos = is_macos
        self.executed_scripts = []
        self.result_to_return = None

    def execute(self, script: str) -> bool:
        self.executed_scripts.append(("execute", script))
        return True

    def execute_with_result(self, script: str) -> str | None:
        self.executed_scripts.append(("execute_with_result", script))
        return self.result_to_return

    def escape(self, val: Path | str) -> str:
        return str(val).replace("\\", "\\\\").replace('"', '\\"')


class FakeCommandService:
    """Fake command service for testing."""

    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.executed_commands = []
        self.return_value = True
        self.return_output = None

    def execute_r(
        self, cmd: list[str], timeout: int = 10, description: str | None = None
    ) -> bool:
        """Record read-only command execution, return configured value."""
        self.executed_commands.append(("execute_r", cmd, timeout, description))
        return self.return_value

    def execute_r_with_output(
        self, cmd: list[str], timeout: int = 10, description: str | None = None
    ) -> str | None:
        """Record read-only command execution with output, return configured output."""
        self.executed_commands.append(
            ("execute_r_with_output", cmd, timeout, description)
        )
        return self.return_output

    def execute_rw(
        self, cmd: list[str], timeout: int = 10, description: str | None = None
    ) -> bool:
        """Record read-write command execution, return configured value."""
        self.executed_commands.append(("execute_rw", cmd, timeout, description))
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
