"""Terminal.app implementation."""

import logging
import shlex
from pathlib import Path

from automate_terminal.utils import run_command

from .base import BaseTerminal

logger = logging.getLogger(__name__)


class TerminalAppTerminal(BaseTerminal):
    """Terminal.app implementation."""

    @property
    def display_name(self) -> str:
        return "Apple Terminal.app"

    def detect(self, term_program: str | None, platform_name: str) -> bool:
        """Detect if Terminal.app is the current terminal."""
        return platform_name == "Darwin" and term_program == "Apple_Terminal"

    def get_current_session_id(self) -> str | None:
        """Terminal.app doesn't have session IDs."""
        return None

    def supports_session_management(self) -> bool:
        """Terminal.app supports session management via working directory detection."""
        return True

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists in Terminal.app by working directory."""
        if not session_id:
            return False

        applescript = f"""
        tell application "Terminal"
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    try
                        set tabTTY to tty of theTab
                        set applescriptShellCmd to "lsof " & tabTTY & " | grep -E '(zsh|bash|sh)' | head -1 | awk '{{print $2}}'"
                        set shellPid to do shell script applescriptShellCmd
                        if shellPid is not "" then
                            set cwdCmd to "lsof -p " & shellPid & " | grep cwd | awk '{{print $9}}'"
                            set workingDir to do shell script cwdCmd
                            if workingDir is "{self.applescript.escape_string(session_id)}" then
                                return true
                            end if
                        end if
                    end try
                end repeat
            end repeat
            return false
        end tell
        """

        result = self.applescript.execute_with_result(applescript)
        return result == "true" if result else False

    def _get_working_directory_from_tty(self, tty: str) -> str | None:
        """Get working directory of shell process using the given TTY."""
        try:
            # Find shell process for this TTY
            shell_cmd = f"lsof {shlex.quote(tty)} | grep -E '(zsh|bash|sh)' | head -1 | awk '{{print $2}}'"
            shell_result = run_command(
                ["bash", "-c", shell_cmd],
                timeout=5,
                description=f"Find shell process for TTY {tty}",
            )

            if shell_result.returncode != 0 or not shell_result.stdout.strip():
                return None

            pid = shell_result.stdout.strip()

            # Get working directory of that process
            cwd_cmd = f"lsof -p {shlex.quote(pid)} | grep cwd | awk '{{print $9}}'"
            cwd_result = run_command(
                ["bash", "-c", cwd_cmd],
                timeout=5,
                description=f"Get working directory for PID {pid}",
            )

            if cwd_result.returncode == 0 and cwd_result.stdout.strip():
                return cwd_result.stdout.strip()

            return None

        except Exception as e:
            logger.debug(f"Failed to get working directory from TTY {tty}: {e}")
            return None

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Switch to existing Terminal.app session by working directory."""
        # Find the window title that contains our target directory
        find_window_script = f"""
        tell application "Terminal"
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    try
                        set tabTTY to tty of theTab
                        set shellCmd to "lsof " & tabTTY & " | grep -E '(zsh|bash|sh)' | head -1 | awk '{{print $2}}'"
                        set shellPid to do shell script shellCmd
                        if shellPid is not "" then
                            set cwdCmd to "lsof -p " & shellPid & " | grep cwd | awk '{{print $9}}'"
                            set workingDir to do shell script cwdCmd
                            if workingDir is "{self.applescript.escape_string(session_id)}" then
                                -- Return the window name for menu matching
                                return name of theWindow
                            end if
                        end if
                    end try
                end repeat
            end repeat
            return ""
        end tell
        """

        window_name = self.applescript.execute_with_result(find_window_script)
        if not window_name:
            return False

        # Use System Events to click the exact menu item
        switch_script = f"""
        tell application "System Events"
            tell process "Terminal"
                try
                    -- Click the menu item with the exact window name
                    click menu item "{self.applescript.escape_string(window_name)}" of menu "Window" of menu bar 1
                    return "success"
                on error errMsg
                    -- Try with localized menu name
                    try
                        click menu item "{self.applescript.escape_string(window_name)}" of menu "窗口" of menu bar 1
                        return "success"
                    on error
                        return "error: " & errMsg
                    end try
                end try
            end tell
        end tell
        """

        # Run init script if provided
        if session_init_script:
            init_result = self.applescript.execute(
                f"""
            tell application "Terminal"
                do script "{self.applescript.escape_string(session_init_script)}" in front window
            end tell
            """
            )
            if not init_result:
                logger.warning("Failed to run init script")

        switch_result = self.applescript.execute_with_result(switch_script)
        return switch_result and switch_result.startswith("success")

    def session_in_directory(self, session_id: str, directory: Path) -> bool:
        """Check if Terminal.app session exists and is in the specified directory or subdirectory."""

        applescript = f"""
        tell application "Terminal"
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    try
                        set tabTTY to tty of theTab
                        set applescriptShellCmd to "lsof " & tabTTY & " | grep -E '(zsh|bash|sh)' | head -1 | awk '{{print $2}}'"
                        set shellPid to do shell script applescriptShellCmd
                        if shellPid is not "" then
                            set cwdCmd to "lsof -p " & shellPid & " | grep cwd | awk '{{print $9}}'"
                            set workingDir to do shell script cwdCmd
                            if workingDir starts with "{self.applescript.escape_string(str(directory))}" then
                                return true
                            end if
                        end if
                    end try
                end repeat
            end repeat
            return false
        end tell
        """

        result = self.applescript.execute_with_result(applescript)
        return result == "true" if result else False

    def open_new_tab(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Terminal.app tab.

        Terminal.app requires System Events (accessibility permissions) to create
        actual tabs via Cmd+T keyboard simulation.
        """
        logger.debug(f"Opening new Terminal.app tab for {working_directory}")

        commands = [f"cd {shlex.quote(str(working_directory))}"]
        if session_init_script:
            commands.append(session_init_script)

        command_string = self.applescript.escape_string("; ".join(commands))

        # First check if we have any Terminal windows open
        check_windows_script = """
        tell application "Terminal"
            return count of windows
        end tell
        """

        try:
            result = run_command(
                ["osascript", "-e", check_windows_script],
                timeout=5,
                description="Check Terminal windows",
            )
            window_count = int(result.stdout.strip()) if result.returncode == 0 else 0
        except Exception:
            window_count = 0

        if window_count == 0:
            # No windows open, create first window
            applescript = f"""
            tell application "Terminal"
                do script "{command_string}"
            end tell
            """
        else:
            # Windows exist, try to create a tab using System Events
            applescript = f"""
            tell application "Terminal"
                activate
                tell application "System Events"
                    tell process "Terminal"
                        keystroke "t" using command down
                    end tell
                end tell
                delay 0.3
                do script "{command_string}" in selected tab of front window
            end tell
            """

        success = self.applescript.execute(applescript)

        if not success and window_count > 0:
            # System Events failed, fall back to window creation
            logger.warning(
                "Failed to create tab (missing accessibility permissions). "
                "Creating new window instead. To fix: Enable Terminal in "
                "System Settings -> Privacy & Security -> Accessibility"
            )
            fallback_script = f"""
            tell application "Terminal"
                do script "{command_string}"
            end tell
            """
            return self.applescript.execute(fallback_script)

        return success

    def open_new_window(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Terminal.app window."""
        logger.debug(f"Opening new Terminal.app window for {working_directory}")

        commands = [f"cd {shlex.quote(str(working_directory))}"]
        if session_init_script:
            commands.append(session_init_script)

        command_string = self.applescript.escape_string("; ".join(commands))

        applescript = f"""
        tell application "Terminal"
            do script "{command_string}"
        end tell
        """

        return self.applescript.execute(applescript)

    def list_sessions(self) -> list[dict[str, str]]:
        """List all Terminal.app sessions with their working directories."""
        applescript = """
        tell application "Terminal"
            set sessionData to ""
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    try
                        set tabTTY to tty of theTab
                        set shellCmd to "lsof " & tabTTY & " | grep -E '(zsh|bash|sh)' | head -1 | awk '{print $2}'"
                        set shellPid to do shell script shellCmd
                        if shellPid is not "" then
                            set cwdCmd to "lsof -p " & shellPid & " | grep cwd | awk '{print $9}'"
                            set workingDir to do shell script cwdCmd
                            if sessionData is not "" then
                                set sessionData to sessionData & return
                            end if
                            set sessionData to sessionData & workingDir
                        end if
                    end try
                end repeat
            end repeat
            return sessionData
        end tell
        """

        output = self.applescript.execute_with_result(applescript)
        if not output:
            return []

        sessions = []
        for line in output.split("\n"):
            line = line.strip()
            if line:
                sessions.append({"working_directory": line})

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
        return False  # Terminal.app doesn't have real session IDs

    def _can_detect_working_directory(self) -> bool:
        return True

    def _can_paste_commands(self) -> bool:
        return True
