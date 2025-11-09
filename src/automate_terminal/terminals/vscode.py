"""VSCode and Cursor terminal implementations."""

import logging
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from .base import BaseTerminal

if TYPE_CHECKING:
    from automate_terminal.applescript_service import AppleScriptService
    from automate_terminal.command_service import CommandService

logger = logging.getLogger(__name__)

VSCodeVariant = Literal["vscode", "cursor"]


class VSCodeTerminal(BaseTerminal):
    """VSCode/Cursor terminal implementation.

    Uses CLI commands (code/cursor) to open or switch to workspace windows.
    The CLI automatically switches to existing windows or opens new ones.
    Can list open windows via AppleScript on macOS.
    """

    def __init__(
        self,
        applescript_service: "AppleScriptService",
        command_service: "CommandService",
        variant: VSCodeVariant = "vscode",
    ):
        """Initialize VSCode terminal with specific variant.

        Args:
            applescript_service: Service for executing AppleScript
            command_service: Service for executing shell commands
            variant: Either "vscode" or "cursor"
        """
        super().__init__(applescript_service)
        self.command_service = command_service
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
        """Can switch to windows via CLI."""
        return True

    def _run_cli(self, working_directory: Path) -> bool:
        """Run the editor CLI to open or switch to a workspace."""
        if not self._is_cli_available():
            logger.error(
                f"{self.cli_command} CLI not found. Install it via "
                f"{self.display_name} Command Palette: 'Shell Command: Install {self.cli_command} command in PATH'"
            )
            return False

        # Without -n flag, CLI switches to existing window or opens new one
        cmd = [self.cli_command, str(working_directory)]
        return self.command_service.execute(
            cmd,
            timeout=10,
            description=f"Open/switch {self.display_name} window",
        )

    def list_sessions(self) -> list[dict[str, str]]:
        """VSCode doesn't expose workspace paths via AppleScript."""
        return []

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Switch to window (CLI switches to existing or opens new)."""
        if session_init_script:
            logger.warning(
                f"{self.display_name} cannot execute init scripts in integrated terminal"
            )

        try:
            workspace_path = Path(session_id)
            return self._run_cli(workspace_path)
        except Exception as e:
            logger.error(f"Failed to switch to {self.display_name} window: {e}")
            return False

    def open_new_tab(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        """Editors don't support terminal tab creation."""
        logger.error(
            f"{self.display_name} does not support creating terminal tabs programmatically"
        )
        return False

    def open_new_window(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        """Open window (CLI switches to existing or opens new)."""
        if session_init_script:
            logger.warning(f"{self.display_name} cannot execute init scripts via CLI")

        return self._run_cli(working_directory)

    def _can_create_tabs(self) -> bool:
        return False

    def _can_create_windows(self) -> bool:
        return True

    def _can_list_sessions(self) -> bool:
        return False

    def _can_switch_to_session(self) -> bool:
        return True

    def _can_detect_session_id(self) -> bool:
        return False

    def _can_paste_commands(self) -> bool:
        return False

    def _can_switch_without_session_detection(self) -> bool:
        return True
