"""WezTerm terminal implementation."""

import json
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

from automate_terminal.models import Capabilities

from .base import BaseTerminal

logger = logging.getLogger(__name__)


class WeztermTerminal(BaseTerminal):
    @property
    def display_name(self) -> str:
        return "WezTerm"

    def detect(self, term_program: str | None, platform_name: str) -> bool:
        return os.getenv("WEZTERM_PANE") is not None

    def get_current_session_id(self) -> str | None:
        pane_id = os.getenv("WEZTERM_PANE")
        logger.debug(f"Current WezTerm pane ID: {pane_id}")
        return pane_id

    def supports_session_management(self) -> bool:
        return True

    def _parse_cwd_uri(self, cwd_uri: str) -> str:
        # Parses file:// URIs like "file://localhost/path/to/dir"
        if not cwd_uri:
            return ""

        if cwd_uri.startswith("file://"):
            parsed = urlparse(cwd_uri)
            return parsed.path

        return cwd_uri

    def session_exists(self, session_id: str) -> bool:
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
        logger.debug(f"Switching to WezTerm pane: {session_id}")

        try:
            if not self.command_service.execute_rw(
                ["wezterm", "cli", "activate-pane", "--pane-id", session_id],
                description=f"Switch to pane {session_id}",
            ):
                return False

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
        logger.debug(f"Opening new WezTerm tab for {working_directory}")

        try:
            output = self.command_service.execute_r_with_output(
                ["wezterm", "cli", "spawn", "--cwd", str(working_directory)],
                description=f"Create new WezTerm tab in {working_directory}",
            )

            if not output:
                logger.error("Failed to get pane ID from spawn command")
                return False

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
        logger.debug(f"Opening new WezTerm window for {working_directory}")

        try:
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
        logger.debug(f"Running command in active WezTerm pane: {command}")

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
