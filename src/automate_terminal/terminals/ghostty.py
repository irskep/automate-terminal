"""Ghostty terminal implementation."""

import logging
import shlex
from pathlib import Path

from automate_terminal.models import Capabilities

from .base import BaseTerminal

logger = logging.getLogger(__name__)


class GhosttyMacTerminal(BaseTerminal):
    # Ghostty has no AppleScript support, so it's bare-bones

    @property
    def display_name(self) -> str:
        return "Ghostty"

    def detect(self, term_program: str | None, platform_name: str) -> bool:
        return platform_name == "Darwin" and term_program == "ghostty"

    def get_current_session_id(self) -> str | None:
        return None

    def supports_session_management(self) -> bool:
        return False

    def session_exists(self, session_id: str) -> bool:
        return False

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        return False

    def session_in_directory(self, session_id: str, directory: Path) -> bool:
        return False

    def open_new_tab(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        # Requires accessibility permissions to simulate Cmd+T
        logger.debug(f"Opening new Ghostty tab for {working_directory}")

        commands = [f"cd {shlex.quote(str(working_directory))}"]
        if session_init_script:
            commands.append(session_init_script)

        command_string = self.applescript.escape("; ".join(commands))

        applescript = f"""
        tell application "Ghostty"
            activate
            tell application "System Events"
                tell process "Ghostty"
                    keystroke "t" using command down
                    delay 0.3
                    keystroke "{self.applescript.escape(command_string)}"
                    key code 36 -- Return
                end tell
            end tell
        end tell
        """

        if self.applescript.execute(applescript):
            return True
        else:
            # System Events failed, fall back to window creation
            logger.warning(
                "Failed to create tab (missing accessibility permissions). "
                "To fix: Enable Terminal in "
                "System Settings -> Privacy & Security -> Accessibility"
            )
            return False

    def open_new_window(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        logger.debug(f"Opening new Ghostty window for {working_directory}")

        commands = [f"cd {shlex.quote(str(working_directory))}"]
        if session_init_script:
            commands.append(session_init_script)

        command_string = self.applescript.escape("; ".join(commands))

        applescript = f"""
        tell application "Ghostty"
            activate
            tell application "System Events"
                tell process "Ghostty"
                    keystroke "n" using command down
                    delay 0.3
                    keystroke "{self.applescript.escape(command_string)}"
                    key code 36 -- Return
                end tell
            end tell
        end tell
        """

        return self.applescript.execute(applescript)

    def get_capabilities(self) -> Capabilities:
        return Capabilities(
            can_create_tabs=True,
            can_create_windows=True,
            can_list_sessions=False,
            can_switch_to_session=False,
            can_detect_session_id=False,
            can_detect_working_directory=False,
            can_paste_commands=True,
            can_run_in_active_session=True,
        )

    def run_in_active_session(self, command: str) -> bool:
        logger.debug(f"Running command in active Ghostty session: {command}")

        applescript = f"""
        tell application "System Events"
            tell process "Ghostty"
                keystroke "{self.applescript.escape(command)}"
                key code 36
            end tell
        end tell
        """

        return self.applescript.execute(applescript)
