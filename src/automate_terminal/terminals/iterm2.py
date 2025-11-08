"""iTerm2 terminal implementation."""

import logging
import os
from pathlib import Path

from .base import BaseTerminal

logger = logging.getLogger(__name__)


class ITerm2Terminal(BaseTerminal):
    """iTerm2 terminal implementation."""

    @property
    def display_name(self) -> str:
        return "iTerm2"

    def detect(self, term_program: str | None, platform_name: str) -> bool:
        """Detect if iTerm2 is the current terminal."""
        return platform_name == "Darwin" and term_program == "iTerm.app"

    def get_current_session_id(self) -> str | None:
        """Get current iTerm2 session ID."""
        session_id = os.getenv("ITERM_SESSION_ID")
        logger.debug(f"Current iTerm2 session ID: {session_id}")
        return session_id

    def supports_session_management(self) -> bool:
        """iTerm2 supports session management."""
        return True

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists in iTerm2."""
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
        """Check if iTerm2 session exists and is in the specified directory."""
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
                            if currentDirectory starts with "{self._escape_for_applescript(str(directory))}" then
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
        """Switch to an existing iTerm2 session."""
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
                                write text "{self._escape_for_applescript(session_init_script)}"
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
        """Open a new iTerm2 tab."""
        logger.debug(f"Opening new iTerm2 tab for {working_directory}")

        commands = [f"cd {self._escape_path_for_command(working_directory)}"]

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
        """Open a new iTerm2 window."""
        logger.debug(f"Opening new iTerm2 window for {working_directory}")

        commands = [f"cd {self._escape_path_for_command(working_directory)}"]
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
        """List all iTerm2 sessions with their working directories."""
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
        """Find a session ID that matches the given working directory."""
        sessions = self.list_sessions()
        target_path = str(Path(target_path).resolve())  # Normalize path

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

    def _can_create_tabs(self) -> bool:
        return True

    def _can_create_windows(self) -> bool:
        return True

    def _can_list_sessions(self) -> bool:
        return True

    def _can_switch_to_session(self) -> bool:
        return True

    def _can_detect_session_id(self) -> bool:
        return True

    def _can_paste_commands(self) -> bool:
        return True
