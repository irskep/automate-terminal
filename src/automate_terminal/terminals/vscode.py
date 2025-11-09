"""VSCode and Cursor terminal implementations."""

import logging
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from automate_terminal.models import Capabilities

from .base import BaseTerminal

if TYPE_CHECKING:
    from automate_terminal.applescript_service import AppleScriptService
    from automate_terminal.command_service import CommandService

logger = logging.getLogger(__name__)

VSCodeVariant = Literal["vscode", "cursor"]


class VSCodeTerminal(BaseTerminal):
    # Uses CLI commands (code/cursor) to open or switch to workspace windows.
    # The CLI automatically switches to existing windows or opens new ones.

    def __init__(
        self,
        applescript_service: "AppleScriptService",
        command_service: "CommandService",
        variant: VSCodeVariant = "vscode",
    ):
        super().__init__(applescript_service, command_service)
        self.variant = variant

    @property
    def cli_command(self) -> str:
        return "code" if self.variant == "vscode" else "cursor"

    @property
    def app_names(self) -> list[str]:
        if self.variant == "vscode":
            return ["Code", "Visual Studio Code"]
        else:
            return ["Cursor"]

    @property
    def display_name(self) -> str:
        return "VSCode" if self.variant == "vscode" else "Cursor"

    def detect(self, term_program: str | None, platform_name: str) -> bool:
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
        return shutil.which(self.cli_command) is not None

    def get_current_session_id(self) -> str | None:
        return None

    def supports_session_management(self) -> bool:
        return True

    def _run_cli(self, working_directory: Path) -> bool:
        if not self._is_cli_available():
            logger.error(
                f"{self.cli_command} CLI not found. Install it via "
                f"{self.display_name} Command Palette: 'Shell Command: Install {self.cli_command} command in PATH'"
            )
            return False

        # Without -n flag, CLI switches to existing window or opens new one
        cmd = [self.cli_command, str(working_directory)]
        return self.command_service.execute_rw(
            cmd,
            timeout=10,
            description=f"Open/switch {self.display_name} window",
        )

    def list_sessions(self) -> list[dict[str, str]]:
        return []

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        return False

    def switch_to_session_by_working_directory(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        if session_init_script:
            logger.warning(
                f"{self.display_name} cannot execute init scripts in integrated terminal"
            )

        try:
            return self._run_cli(working_directory)
        except Exception as e:
            logger.error(f"Failed to switch to {self.display_name} window: {e}")
            return False

    def open_new_tab(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        logger.error(
            f"{self.display_name} does not support creating terminal tabs programmatically"
        )
        return False

    def open_new_window(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        if session_init_script:
            logger.warning(f"{self.display_name} cannot execute init scripts via CLI")

        return self._run_cli(working_directory)

    def get_capabilities(self) -> Capabilities:
        return Capabilities(
            can_create_tabs=False,
            can_create_windows=True,
            can_list_sessions=False,
            can_switch_to_session=True,
            can_detect_session_id=False,
            can_detect_working_directory=False,
            can_paste_commands=False,
            can_run_in_active_session=False,
        )
