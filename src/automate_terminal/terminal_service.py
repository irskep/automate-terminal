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
from automate_terminal.terminals.guake import GuakeTerminal
from automate_terminal.terminals.iterm2 import ITerm2Terminal
from automate_terminal.terminals.kitty import KittyTerminal
from automate_terminal.terminals.tmux import TmuxTerminal
from automate_terminal.terminals.vscode import VSCodeTerminal
from automate_terminal.terminals.wezterm import WeztermTerminal

logger = logging.getLogger(__name__)


EMPTY_CAPABILITIES = Capabilities(
    can_create_tabs=False,
    can_create_windows=False,
    can_list_sessions=False,
    can_switch_to_session=False,
    can_detect_session_id=False,
    can_detect_working_directory=True,
    can_paste_commands=False,
    can_run_in_active_session=False,
)


def create_terminal_implementation(
    platform_name: str,
    term_program: str | None,
    applescript_service: AppleScriptService,
) -> BaseTerminal | None:
    # ApplescriptService "owns" dry_run config because it's not terrible enough
    # to refactor yet
    command_service = CommandService(dry_run=applescript_service.dry_run)

    # This is a private API used for testing various terminal emulators without
    # having to constantly switch terminal emulators
    override = os.getenv("AUTOMATE_TERMINAL_OVERRIDE")
    if override:
        logger.debug(f"Using AUTOMATE_TERMINAL_OVERRIDE={override}")
        override_map = {
            "iterm2": ITerm2Terminal(applescript_service, command_service),
            "terminal": TerminalAppTerminal(applescript_service, command_service),
            "terminal.app": TerminalAppTerminal(applescript_service, command_service),
            "ghostty": GhosttyMacTerminal(applescript_service, command_service),
            "tmux": TmuxTerminal(applescript_service, command_service),
            "wezterm": WeztermTerminal(applescript_service, command_service),
            "kitty": KittyTerminal(applescript_service, command_service),
            "guake": GuakeTerminal(applescript_service, command_service),
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

    # Terminals are tried in order.
    terminals = [
        # tmux first since it can be running inside any other terminal
        TmuxTerminal(applescript_service, command_service),
        # Guake sets GUAKE_TAB_UUID which is very specific
        GuakeTerminal(applescript_service, command_service),
        WeztermTerminal(applescript_service, command_service),
        KittyTerminal(applescript_service, command_service),
        ITerm2Terminal(applescript_service, command_service),
        TerminalAppTerminal(applescript_service, command_service),
        GhosttyMacTerminal(applescript_service, command_service),
        # Cursor before VSCode since it's more specific (both use TERM_PROGRAM=vscode)
        VSCodeTerminal(applescript_service, command_service, variant="cursor"),
        VSCodeTerminal(applescript_service, command_service, variant="vscode"),
    ]

    # Try each terminal implementation's detect() method
    for terminal in terminals:
        if terminal.detect(term_program, platform_name):
            logger.debug(f"Detected terminal: {terminal.display_name}")
            return terminal

    logger.warning(
        f"Unsupported terminal: {term_program or 'unknown'} on platform {platform_name}"
    )
    return None


class TerminalNotFoundError(Exception):
    pass


class TerminalService:
    def __init__(self, applescript_service: AppleScriptService):
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
        return self.terminal.display_name

    def get_current_session_id(self) -> str | None:
        return self.terminal.get_current_session_id()

    def get_shell_name(self) -> str | None:
        return self.terminal.get_shell_name()

    def get_capabilities(self) -> Capabilities:
        return self.terminal.get_capabilities()

    def switch_to_session_by_id(
        self, session_id: str, paste_script: str | None = None
    ) -> bool:
        if not self.terminal.session_exists(session_id):
            return False

        return self.terminal.switch_to_session(session_id, paste_script)

    def find_session_by_directory(
        self, working_directory: Path, subdirectory_ok: bool = False
    ) -> str | None:
        return self.terminal.find_session_by_working_directory(
            str(working_directory), subdirectory_ok=subdirectory_ok
        )

    def switch_to_session_by_directory(
        self,
        working_directory: Path,
        paste_script: str | None = None,
        subdirectory_ok: bool = False,
    ) -> bool:
        # First try to find a session ID by working directory
        session_id = self.terminal.find_session_by_working_directory(
            str(working_directory), subdirectory_ok=subdirectory_ok
        )

        if session_id:
            # If we found a session ID, use it
            return self.terminal.switch_to_session(session_id, paste_script)

        # Otherwise try switching directly by working directory
        # (for terminals like Terminal.app that don't have session IDs)
        return self.terminal.switch_to_session_by_working_directory(
            working_directory, paste_script
        )

    def switch_to_session(
        self,
        session_id: str | None = None,
        working_directory: Path | None = None,
        paste_script: str | None = None,
        subdirectory_ok: bool = False,
    ) -> bool:
        if session_id and self.terminal.session_exists(session_id):
            return self.terminal.switch_to_session(session_id, paste_script)

        if working_directory:
            return self.switch_to_session_by_directory(
                working_directory, paste_script, subdirectory_ok=subdirectory_ok
            )

        return False

    def new_tab(self, working_directory: Path, paste_script: str | None = None) -> bool:
        if not self.terminal.get_capabilities().can_create_tabs:
            raise RuntimeError("Terminal does not support tab creation")

        return self.terminal.open_new_tab(working_directory, paste_script)

    def new_window(
        self, working_directory: Path, paste_script: str | None = None
    ) -> bool:
        if not self.terminal.get_capabilities().can_create_windows:
            raise RuntimeError("Terminal does not support window creation")

        return self.terminal.open_new_window(working_directory, paste_script)

    def list_sessions(self) -> list[dict[str, str]]:
        if not self.terminal.get_capabilities().can_list_sessions:
            raise RuntimeError("Terminal does not support session listing")

        return self.terminal.list_sessions()

    def find_session(
        self, session_id: str | None = None, working_directory: Path | None = None
    ) -> dict[str, str] | None:
        if session_id and self.terminal.session_exists(session_id):
            return {
                "session_id": session_id,
                "working_directory": "unknown",  # We don't track this
            }

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

    def run_in_active_session(self, command: str) -> bool:
        if not self.terminal.get_capabilities().can_run_in_active_session:
            raise RuntimeError(
                "Terminal does not support running commands in active session"
            )

        return self.terminal.run_in_active_session(command)
