"""Kitty terminal implementation."""

import json
import logging
import os
from pathlib import Path

from .base import BaseTerminal

logger = logging.getLogger(__name__)


class KittyTerminal(BaseTerminal):
    """Kitty terminal emulator implementation.

    Note: Requires allow_remote_control=yes in kitty.conf to function.
    """

    @property
    def display_name(self) -> str:
        return "Kitty"

    def detect(self, term_program: str | None, platform_name: str) -> bool:
        """Detect if we're running inside Kitty.

        Args:
            term_program: Value of TERM_PROGRAM environment variable (unused for Kitty)
            platform_name: Platform name (Kitty works on macOS, Linux, BSD)

        Returns:
            True if running inside Kitty (KITTY_WINDOW_ID env var is set)
        """
        return os.getenv("KITTY_WINDOW_ID") is not None

    def get_current_session_id(self) -> str | None:
        """Get current Kitty window ID.

        Returns:
            Current window ID or None if not available
        """
        window_id = os.getenv("KITTY_WINDOW_ID")
        logger.debug(f"Current Kitty window ID: {window_id}")
        return window_id

    def supports_session_management(self) -> bool:
        """Kitty supports comprehensive session management via remote control."""
        return True

    def _get_all_windows(self) -> list[dict]:
        """Get all Kitty windows from all OS windows and tabs.

        Returns:
            List of window objects with id, cwd, title, etc.
        """
        try:
            output = self.command_service.execute_r_with_output(
                ["kitten", "@", "ls"],
                description="List all Kitty windows",
            )

            if not output:
                return []

            os_windows = json.loads(output)
            all_windows = []

            # Navigate the nested structure: OS windows -> tabs -> windows
            for os_window in os_windows:
                for tab in os_window.get("tabs", []):
                    for window in tab.get("windows", []):
                        all_windows.append(window)

            return all_windows

        except Exception as e:
            logger.error(f"Failed to list Kitty windows: {e}")
            return []

    def session_exists(self, session_id: str) -> bool:
        """Check if a Kitty window exists.

        Args:
            session_id: Window ID

        Returns:
            True if window exists, False otherwise
        """
        if not session_id:
            return False

        logger.debug(f"Checking if Kitty window exists: {session_id}")

        windows = self._get_all_windows()
        window_ids = [str(w.get("id")) for w in windows]
        return session_id in window_ids

    def session_in_directory(self, session_id: str, directory: Path) -> bool:
        """Check if Kitty window exists and is in the specified directory.

        Args:
            session_id: Window ID
            directory: Target directory path

        Returns:
            True if window exists and is in directory, False otherwise
        """
        if not session_id:
            return False

        logger.debug(f"Checking if window {session_id} is in directory {directory}")

        windows = self._get_all_windows()
        for window in windows:
            if str(window.get("id")) == session_id:
                window_cwd = window.get("cwd", "")
                return window_cwd == str(directory)

        return False

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Switch to an existing Kitty window.

        Args:
            session_id: Window ID to switch to
            session_init_script: Optional script to run after switching

        Returns:
            True if switch succeeded, False otherwise
        """
        logger.debug(f"Switching to Kitty window: {session_id}")

        try:
            # Focus the target window
            if not self.command_service.execute_rw(
                ["kitten", "@", "focus-window", "--match", f"id:{session_id}"],
                description=f"Switch to window {session_id}",
            ):
                return False

            # If there's a script to run, send it to the window
            if session_init_script:
                return self.command_service.execute_rw(
                    [
                        "kitten",
                        "@",
                        "send-text",
                        "--match",
                        f"id:{session_id}",
                        session_init_script + "\n",
                    ],
                    description=f"Send script to window {session_id}",
                )

            return True

        except Exception as e:
            logger.error(f"Failed to switch to window: {e}")
            return False

    def open_new_tab(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Kitty tab.

        Args:
            working_directory: Directory to start in
            session_init_script: Optional script to run in new tab

        Returns:
            True if tab creation succeeded, False otherwise
        """
        logger.debug(f"Opening new Kitty tab for {working_directory}")

        try:
            # Create new tab with specified working directory
            cmd = [
                "kitten",
                "@",
                "launch",
                "--type=tab",
                "--cwd",
                str(working_directory),
            ]

            # If there's a script to run, we can't easily get the new window ID
            # from launch, so we'll run the script as the launch command
            if session_init_script:
                # Use the shell to run both cd and the script
                cmd.extend(
                    [
                        "sh",
                        "-c",
                        f"cd {working_directory} && {session_init_script}",
                    ]
                )
                return self.command_service.execute_rw(
                    cmd,
                    description=f"Create new Kitty tab in {working_directory} with script",
                )
            else:
                return self.command_service.execute_rw(
                    cmd,
                    description=f"Create new Kitty tab in {working_directory}",
                )

        except Exception as e:
            logger.error(f"Failed to create new tab: {e}")
            return False

    def open_new_window(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Kitty OS window.

        Args:
            working_directory: Directory to start in
            session_init_script: Optional script to run in new window

        Returns:
            True if window creation succeeded, False otherwise
        """
        logger.debug(f"Opening new Kitty window for {working_directory}")

        try:
            # Create new OS window with specified working directory
            cmd = [
                "kitten",
                "@",
                "launch",
                "--type=os-window",
                "--cwd",
                str(working_directory),
            ]

            # If there's a script to run, execute it as the launch command
            if session_init_script:
                cmd.extend(
                    [
                        "sh",
                        "-c",
                        f"cd {working_directory} && {session_init_script}",
                    ]
                )
                return self.command_service.execute_rw(
                    cmd,
                    description=f"Create new Kitty window in {working_directory} with script",
                )
            else:
                return self.command_service.execute_rw(
                    cmd,
                    description=f"Create new Kitty window in {working_directory}",
                )

        except Exception as e:
            logger.error(f"Failed to create new window: {e}")
            return False

    def list_sessions(self) -> list[dict[str, str]]:
        """List all Kitty windows with their working directories.

        Returns:
            List of dicts with 'session_id' and 'working_directory' keys
        """
        logger.debug("Listing all Kitty windows")

        windows = self._get_all_windows()
        sessions = []

        for window in windows:
            window_id = window.get("id")
            cwd = window.get("cwd", "")

            if window_id is not None and cwd:
                sessions.append(
                    {
                        "session_id": str(window_id),
                        "working_directory": cwd,
                    }
                )

        logger.debug(f"Found {len(sessions)} Kitty windows")
        return sessions

    def find_session_by_working_directory(
        self, target_path: str, subdirectory_ok: bool = False
    ) -> str | None:
        """Find a Kitty window ID that matches the given working directory.

        Args:
            target_path: Target directory path
            subdirectory_ok: If True, match windows in subdirectories of target_path

        Returns:
            Window ID if found, None otherwise
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
        """Kitty can create tabs."""
        return True

    def _can_create_windows(self) -> bool:
        """Kitty can create OS windows."""
        return True

    def _can_list_sessions(self) -> bool:
        """Kitty can list all windows."""
        return True

    def _can_switch_to_session(self) -> bool:
        """Kitty can switch to windows."""
        return True

    def _can_detect_session_id(self) -> bool:
        """Kitty provides KITTY_WINDOW_ID for session identification."""
        return True

    def _can_detect_working_directory(self) -> bool:
        """Kitty can detect working directory of windows."""
        return True

    def _can_paste_commands(self) -> bool:
        """Kitty can send commands to windows."""
        return True

    def _can_run_in_active_session(self) -> bool:
        """Kitty can run commands in the active window."""
        return True

    def run_in_active_session(self, command: str) -> bool:
        """Run a command in the current active Kitty window.

        Args:
            command: Shell command to execute

        Returns:
            True if command was sent successfully, False otherwise
        """
        logger.debug(f"Running command in active Kitty window: {command}")

        # Get the current window ID
        current_window = self.get_current_session_id()
        if not current_window:
            logger.error("Could not determine current Kitty window")
            return False

        try:
            return self.command_service.execute_rw(
                [
                    "kitten",
                    "@",
                    "send-text",
                    "--match",
                    f"id:{current_window}",
                    command + "\n",
                ],
                description=f"Send command to window {current_window}",
            )

        except Exception as e:
            logger.error(f"Failed to run command in active window: {e}")
            return False
