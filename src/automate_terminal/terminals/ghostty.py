"""Ghostty terminal implementation."""

import logging
import shlex
from pathlib import Path

from .base import BaseTerminal

logger = logging.getLogger(__name__)


class GhosttyMacTerminal(BaseTerminal):
    """Ghostty implementation. Ghostty has no AppleScript support, so it's bare-bones."""

    @property
    def display_name(self) -> str:
        return "Ghostty"

    def detect(self, term_program: str | None, platform_name: str) -> bool:
        """Detect if Ghostty is the current terminal."""
        return platform_name == "Darwin" and term_program == "ghostty"

    def get_current_session_id(self) -> str | None:
        """Ghostty doesn't support session IDs."""
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
        # Ghostty requires System Events (accessibility permissions) to create
        # actual tabs via Cmd+T keyboard simulation.
        logger.debug(f"Opening new Ghostty tab for {working_directory}")

        commands = [f"cd {shlex.quote(str(working_directory))}"]
        if session_init_script:
            commands.append(session_init_script)

        command_string = self.applescript.escape_string("; ".join(commands))

        applescript = f"""
        tell application "Ghostty"
            activate
            tell application "System Events"
                tell process "Ghostty"
                    keystroke "t" using command down
                    delay 0.3
                    keystroke "{self.applescript.escape_string(command_string)}"
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

        command_string = self.applescript.escape_string("; ".join(commands))

        applescript = f"""
        tell application "Ghostty"
            activate
            tell application "System Events"
                tell process "Ghostty"
                    keystroke "n" using command down
                    delay 0.3
                    keystroke "{self.applescript.escape_string(command_string)}"
                    key code 36 -- Return
                end tell
            end tell
        end tell
        """

        return self.applescript.execute(applescript)

    def _can_create_tabs(self) -> bool:
        return True

    def _can_create_windows(self) -> bool:
        return True

    def _can_paste_commands(self) -> bool:
        return True
