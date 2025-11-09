"""WezTerm terminal implementation."""

import json
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

from .base import BaseTerminal

logger = logging.getLogger(__name__)


class WeztermTerminal(BaseTerminal):
    """WezTerm terminal emulator implementation."""

    @property
    def display_name(self) -> str:
        return "WezTerm"

    def detect(self, term_program: str | None, platform_name: str) -> bool:
        """Detect if we're running inside WezTerm.

        Args:
            term_program: Value of TERM_PROGRAM environment variable
            platform_name: Platform name (WezTerm works on all platforms)

        Returns:
            True if running inside WezTerm (WEZTERM_PANE env var is set)
        """
        return os.getenv("WEZTERM_PANE") is not None

    def get_current_session_id(self) -> str | None:
        """Get current WezTerm pane ID.

        Returns:
            Current pane ID (e.g., '0', '1') or None if not available
        """
        pane_id = os.getenv("WEZTERM_PANE")
        logger.debug(f"Current WezTerm pane ID: {pane_id}")
        return pane_id

    def supports_session_management(self) -> bool:
        """WezTerm supports comprehensive session management."""
        return True

    def _parse_cwd_uri(self, cwd_uri: str) -> str:
        """Parse WezTerm's file URI to extract the path.

        Args:
            cwd_uri: File URI like "file://localhost/path/to/dir"

        Returns:
            Extracted path string
        """
        if not cwd_uri:
            return ""

        # Handle file:// URIs
        if cwd_uri.startswith("file://"):
            parsed = urlparse(cwd_uri)
            return parsed.path

        # Already a path
        return cwd_uri

    def session_exists(self, session_id: str) -> bool:
        """Check if a WezTerm pane exists.

        Args:
            session_id: Pane ID (e.g., '0', '1')

        Returns:
            True if pane exists, False otherwise
        """
        if not session_id:
            return False

        logger.debug(f"Checking if WezTerm pane exists: {session_id}")

        try:
            output = self.command_service.execute_r_with_output(
                ["wezterm", "cli", "list", "--format", "json"],
                description="List all WezTerm panes",
            )
            if output:
                panes = json.loads(output)
                pane_ids = [str(pane.get("pane_id")) for pane in panes]
                return session_id in pane_ids
        except Exception as e:
            logger.error(f"Failed to check if pane exists: {e}")

        return False

    def session_in_directory(self, session_id: str, directory: Path) -> bool:
        """Check if WezTerm pane exists and is in the specified directory.

        Args:
            session_id: Pane ID
            directory: Target directory path

        Returns:
            True if pane exists and is in directory, False otherwise
        """
        if not session_id:
            return False

        logger.debug(f"Checking if pane {session_id} is in directory {directory}")

        try:
            output = self.command_service.execute_r_with_output(
                ["wezterm", "cli", "list", "--format", "json"],
                description="List all WezTerm panes",
            )
            if output:
                panes = json.loads(output)
                for pane in panes:
                    if str(pane.get("pane_id")) == session_id:
                        pane_path = self._parse_cwd_uri(pane.get("cwd", ""))
                        return pane_path == str(directory)
        except Exception as e:
            logger.error(f"Failed to check pane directory: {e}")

        return False

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Switch to an existing WezTerm pane.

        Args:
            session_id: Pane ID to switch to
            session_init_script: Optional script to run after switching

        Returns:
            True if switch succeeded, False otherwise
        """
        logger.debug(f"Switching to WezTerm pane: {session_id}")

        try:
            # Activate the target pane
            if not self.command_service.execute_rw(
                ["wezterm", "cli", "activate-pane", "--pane-id", session_id],
                description=f"Switch to pane {session_id}",
            ):
                return False

            # If there's a script to run, send it to the pane
            if session_init_script:
                # send-text doesn't auto-press Enter, so add newline
                return self.command_service.execute_rw(
                    [
                        "wezterm",
                        "cli",
                        "send-text",
                        "--pane-id",
                        session_id,
                        "--no-paste",
                        session_init_script + "\n",
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
        """Open a new WezTerm tab (pane in current window).

        Args:
            working_directory: Directory to start in
            session_init_script: Optional script to run in new tab

        Returns:
            True if tab creation succeeded, False otherwise
        """
        logger.debug(f"Opening new WezTerm tab for {working_directory}")

        try:
            # spawn creates a new tab and returns the pane ID
            output = self.command_service.execute_r_with_output(
                ["wezterm", "cli", "spawn", "--cwd", str(working_directory)],
                description=f"Create new WezTerm tab in {working_directory}",
            )

            if not output:
                logger.error("Failed to get pane ID from spawn command")
                return False

            # If there's a script to run, send it to the new pane
            if session_init_script:
                pane_id = output.strip()
                return self.command_service.execute_rw(
                    [
                        "wezterm",
                        "cli",
                        "send-text",
                        "--pane-id",
                        pane_id,
                        "--no-paste",
                        session_init_script + "\n",
                    ],
                    description=f"Send script to pane {pane_id}",
                )

            return True

        except Exception as e:
            logger.error(f"Failed to create new tab: {e}")
            return False

    def open_new_window(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new WezTerm window.

        Args:
            working_directory: Directory to start in
            session_init_script: Optional script to run in new window

        Returns:
            True if window creation succeeded, False otherwise
        """
        logger.debug(f"Opening new WezTerm window for {working_directory}")

        try:
            # spawn with --new-window creates a new window
            output = self.command_service.execute_r_with_output(
                [
                    "wezterm",
                    "cli",
                    "spawn",
                    "--new-window",
                    "--cwd",
                    str(working_directory),
                ],
                description=f"Create new WezTerm window in {working_directory}",
            )

            if not output:
                logger.error("Failed to get pane ID from spawn command")
                return False

            # If there's a script to run, send it to the new pane
            if session_init_script:
                pane_id = output.strip()
                return self.command_service.execute_rw(
                    [
                        "wezterm",
                        "cli",
                        "send-text",
                        "--pane-id",
                        pane_id,
                        "--no-paste",
                        session_init_script + "\n",
                    ],
                    description=f"Send script to pane {pane_id}",
                )

            return True

        except Exception as e:
            logger.error(f"Failed to create new window: {e}")
            return False

    def list_sessions(self) -> list[dict[str, str]]:
        """List all WezTerm panes with their working directories.

        Returns:
            List of dicts with 'session_id' and 'working_directory' keys
        """
        logger.debug("Listing all WezTerm panes")

        try:
            output = self.command_service.execute_r_with_output(
                ["wezterm", "cli", "list", "--format", "json"],
                description="List all WezTerm panes with working directories",
            )

            if not output:
                return []

            panes = json.loads(output)
            sessions = []

            for pane in panes:
                pane_id = pane.get("pane_id")
                cwd_uri = pane.get("cwd", "")
                cwd_path = self._parse_cwd_uri(cwd_uri)

                if pane_id is not None and cwd_path:
                    sessions.append(
                        {
                            "session_id": str(pane_id),
                            "working_directory": cwd_path,
                        }
                    )

            logger.debug(f"Found {len(sessions)} WezTerm panes")
            return sessions

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    def find_session_by_working_directory(
        self, target_path: str, subdirectory_ok: bool = False
    ) -> str | None:
        """Find a WezTerm pane ID that matches the given working directory.

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
        """WezTerm can create tabs."""
        return True

    def _can_create_windows(self) -> bool:
        """WezTerm can create windows."""
        return True

    def _can_list_sessions(self) -> bool:
        """WezTerm can list all panes."""
        return True

    def _can_switch_to_session(self) -> bool:
        """WezTerm can switch to panes."""
        return True

    def _can_detect_session_id(self) -> bool:
        """WezTerm provides WEZTERM_PANE for session identification."""
        return True

    def _can_detect_working_directory(self) -> bool:
        """WezTerm can detect working directory of panes."""
        return True

    def _can_paste_commands(self) -> bool:
        """WezTerm can send commands to panes."""
        return True

    def _can_run_in_active_session(self) -> bool:
        """WezTerm can run commands in the active pane."""
        return True

    def run_in_active_session(self, command: str) -> bool:
        """Run a command in the current active WezTerm pane.

        Args:
            command: Shell command to execute

        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.debug(f"Running command in active WezTerm pane: {command}")

        # Get the current pane ID
        current_pane = self.get_current_session_id()
        if not current_pane:
            logger.error("Could not determine current WezTerm pane")
            return False

        try:
            return self.command_service.execute_rw(
                [
                    "wezterm",
                    "cli",
                    "send-text",
                    "--pane-id",
                    current_pane,
                    "--no-paste",
                    command + "\n",
                ],
                description=f"Send command to pane {current_pane}",
            )

        except Exception as e:
            logger.error(f"Failed to run command in active pane: {e}")
            return False
