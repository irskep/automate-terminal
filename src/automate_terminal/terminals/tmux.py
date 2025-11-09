"""Tmux terminal implementation."""

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from automate_terminal.utils import run_command_r, run_command_rw

from .base import BaseTerminal

if TYPE_CHECKING:
    from automate_terminal.applescript_service import AppleScriptService
    from automate_terminal.command_service import CommandService

logger = logging.getLogger(__name__)


class TmuxTerminal(BaseTerminal):
    """Tmux terminal multiplexer implementation."""

    def __init__(
        self,
        applescript_service: "AppleScriptService",
        command_service: "CommandService",
    ):
        """Initialize tmux terminal.

        Args:
            applescript_service: Service for executing AppleScript (not used by tmux)
            command_service: Service for executing shell commands
        """
        super().__init__(applescript_service)
        self.command_service = command_service

    @property
    def display_name(self) -> str:
        return "tmux"

    def detect(self, term_program: str | None, platform_name: str) -> bool:
        """Detect if we're running inside tmux.

        Args:
            term_program: Value of TERM_PROGRAM environment variable (unused for tmux)
            platform_name: Platform name (tmux works on all platforms)

        Returns:
            True if running inside tmux (TMUX env var is set)
        """
        return os.getenv("TMUX") is not None

    def get_current_session_id(self) -> str | None:
        """Get current tmux pane ID.

        Returns:
            Current pane ID (e.g., '%0', '%1') or None if not available
        """
        pane_id = os.getenv("TMUX_PANE")
        logger.debug(f"Current tmux pane ID: {pane_id}")
        return pane_id

    def supports_session_management(self) -> bool:
        """Tmux supports comprehensive session management."""
        return True

    def session_exists(self, session_id: str) -> bool:
        """Check if a tmux pane exists.

        Args:
            session_id: Pane ID (e.g., '%0')

        Returns:
            True if pane exists, False otherwise
        """
        if not session_id:
            return False

        logger.debug(f"Checking if tmux pane exists: {session_id}")

        # Use tmux list-panes to check if pane exists
        try:
            result = run_command_r(
                ["tmux", "list-panes", "-a", "-F", "#{pane_id}"],
                description="List all tmux panes",
            )
            if result.returncode == 0 and result.stdout:
                pane_ids = [line.strip() for line in result.stdout.strip().split("\n")]
                return session_id in pane_ids
        except Exception as e:
            logger.error(f"Failed to check if pane exists: {e}")

        return False

    def session_in_directory(self, session_id: str, directory: Path) -> bool:
        """Check if tmux pane exists and is in the specified directory.

        Args:
            session_id: Pane ID (e.g., '%0')
            directory: Target directory path

        Returns:
            True if pane exists and is in directory, False otherwise
        """
        if not session_id:
            return False

        logger.debug(f"Checking if pane {session_id} is in directory {directory}")

        try:
            result = run_command_r(
                [
                    "tmux",
                    "display-message",
                    "-p",
                    "-t",
                    session_id,
                    "-F",
                    "#{pane_current_path}",
                ],
                description=f"Get working directory for pane {session_id}",
            )
            if result.returncode == 0 and result.stdout:
                pane_path = result.stdout.strip()
                return pane_path == str(directory)
        except Exception as e:
            logger.error(f"Failed to check pane directory: {e}")

        return False

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Switch to an existing tmux pane.

        Args:
            session_id: Pane ID to switch to (e.g., '%0')
            session_init_script: Optional script to run after switching

        Returns:
            True if switch succeeded, False otherwise
        """
        logger.debug(f"Switching to tmux pane: {session_id}")

        try:
            # First, get the window that contains this pane
            window_result = run_command_r(
                [
                    "tmux",
                    "display-message",
                    "-p",
                    "-t",
                    session_id,
                    "-F",
                    "#{window_id}",
                ],
                description=f"Get window for pane {session_id}",
            )

            if window_result.returncode != 0:
                logger.error(f"Failed to get window for pane {session_id}")
                return False

            window_id = window_result.stdout.strip()
            logger.debug(f"Pane {session_id} is in window {window_id}")

            # Switch to the window containing the target pane
            select_window_result = run_command_rw(
                ["tmux", "select-window", "-t", window_id],
                description=f"Switch to window {window_id}",
                dry_run=self.command_service.dry_run,
            )

            if select_window_result.returncode != 0:
                logger.error(f"Failed to switch to window {window_id}")
                return False

            # Then switch to the specific pane within that window
            result = run_command_rw(
                ["tmux", "select-pane", "-t", session_id],
                description=f"Switch to pane {session_id}",
                dry_run=self.command_service.dry_run,
            )

            if result.returncode != 0:
                return False

            # If there's a script to run, send it to the pane
            if session_init_script:
                send_result = run_command_rw(
                    [
                        "tmux",
                        "send-keys",
                        "-t",
                        session_id,
                        session_init_script,
                        "Enter",
                    ],
                    description=f"Send script to pane {session_id}",
                    dry_run=self.command_service.dry_run,
                )
                return send_result.returncode == 0

            return True

        except Exception as e:
            logger.error(f"Failed to switch to pane: {e}")
            return False

    def open_new_tab(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new tmux window (equivalent to a tab).

        Args:
            working_directory: Directory to start in
            session_init_script: Optional script to run in new window

        Returns:
            True if window creation succeeded, False otherwise
        """
        logger.debug(f"Opening new tmux window for {working_directory}")

        try:
            # Create new window with specified working directory
            cmd = ["tmux", "new-window", "-c", str(working_directory)]

            # If there's a script to run, add it to the command
            if session_init_script:
                cmd.append(session_init_script)

            result = run_command_rw(
                cmd,
                description=f"Create new tmux window in {working_directory}",
                dry_run=self.command_service.dry_run,
            )

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to create new window: {e}")
            return False

    def open_new_window(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new tmux session (equivalent to a window).

        For tmux, we create a detached session which is like opening a new window.

        Args:
            working_directory: Directory to start in
            session_init_script: Optional script to run in new session

        Returns:
            True if session creation succeeded, False otherwise
        """
        logger.debug(f"Opening new tmux session for {working_directory}")

        try:
            # Create new detached session with specified working directory
            cmd = ["tmux", "new-session", "-d", "-c", str(working_directory)]

            result = run_command_rw(
                cmd,
                description=f"Create new tmux session in {working_directory}",
                dry_run=self.command_service.dry_run,
            )

            if result.returncode != 0:
                return False

            # If there's a script to run, we need to find the new session and send keys
            if session_init_script:
                # Get the most recently created session
                session_result = run_command_r(
                    ["tmux", "display-message", "-p", "-t", "#{session_id}"],
                    description="Get newest session ID",
                )
                if session_result.returncode == 0 and session_result.stdout:
                    session_id = session_result.stdout.strip()
                    run_command_rw(
                        [
                            "tmux",
                            "send-keys",
                            "-t",
                            session_id,
                            session_init_script,
                            "Enter",
                        ],
                        description=f"Send script to session {session_id}",
                        dry_run=self.command_service.dry_run,
                    )

            return True

        except Exception as e:
            logger.error(f"Failed to create new session: {e}")
            return False

    def list_sessions(self) -> list[dict[str, str]]:
        """List all tmux panes with their working directories.

        Returns:
            List of dicts with 'session_id' and 'working_directory' keys
        """
        logger.debug("Listing all tmux panes")

        try:
            result = run_command_r(
                ["tmux", "list-panes", "-a", "-F", "#{pane_id}|#{pane_current_path}"],
                description="List all tmux panes with working directories",
            )

            if result.returncode != 0 or not result.stdout:
                return []

            sessions = []
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line and "|" in line:
                    pane_id, path = line.split("|", 1)
                    sessions.append(
                        {
                            "session_id": pane_id.strip(),
                            "working_directory": path.strip(),
                        }
                    )

            logger.debug(f"Found {len(sessions)} tmux panes")
            return sessions

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    def find_session_by_working_directory(
        self, target_path: str, subdirectory_ok: bool = False
    ) -> str | None:
        """Find a tmux pane ID that matches the given working directory.

        Args:
            target_path: Target directory path
            subdirectory_ok: If True, match panes in subdirectories of target_path

        Returns:
            Pane ID if found, None otherwise
        """
        sessions = self.list_sessions()
        target_path = str(Path(target_path).resolve())  # Normalize path

        # First try exact match
        for session in sessions:
            session_path = str(Path(session["working_directory"]).resolve())
            if session_path == target_path:
                return session["session_id"]

        # Try subdirectory match if requested
        if subdirectory_ok:
            for session in sessions:
                session_path = str(Path(session["working_directory"]).resolve())
                if session_path.startswith(target_path + "/"):
                    return session["session_id"]

        return None

    def _can_create_tabs(self) -> bool:
        """Tmux can create windows (equivalent to tabs)."""
        return True

    def _can_create_windows(self) -> bool:
        """Tmux can create sessions (equivalent to windows)."""
        return True

    def _can_list_sessions(self) -> bool:
        """Tmux can list all panes."""
        return True

    def _can_switch_to_session(self) -> bool:
        """Tmux can switch to panes."""
        return True

    def _can_detect_session_id(self) -> bool:
        """Tmux provides TMUX_PANE for session identification."""
        return True

    def _can_detect_working_directory(self) -> bool:
        """Tmux can detect working directory of panes."""
        return True

    def _can_paste_commands(self) -> bool:
        """Tmux can send commands to panes."""
        return True

    def _can_run_in_active_session(self) -> bool:
        """Tmux can run commands in the active pane."""
        return True

    def run_in_active_session(self, command: str) -> bool:
        """Run a command in the current active tmux pane.

        Args:
            command: Shell command to execute

        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.debug(f"Running command in active tmux pane: {command}")

        # Get the current pane ID
        current_pane = self.get_current_session_id()
        if not current_pane:
            logger.error("Could not determine current tmux pane")
            return False

        try:
            result = run_command_rw(
                ["tmux", "send-keys", "-t", current_pane, command, "Enter"],
                description=f"Send command to pane {current_pane}",
                dry_run=self.command_service.dry_run,
            )

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to run command in active pane: {e}")
            return False
