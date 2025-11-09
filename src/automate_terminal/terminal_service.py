"""Terminal management service."""

import logging
import os
import platform
from pathlib import Path

from automate_terminal.applescript_service import AppleScriptService
from automate_terminal.command_service import CommandService
from automate_terminal.models import Capabilities
from automate_terminal.terminals.apple import TerminalAppTerminal
from automate_terminal.terminals.base import BaseTerminal
from automate_terminal.terminals.ghostty import GhosttyMacTerminal
from automate_terminal.terminals.iterm2 import ITerm2Terminal
from automate_terminal.terminals.vscode import VSCodeTerminal

logger = logging.getLogger(__name__)


EMPTY_CAPABILITIES = Capabilities(
    can_create_tabs=False,
    can_create_windows=False,
    can_list_sessions=False,
    can_switch_to_session=False,
    can_detect_session_id=False,
    can_detect_working_directory=True,
    can_paste_commands=False,
)


def create_terminal_implementation(
    platform_name: str,
    term_program: str | None,
    applescript_service: AppleScriptService,
) -> BaseTerminal | None:
    """Create the appropriate terminal implementation."""
    command_service = CommandService()

    # Check for override environment variable
    override = os.getenv("AUTOMATE_TERMINAL_OVERRIDE")
    if override:
        logger.debug(f"Using AUTOMATE_TERMINAL_OVERRIDE={override}")
        override_map = {
            "iterm2": ITerm2Terminal(applescript_service),
            "terminal": TerminalAppTerminal(applescript_service),
            "terminal.app": TerminalAppTerminal(applescript_service),
            "ghostty": GhosttyMacTerminal(applescript_service),
            "vscode": VSCodeTerminal(
                applescript_service, command_service, variant="vscode"
            ),
            "cursor": VSCodeTerminal(
                applescript_service, command_service, variant="cursor"
            ),
        }
        terminal = override_map.get(override.lower())
        if terminal:
            logger.debug(f"Overridden terminal: {terminal.display_name}")
            return terminal
        else:
            logger.warning(f"Unknown AUTOMATE_TERMINAL_OVERRIDE value: {override}")

    # Ordered list of terminal implementations to try
    # Cursor before VSCode since it's more specific (both use TERM_PROGRAM=vscode)
    terminals = [
        ITerm2Terminal(applescript_service),
        TerminalAppTerminal(applescript_service),
        GhosttyMacTerminal(applescript_service),
        VSCodeTerminal(applescript_service, command_service, variant="cursor"),
        VSCodeTerminal(applescript_service, command_service, variant="vscode"),
    ]

    # Try each terminal implementation's detect method
    for terminal in terminals:
        if terminal.detect(term_program, platform_name):
            logger.debug(f"Detected terminal: {terminal.display_name}")
            return terminal

    # Unsupported terminal
    logger.warning(
        f"Unsupported terminal: {term_program or 'unknown'} on platform {platform_name}"
    )
    return None


class TerminalNotFoundError(Exception):
    pass


class TerminalService:
    """Handles terminal switching and session management."""

    def __init__(self, applescript_service: AppleScriptService):
        """Initialize terminal service.

        Args:
            applescript_service: Service for executing AppleScript
        """
        self.applescript_service = applescript_service
        self.terminal = create_terminal_implementation(
            platform.system(),
            os.getenv("TERM_PROGRAM"),
            self.applescript_service,
        )
        if self.terminal:
            logger.debug(
                f"Terminal service initialized with {type(self.terminal).__name__}"
            )
        else:
            logger.debug("No supported terminal detected")
            raise TerminalNotFoundError()

    def get_terminal_name(self) -> str:
        """Get the name of the current terminal."""
        return self.terminal.display_name

    def get_current_session_id(self) -> str | None:
        """Get the current terminal session ID."""
        return self.terminal.get_current_session_id()

    def get_shell_name(self) -> str | None:
        """Get the name of the current shell."""
        return self.terminal.get_shell_name()

    def get_capabilities(self) -> Capabilities:
        """Get capabilities of the current terminal."""
        return self.terminal.get_capabilities()

    def switch_to_session_by_id(
        self, session_id: str, paste_script: str | None = None
    ) -> bool:
        """Switch to a session by session ID."""
        if not self.terminal.session_exists(session_id):
            return False

        return self.terminal.switch_to_session(session_id, paste_script)

    def find_session_by_directory(
        self, working_directory: Path, subdirectory_ok: bool = False
    ) -> str | None:
        """Check if a session exists by working directory without switching to it."""
        return self.terminal.find_session_by_working_directory(
            str(working_directory), subdirectory_ok=subdirectory_ok
        )

    def switch_to_session_by_directory(
        self,
        working_directory: Path,
        paste_script: str | None = None,
        subdirectory_ok: bool = False,
    ) -> bool:
        """Switch to a session by working directory."""
        # Try to find a session in the target directory
        session_id = self.terminal.find_session_by_working_directory(
            str(working_directory), subdirectory_ok=subdirectory_ok
        )

        if not session_id:
            # For terminals that can switch without session detection,
            # try switching with the path directly
            if self.terminal._can_switch_without_session_detection():
                return self.terminal.switch_to_session(
                    str(working_directory), paste_script
                )
            return False

        return self.terminal.switch_to_session(session_id, paste_script)

    def switch_to_session(
        self,
        session_id: str | None = None,
        working_directory: Path | None = None,
        paste_script: str | None = None,
        subdirectory_ok: bool = False,
    ) -> bool:
        """Switch to session by ID or working directory (ID takes precedence)."""
        # Try session ID first
        if session_id:
            if self.terminal.session_exists(session_id):
                return self.terminal.switch_to_session(session_id, paste_script)

        # Fall back to working directory
        if working_directory:
            return self.switch_to_session_by_directory(
                working_directory, paste_script, subdirectory_ok=subdirectory_ok
            )

        return False

    def new_tab(self, working_directory: Path, paste_script: str | None = None) -> bool:
        """Create a new tab."""
        if not self.terminal.get_capabilities().can_create_tabs:
            raise RuntimeError("Terminal does not support tab creation")

        return self.terminal.open_new_tab(working_directory, paste_script)

    def new_window(
        self, working_directory: Path, paste_script: str | None = None
    ) -> bool:
        """Create a new window."""
        if not self.terminal.get_capabilities().can_create_windows:
            raise RuntimeError("Terminal does not support window creation")

        return self.terminal.open_new_window(working_directory, paste_script)

    def list_sessions(self) -> list[dict[str, str]]:
        """List all terminal sessions."""
        if not self.terminal.get_capabilities().can_list_sessions:
            raise RuntimeError("Terminal does not support session listing")

        return self.terminal.list_sessions()

    def find_session(
        self, session_id: str | None = None, working_directory: Path | None = None
    ) -> dict[str, str] | None:
        """Find a session by ID or working directory."""
        # Try session ID first
        if session_id and self.terminal.session_exists(session_id):
            return {
                "session_id": session_id,
                "working_directory": "unknown",  # We don't track this
            }

        # Try working directory
        if working_directory:
            found_session_id = self.terminal.find_session_by_working_directory(
                str(working_directory)
            )
            if found_session_id:
                return {
                    "session_id": found_session_id,
                    "working_directory": str(working_directory),
                }

        return None
