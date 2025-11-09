"""iTerm2 terminal implementation."""

import logging
import os
from pathlib import Path

from automate_terminal.models import Capabilities

from .base import BaseTerminal

logger = logging.getLogger(__name__)


class ITerm2Terminal(BaseTerminal):
    @property
    def display_name(self) -> str:
        return "iTerm2"

    def detect(self, term_program: str | None, platform_name: str) -> bool:
        return platform_name == "Darwin" and term_program == "iTerm.app"

    def get_current_session_id(self) -> str | None:
        session_id = os.getenv("ITERM_SESSION_ID")
        logger.debug(f"Current iTerm2 session ID: {session_id}")
        return session_id

    def supports_session_management(self) -> bool:
        return True

    def session_exists(self, session_id: str) -> bool:
        if not session_id:
            return False

        # Extract UUID part from session ID (format: w0t0p2:UUID)
        session_uuid = session_id.split(":")[-1] if ":" in session_id else session_id
        logger.debug(f"Checking if session exists: {session_uuid}")

        applescript = f"""
        tell application "iTerm2"
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    repeat with theSession in sessions of theTab
                        if id of theSession is "{session_uuid}" then
                            return true
                        end if
                    end repeat
                end repeat
            end repeat
            return false
        end tell
        """

        result = self.applescript.execute_with_result(applescript)
        return result == "true" if result else False

    def session_in_directory(self, session_id: str, directory: Path) -> bool:
        if not session_id:
            return False

        # Extract UUID part from session ID (format: w0t0p2:UUID)
        session_uuid = session_id.split(":")[-1] if ":" in session_id else session_id
        logger.debug(f"Checking if session {session_uuid} is in directory {directory}")

        applescript = f"""
        tell application "iTerm2"
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    repeat with theSession in sessions of theTab
                        if id of theSession is "{session_uuid}" then
                            set currentDirectory to get variable named "PWD" of theSession
                            if currentDirectory starts with "{self.applescript.escape(str(directory))}" then
                                return true
                            else
                                return false
                            end if
                        end if
                    end repeat
                end repeat
            end repeat
            return false
        end tell
        """

        result = self.applescript.execute_with_result(applescript)
        return result == "true" if result else False

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        logger.debug(f"Switching to iTerm2 session: {session_id}")

        # Extract UUID part from session ID (format: w0t0p2:UUID)
        session_uuid = session_id.split(":")[-1] if ":" in session_id else session_id
        logger.debug(f"Using session UUID: {session_uuid}")

        applescript = f"""
        tell application "iTerm2"
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    repeat with theSession in sessions of theTab
                        if id of theSession is "{session_uuid}" then
                            select theTab
                            select theWindow"""

        if session_init_script:
            applescript += f"""
                            tell theSession
                                write text "{self.applescript.escape(session_init_script)}"
                            end tell"""

        applescript += """
                            return
                        end if
                    end repeat
                end repeat
            end repeat
        end tell
        """

        return self.applescript.execute(applescript)

    def open_new_tab(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        logger.debug(f"Opening new iTerm2 tab for {working_directory}")

        commands = [f"cd {self.applescript.escape(working_directory)}"]

        if session_init_script:
            commands.append(session_init_script)

        applescript = f"""
        tell application "iTerm2"
            tell current window
                create tab with default profile
                tell current session of current tab
                    write text "{"; ".join(commands)}"
                end tell
            end tell
        end tell
        """

        return self.applescript.execute(applescript)

    def open_new_window(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        logger.debug(f"Opening new iTerm2 window for {working_directory}")

        commands = [f"cd {self.applescript.escape(working_directory)}"]
        if session_init_script:
            commands.append(session_init_script)

        applescript = f"""
        tell application "iTerm2"
            create window with default profile
            tell current session of current window
                write text "{"; ".join(commands)}"
            end tell
        end tell
        """

        return self.applescript.execute(applescript)

    def list_sessions(self) -> list[dict[str, str]]:
        applescript = """
        tell application "iTerm2"
            set sessionData to ""
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    repeat with theSession in sessions of theTab
                        try
                            set sessionId to id of theSession
                            set sessionPath to (variable named "session.path") of theSession
                            if sessionData is not "" then
                                set sessionData to sessionData & return
                            end if
                            set sessionData to sessionData & sessionId & "|" & sessionPath
                        on error
                            if sessionData is not "" then
                                set sessionData to sessionData & return
                            end if
                            set sessionData to sessionData & sessionId & "|unknown"
                        end try
                    end repeat
                end repeat
            end repeat
            return sessionData
        end tell
        """

        output = self.applescript.execute_with_result(applescript)
        if not output:
            return []

        sessions = []
        # Output format: "session1|/path1\nsession2|/path2\n..."
        for line in output.split("\n"):
            line = line.strip()
            if line and "|" in line:
                session_id, path = line.split("|", 1)
                sessions.append(
                    {
                        "session_id": session_id.strip(),
                        "working_directory": path.strip(),
                    }
                )

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
        logger.debug(f"Running command in active iTerm2 session: {command}")

        applescript = f"""
        tell application "iTerm2"
            tell current session of current window
                write text "{self.applescript.escape(command)}"
            end tell
        end tell
        """

        return self.applescript.execute(applescript)
