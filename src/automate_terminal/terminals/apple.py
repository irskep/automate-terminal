"""Terminal.app implementation."""

import logging
import shlex
from pathlib import Path

from automate_terminal.models import Capabilities

from .base import BaseTerminal

logger = logging.getLogger(__name__)


class TerminalAppTerminal(BaseTerminal):
    @property
    def display_name(self) -> str:
        return "Apple Terminal.app"

    def detect(self, term_program: str | None, platform_name: str) -> bool:
        return platform_name == "Darwin" and term_program == "Apple_Terminal"

    def get_current_session_id(self) -> str | None:
        # Terminal.app doesn't have session IDs.
        return None

    def supports_session_management(self) -> bool:
        # Terminal.app doesn't support session management via session IDs.
        # It only supports working directory-based switching.
        return False

    def session_exists(self, session_id: str) -> bool:
        # Terminal.app doesn't have session IDs.
        return False

    def _get_working_directory_from_tty(self, tty: str) -> str | None:
        # Terminal.app's AppleScript API only exposes TTY, not working directory.
        # Work around this by: TTY → find shell PID → get that process's cwd via lsof.
        try:
            shell_cmd = f"lsof {shlex.quote(tty)} | grep -E '(zsh|bash|fish|osh|nu|pwsh|sh)' | head -1 | awk '{{print $2}}'"
            pid = self.command_service.execute_r_with_output(
                ["bash", "-c", shell_cmd],
                timeout=5,
                description=f"Find shell process for TTY {tty}",
            )

            if not pid:
                return None

            # Get working directory of that process
            cwd_cmd = f"lsof -p {shlex.quote(pid)} | grep cwd | awk '{{print $9}}'"
            cwd = self.command_service.execute_r_with_output(
                ["bash", "-c", cwd_cmd],
                timeout=5,
                description=f"Get working directory for PID {pid}",
            )

            return cwd if cwd else None

        except Exception as e:
            logger.debug(f"Failed to get working directory from TTY {tty}: {e}")
            return None

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        # Terminal.app doesn't have session IDs.
        return False

    def switch_to_session_by_working_directory(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        # Terminal.app can't switch to tabs directly, so we:
        # 1. Find the window containing a tab with the target directory (via TTY → PID → cwd chain)
        # 2. Use System Events to click that window's menu item to bring it to front
        working_directory_str = str(working_directory)

        find_window_script = f"""
        tell application "Terminal"
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    try
                        set tabTTY to tty of theTab
                        set shellCmd to "lsof " & tabTTY & " | grep -E '(zsh|bash|fish|osh|nu|pwsh|sh)' | head -1 | awk '{{print $2}}'"
                        set shellPid to do shell script shellCmd
                        if shellPid is not "" then
                            set cwdCmd to "lsof -p " & shellPid & " | grep cwd | awk '{{print $9}}'"
                            set workingDir to do shell script cwdCmd
                            if workingDir is "{self.applescript.escape(working_directory_str)}" then
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
                    click menu item "{self.applescript.escape(window_name)}" of menu "Window" of menu bar 1
                    return "success"
                on error errMsg
                    -- Try with localized menu name
                    try
                        click menu item "{self.applescript.escape(window_name)}" of menu "窗口" of menu bar 1
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
                do script "{self.applescript.escape(session_init_script)}" in front window
            end tell
            """
            )
            if not init_result:
                logger.warning("Failed to run init script")

        switch_result = self.applescript.execute_with_result(switch_script)
        return switch_result and switch_result.startswith("success")

    def session_in_directory(self, session_id: str, directory: Path) -> bool:
        # Terminal.app doesn't have session IDs.
        return False

    def open_new_tab(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        # Terminal.app requires System Events (accessibility permissions) to create
        # actual tabs via Cmd+T keyboard simulation.
        logger.debug(f"Opening new Terminal.app tab for {working_directory}")

        commands = [f"cd {shlex.quote(str(working_directory))}"]
        if session_init_script:
            commands.append(session_init_script)

        command_string = self.applescript.escape("; ".join(commands))

        # First check if we have any Terminal windows open
        check_windows_script = """
        tell application "Terminal"
            return count of windows
        end tell
        """

        try:
            result = self.command_service.execute_r_with_output(
                ["osascript", "-e", check_windows_script],
                timeout=5,
                description="Check Terminal windows",
            )
            window_count = int(result) if result else 0
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
        logger.debug(f"Opening new Terminal.app window for {working_directory}")

        commands = [f"cd {shlex.quote(str(working_directory))}"]
        if session_init_script:
            commands.append(session_init_script)

        command_string = self.applescript.escape("; ".join(commands))

        applescript = f"""
        tell application "Terminal"
            do script "{command_string}"
        end tell
        """

        return self.applescript.execute(applescript)

    def list_sessions(self) -> list[dict[str, str]]:
        # Terminal.app doesn't have session IDs, so only working_directory is returned
        applescript = """
        tell application "Terminal"
            set sessionData to ""
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    try
                        set tabTTY to tty of theTab
                        set shellCmd to "lsof " & tabTTY & " | grep -E '(zsh|bash|fish|osh|nu|pwsh|sh)' | head -1 | awk '{print $2}'"
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
        # Terminal.app doesn't have session IDs
        return None

    def get_capabilities(self) -> Capabilities:
        return Capabilities(
            can_create_tabs=True,
            can_create_windows=True,
            can_list_sessions=True,
            can_switch_to_session=True,
            can_detect_session_id=False,
            can_detect_working_directory=True,
            can_paste_commands=True,
            can_run_in_active_session=True,
        )

    def run_in_active_session(self, command: str) -> bool:
        logger.debug(f"Running command in active Terminal.app session: {command}")

        applescript = f"""
        tell application "Terminal"
            do script "{self.applescript.escape(command)}" in selected tab of front window
        end tell
        """

        return self.applescript.execute(applescript)
