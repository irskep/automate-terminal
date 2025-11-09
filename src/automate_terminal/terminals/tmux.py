"""Tmux terminal implementation."""

import logging
import os
from pathlib import Path

from automate_terminal.models import Capabilities

from .base import BaseTerminal

logger = logging.getLogger(__name__)


class TmuxTerminal(BaseTerminal):
    """Tmux terminal multiplexer implementation."""

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
            output = self.command_service.execute_r_with_output(
                ["tmux", "list-panes", "-a", "-F", "#{pane_id}"],
                description="List all tmux panes",
            )
            if output:
                pane_ids = [line.strip() for line in output.split("\n")]
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
            pane_path = self.command_service.execute_r_with_output(
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
            if pane_path:
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
            window_id = self.command_service.execute_r_with_output(
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

            if not window_id:
                logger.error(f"Failed to get window for pane {session_id}")
                return False

            logger.debug(f"Pane {session_id} is in window {window_id}")

            # Switch to the window containing the target pane
            if not self.command_service.execute_rw(
                ["tmux", "select-window", "-t", window_id],
                description=f"Switch to window {window_id}",
            ):
                logger.error(f"Failed to switch to window {window_id}")
                return False

            # Then switch to the specific pane within that window
            if not self.command_service.execute_rw(
                ["tmux", "select-pane", "-t", session_id],
                description=f"Switch to pane {session_id}",
            ):
                return False

            # If there's a script to run, send it to the pane
            if session_init_script:
                return self.command_service.execute_rw(
                    [
                        "tmux",
                        "send-keys",
                        "-t",
                        session_id,
                        session_init_script,
                        "Enter",
                    ],
                    description=f"Send script to pane {session_id}",
                )

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

            return self.command_service.execute_rw(
                cmd,
                description=f"Create new tmux window in {working_directory}",
            )

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

            if not self.command_service.execute_rw(
                cmd,
                description=f"Create new tmux session in {working_directory}",
            ):
                return False

            # If there's a script to run, we need to find the new session and send keys
            if session_init_script:
                # Get the most recently created session
                session_id = self.command_service.execute_r_with_output(
                    ["tmux", "display-message", "-p", "-t", "#{session_id}"],
                    description="Get newest session ID",
                )
                if session_id:
                    self.command_service.execute_rw(
                        [
                            "tmux",
                            "send-keys",
                            "-t",
                            session_id,
                            session_init_script,
                            "Enter",
                        ],
                        description=f"Send script to session {session_id}",
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
            output = self.command_service.execute_r_with_output(
                ["tmux", "list-panes", "-a", "-F", "#{pane_id}|#{pane_current_path}"],
                description="List all tmux panes with working directories",
            )

            if not output:
                return []

            sessions = []
            for line in output.split("\n"):
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

    def get_capabilities(self) -> Capabilities:
        return Capabilities(
            can_create_tabs=True,
            can_create_windows=True,
            can_list_sessions=True,
            can_switch_to_session=True,
            can_detect_session_id=True,
            can_detect_working_directory=True,
            can_paste_commands=True,
            can_run_in_active_session=True,
        )

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
            return self.command_service.execute_rw(
                ["tmux", "send-keys", "-t", current_pane, command, "Enter"],
                description=f"Send command to pane {current_pane}",
            )

        except Exception as e:
            logger.error(f"Failed to run command in active pane: {e}")
            return False
