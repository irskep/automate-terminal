"""Base terminal implementation."""

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from automate_terminal.models import Capabilities

if TYPE_CHECKING:
    from automate_terminal.applescript_service import AppleScriptService
    from automate_terminal.command_service import CommandService

logger = logging.getLogger(__name__)


class BaseTerminal(ABC):
    def __init__(
        self,
        applescript_service: "AppleScriptService",
        command_service: "CommandService",
    ):
        self.applescript = applescript_service
        self.command_service = command_service

    @property
    def display_name(self) -> str:
        pass

    @abstractmethod
    def detect(self, term_program: str | None, platform_name: str) -> bool:
        """Detect if this terminal is currently active.

        Args:
            term_program: Value of TERM_PROGRAM environment variable
            platform_name: Platform name (e.g., 'Darwin', 'Linux', 'Windows')

        Returns:
            True if this terminal is detected, False otherwise
        """
        pass

    @abstractmethod
    def get_current_session_id(self) -> str | None:
        """Get current session ID if supported."""
        pass

    @abstractmethod
    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Switch to existing session by session ID if supported."""
        pass

    def switch_to_session_by_working_directory(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        """Switch to existing session by working directory if supported.

        This is for terminals that can switch to sessions by working directory
        without needing a session ID (like Terminal.app).
        """
        return False

    @abstractmethod
    def open_new_tab(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        """Open new tab in current window."""
        pass

    @abstractmethod
    def open_new_window(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        """Open new window."""
        pass

    def supports_session_management(self) -> bool:
        """Whether this terminal supports session management."""
        return False

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists in the terminal."""
        return False

    def session_in_directory(self, session_id: str, directory: Path) -> bool:
        """Check if a session exists and is currently in the specified directory."""
        return False

    def list_sessions(self) -> list[dict[str, str]]:
        """List all sessions with their working directories."""
        return []

    def find_session_by_working_directory(
        self, target_path: str, subdirectory_ok: bool = False
    ) -> str | None:
        """Find a session ID that matches the given working directory.

        Args:
            target_path: The target directory path
            subdirectory_ok: If True, match sessions in subdirectories of target_path
        """
        return None

    def run_in_active_session(self, command: str) -> bool:
        """Run a command in the current active terminal session."""
        return False

    def get_shell_name(self) -> str | None:
        """Get the name of the current shell (e.g., 'zsh', 'bash', 'fish')."""
        shell_path = os.environ.get("SHELL", "")
        if shell_path:
            return os.path.basename(shell_path)
        return None

    @abstractmethod
    def get_capabilities(self) -> Capabilities:
        """Return capabilities this terminal supports."""
        pass
