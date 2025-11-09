"""Kitty terminal implementation."""

import json
import logging
import os
from pathlib import Path

from automate_terminal.models import Capabilities

from .base import BaseTerminal

logger = logging.getLogger(__name__)


class KittyTerminal(BaseTerminal):
    # Requires allow_remote_control=yes in kitty.conf

    @property
    def display_name(self) -> str:
        return "Kitty"

    def detect(self, term_program: str | None, platform_name: str) -> bool:
        return os.getenv("KITTY_WINDOW_ID") is not None

    def get_current_session_id(self) -> str | None:
        window_id = os.getenv("KITTY_WINDOW_ID")
        logger.debug(f"Current Kitty window ID: {window_id}")
        return window_id

    def supports_session_management(self) -> bool:
        return True

    def _get_all_windows(self) -> list[dict]:
        # Navigate nested structure: OS windows -> tabs -> windows
        try:
            output = self.command_service.execute_r_with_output(
                ["kitten", "@", "ls"],
                description="List all Kitty windows",
            )

            if not output:
                return []

            os_windows = json.loads(output)
            all_windows = []

            for os_window in os_windows:
                for tab in os_window.get("tabs", []):
                    for window in tab.get("windows", []):
                        all_windows.append(window)

            return all_windows

        except Exception as e:
            logger.error(f"Failed to list Kitty windows: {e}")
            return []

    def session_exists(self, session_id: str) -> bool:
        if not session_id:
            return False

        logger.debug(f"Checking if Kitty window exists: {session_id}")

        windows = self._get_all_windows()
        window_ids = [str(w.get("id")) for w in windows]
        return session_id in window_ids

    def session_in_directory(self, session_id: str, directory: Path) -> bool:
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
        logger.debug(f"Switching to Kitty window: {session_id}")

        try:
            if not self.command_service.execute_rw(
                ["kitten", "@", "focus-window", "--match", f"id:{session_id}"],
                description=f"Switch to window {session_id}",
            ):
                return False

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
        logger.debug(f"Opening new Kitty tab for {working_directory}")

        try:
            cmd = [
                "kitten",
                "@",
                "launch",
                "--type=tab",
                "--cwd",
                str(working_directory),
            ]

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
        logger.debug(f"Opening new Kitty window for {working_directory}")

        try:
            cmd = [
                "kitten",
                "@",
                "launch",
                "--type=os-window",
                "--cwd",
                str(working_directory),
            ]

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
        sessions = self.list_sessions()
        target_path = str(Path(target_path).resolve())

        for session in sessions:
            session_path = str(Path(session["working_directory"]).resolve())
            if session_path == target_path:
                return session["session_id"]

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
        logger.debug(f"Running command in active Kitty window: {command}")

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
