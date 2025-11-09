"""VSCode and Cursor terminal implementations."""

import logging
import os
import shutil
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from automate_terminal.utils import run_command

from .base import BaseTerminal

logger = logging.getLogger(__name__)

VSCodeVariant = Literal["vscode", "cursor"]


class VSCodeTerminal(BaseTerminal):
    """VSCode/Cursor terminal implementation.

    These editors have integrated terminals but limited automation capabilities.
    They can manage windows by workspace path but cannot automate terminal sessions.
    """

    def __init__(self, applescript_service, variant: VSCodeVariant = "vscode"):
        """Initialize VSCode terminal with specific variant.

        Args:
            applescript_service: Service for executing AppleScript
            variant: Either "vscode" or "cursor"
        """
        super().__init__(applescript_service)
        self.variant = variant

    @property
    def cli_command(self) -> str:
        """CLI command name."""
        return "code" if self.variant == "vscode" else "cursor"

    @property
    def app_names(self) -> list[str]:
        """Application process names for AppleScript detection on macOS."""
        if self.variant == "vscode":
            return ["Code", "Visual Studio Code"]
        else:
            return ["Cursor"]

    @property
    def display_name(self) -> str:
        """Human-readable name for logging and error messages."""
        return "VSCode" if self.variant == "vscode" else "Cursor"

    def detect(self, term_program: str | None, platform_name: str) -> bool:
        """Detect if this editor variant is the current terminal."""
        # Both VSCode and Cursor set TERM_PROGRAM=vscode
        if term_program != "vscode":
            return False

        # Cursor sets CURSOR_TRACE_ID, VSCode doesn't
        has_cursor_id = bool(os.getenv("CURSOR_TRACE_ID"))

        if self.variant == "vscode":
            return not has_cursor_id
        else:  # cursor
            return has_cursor_id

    def _is_cli_available(self) -> bool:
        """Check if the CLI command is available."""
        return shutil.which(self.cli_command) is not None

    def get_current_session_id(self) -> str | None:
        """Editors don't provide session IDs."""
        return None

    def supports_session_management(self) -> bool:
        """Can switch to windows on macOS only."""
        return self.applescript.is_macos

    def _path_to_file_url(self, path: Path) -> str:
        """Convert absolute path to file:// URL format."""
        path = path.resolve()
        return f"file://{quote(str(path), safe='/')}"

    def _find_window_with_path(self, workspace_path: Path) -> bool:
        """Find and activate editor window containing the target path (macOS only)."""
        if not self.applescript.is_macos:
            return False

        target_url = self._path_to_file_url(workspace_path)

        for app_name in self.app_names:
            applescript = f"""
            tell application "System Events"
                if not (exists process "{app_name}") then
                    return false
                end if

                tell process "{app_name}"
                    set targetURL to "{target_url}"
                    set foundWindow to missing value
                    set windowIndex to 0

                    repeat with w in windows
                        set windowIndex to windowIndex + 1
                        try
                            set docPath to value of attribute "AXDocument" of w
                            if docPath starts with targetURL or targetURL starts with docPath then
                                set foundWindow to windowIndex
                                exit repeat
                            end if
                        on error
                            -- window has no document attribute
                        end try
                    end repeat

                    if foundWindow is not missing value then
                        -- Activate the window
                        set frontmost to true
                        click window foundWindow
                        return true
                    else
                        return false
                    end if
                end tell
            end tell
            """

            result = self.applescript.execute_with_result(applescript)
            if result == "true":
                logger.debug(
                    f"Found and activated {self.display_name} window for {workspace_path}"
                )
                return True

        return False

    def session_exists(self, session_id: str) -> bool:
        """Check if a window exists with this workspace path (macOS only).

        For editors, session_id is the workspace path.
        """
        if not self.applescript.is_macos:
            return False

        try:
            workspace_path = Path(session_id)
            if not workspace_path.exists():
                return False

            target_url = self._path_to_file_url(workspace_path)

            for app_name in self.app_names:
                applescript = f"""
                tell application "System Events"
                    if not (exists process "{app_name}") then
                        return false
                    end if

                    tell process "{app_name}"
                        set targetURL to "{target_url}"

                        repeat with w in windows
                            try
                                set docPath to value of attribute "AXDocument" of w
                                if docPath starts with targetURL or targetURL starts with docPath then
                                    return true
                                end if
                            on error
                                -- window has no document attribute
                            end try
                        end repeat
                        return false
                    end tell
                end tell
                """

                result = self.applescript.execute_with_result(applescript)
                if result == "true":
                    return True

            return False

        except Exception as e:
            logger.debug(f"Error checking if session exists: {e}")
            return False

    def find_session_by_working_directory(
        self, target_path: str, subdirectory_ok: bool = False
    ) -> str | None:
        """Find a window with this workspace path (macOS only).

        Returns the workspace path as the session ID if found.
        """
        if self.session_exists(target_path):
            return target_path
        return None

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Switch to window with this workspace path (macOS only)."""
        if not self.applescript.is_macos:
            logger.debug(
                f"{self.display_name} session switching only supported on macOS"
            )
            return False

        if session_init_script:
            logger.warning(
                f"{self.display_name} cannot execute init scripts in integrated terminal"
            )

        try:
            workspace_path = Path(session_id)
            return self._find_window_with_path(workspace_path)
        except Exception as e:
            logger.error(f"Failed to switch to {self.display_name} window: {e}")
            return False

    def open_new_tab(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        """Editors don't support terminal tab creation via automation."""
        logger.error(
            f"{self.display_name} does not support creating terminal tabs programmatically"
        )
        return False

    def open_new_window(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new editor window via CLI."""
        logger.debug(f"Opening new {self.display_name} window for {working_directory}")

        if not self._is_cli_available():
            logger.error(
                f"{self.cli_command} CLI not found. Install it via "
                f"{self.display_name} Command Palette: 'Shell Command: Install {self.cli_command} command in PATH'"
            )
            return False

        if session_init_script:
            logger.warning(
                f"{self.display_name} cannot execute init scripts via CLI. "
                "The init script will not be executed."
            )

        try:
            cmd = [self.cli_command, "-n", str(working_directory)]
            result = run_command(
                cmd,
                timeout=10,
                description=f"Open {self.display_name} window",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open {self.display_name} window: {e}")
            return False

    def _can_create_tabs(self) -> bool:
        return False

    def _can_create_windows(self) -> bool:
        return True

    def _can_list_sessions(self) -> bool:
        return False

    def _can_switch_to_session(self) -> bool:
        return self.applescript.is_macos

    def _can_detect_session_id(self) -> bool:
        return False

    def _can_paste_commands(self) -> bool:
        return False
