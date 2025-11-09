"""Base terminal implementation."""

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from automate_terminal.models import Capabilities

if TYPE_CHECKING:
    from automate_terminal.applescript_service import AppleScriptService

logger = logging.getLogger(__name__)


class BaseTerminal(ABC):
    """Base class for terminal implementations."""

    def __init__(self, applescript_service: "AppleScriptService"):
        """Initialize terminal implementation.

        Args:
            applescript_service: Service for executing AppleScript
        """
        self.applescript = applescript_service

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
        """Switch to existing session if supported."""
        pass

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

    def get_shell_name(self) -> str | None:
        """Get the name of the current shell (e.g., 'zsh', 'bash', 'fish')."""
        shell_path = os.environ.get("SHELL", "")
        if shell_path:
            return os.path.basename(shell_path)
        return None

    def get_capabilities(self) -> Capabilities:
        """Return capabilities this terminal supports."""
        return Capabilities(
            can_create_tabs=self._can_create_tabs(),
            can_create_windows=self._can_create_windows(),
            can_list_sessions=self._can_list_sessions(),
            can_switch_to_session=self._can_switch_to_session(),
            can_detect_session_id=self._can_detect_session_id(),
            can_detect_working_directory=self._can_detect_working_directory(),
            can_paste_commands=self._can_paste_commands(),
        )

    def _can_create_tabs(self) -> bool:
        """Override in subclass to indicate tab creation support."""
        return False

    def _can_create_windows(self) -> bool:
        """Override in subclass to indicate window creation support."""
        return False

    def _can_list_sessions(self) -> bool:
        """Override in subclass to indicate session listing support."""
        return False

    def _can_switch_to_session(self) -> bool:
        """Override in subclass to indicate session switching support."""
        return False

    def _can_detect_session_id(self) -> bool:
        """Override in subclass to indicate session ID detection support."""
        return False

    def _can_detect_working_directory(self) -> bool:
        """Override in subclass to indicate working directory detection support.

        This means: can determine which sessions/tabs/windows are in which directories.
        Not just "can get current working directory from environment".
        """
        return False

    def _can_paste_commands(self) -> bool:
        """Override in subclass to indicate command pasting support."""
        return False

    def _can_switch_without_session_detection(self) -> bool:
        """Whether switch_to_session can work without finding session first.

        True for terminals like VSCode where switch_to_session(path) works
        even if find_session_by_working_directory returns None.

        Default: False (requires session detection before switching)
        """
        return False
