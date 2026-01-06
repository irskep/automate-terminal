"""Guake terminal implementation."""

import logging
import os
import re
import shutil
from pathlib import Path

from automate_terminal.models import Capabilities

from .base import BaseTerminal

logger = logging.getLogger(__name__)

GUAKE_DBUS_DEST = "org.guake3.RemoteControl"
GUAKE_DBUS_PATH = "/org/guake3/RemoteControl"
GUAKE_DBUS_INTERFACE = "org.guake3.RemoteControl"
PROC_ROOT = Path("/proc")
HAS_GDBUS = shutil.which("gdbus") is not None
SHELL_PROCESS_NAMES = {"bash", "zsh", "fish", "sh", "dash"}


class GuakeTerminal(BaseTerminal):
    # Requires Guake terminal plus gdbus CLI support

    @property
    def display_name(self) -> str:
        return "Guake"

    def detect(self, term_program: str | None, platform_name: str) -> bool:
        # Guake sets GUAKE_TAB_UUID environment variable
        return os.getenv("GUAKE_TAB_UUID") is not None and HAS_GDBUS

    def _call_gdbus(self, method: str, args: list[str] | None = None) -> str | None:
        """Invoke a Guake DBus method via gdbus and return raw output."""
        if not HAS_GDBUS:
            logger.error("gdbus command not available")
            return None

        full_method = f"{GUAKE_DBUS_INTERFACE}.{method}"
        cmd = [
            "gdbus",
            "call",
            "--session",
            "--dest",
            GUAKE_DBUS_DEST,
            "--object-path",
            GUAKE_DBUS_PATH,
            "--method",
            full_method,
        ]
        if args:
            cmd.extend(args)

        description = f"Guake DBus call {method}"
        return self.command_service.execute_r_with_output(
            cmd,
            timeout=10,
            description=description,
        )

    def _call_gdbus_bool(
        self, method: str, args: list[str] | None = None
    ) -> bool | None:
        output = self._call_gdbus(method, args)
        if not output:
            return None
        normalized = output.strip().lower()
        if "true" in normalized or "(1," in normalized:
            return True
        if "false" in normalized or "(0," in normalized:
            return False
        logger.error(f"Failed to parse boolean from gdbus output: {output}")
        return None

    def _call_gdbus_int(self, method: str, args: list[str] | None = None) -> int | None:
        output = self._call_gdbus(method, args)
        if not output:
            return None
        match = re.search(r"int\d+\s+(-?\d+)", output)
        if not match:
            match = re.search(r"(-?\d+)", output)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        logger.error(f"Failed to parse integer from gdbus output: {output}")
        return None

    def _read_proc_comm(self, proc_path: Path) -> str:
        try:
            return (proc_path / "comm").read_text().strip()
        except (FileNotFoundError, ProcessLookupError, PermissionError, OSError):
            return ""

    def _read_proc_ppid(self, proc_path: Path) -> int | None:
        status_path = proc_path / "status"
        try:
            for line in status_path.read_text().splitlines():
                if line.startswith("PPid:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return int(parts[1])
        except (
            FileNotFoundError,
            ProcessLookupError,
            PermissionError,
            OSError,
            ValueError,
        ):
            pass
        return None

    def _read_proc_environ(self, proc_path: Path) -> dict[str, str]:
        environ_path = proc_path / "environ"
        try:
            raw = environ_path.read_bytes()
        except (FileNotFoundError, ProcessLookupError, PermissionError, OSError):
            return {}

        env: dict[str, str] = {}
        for entry in raw.split(b"\0"):
            if not entry:
                continue
            try:
                key, value = entry.split(b"=", 1)
            except ValueError:
                continue
            env[key.decode(errors="ignore")] = value.decode(errors="ignore")
        return env

    def _read_proc_cwd(self, proc_path: Path) -> str | None:
        try:
            return os.readlink(proc_path / "cwd")
        except (FileNotFoundError, ProcessLookupError, PermissionError, OSError):
            return None

    def _has_guake_ancestor(
        self,
        pid: int,
        processes: dict[int, dict[str, object]],
        guake_pids: set[int],
    ) -> bool:
        visited: set[int] = set()
        current = pid

        while True:
            info = processes.get(current)
            if not info:
                return False

            parent_pid = info.get("ppid")
            if not isinstance(parent_pid, int) or parent_pid <= 1:
                return False

            if parent_pid in guake_pids:
                return True

            if parent_pid in visited:
                return False

            visited.add(parent_pid)
            current = parent_pid

    def get_current_session_id(self) -> str | None:
        # Return current tab UUID from environment
        tab_uuid = os.getenv("GUAKE_TAB_UUID")
        logger.debug(f"Current Guake tab UUID: {tab_uuid}")
        return tab_uuid

    def supports_session_management(self) -> bool:
        return True

    def _get_shell_processes(self):
        """Get all shell processes running under Guake with their tab UUIDs and CWDs."""
        proc_root = PROC_ROOT
        if not proc_root.exists():
            logger.warning(
                "/proc filesystem not available; cannot inspect Guake sessions"
            )
            return []

        processes: dict[int, dict[str, object]] = {}
        guake_pids: set[int] = set()

        try:
            for entry in proc_root.iterdir():
                if not entry.name.isdigit():
                    continue
                pid = int(entry.name)

                name = self._read_proc_comm(entry)
                if not name:
                    continue

                ppid = self._read_proc_ppid(entry)
                processes[pid] = {"ppid": ppid, "name": name, "path": entry}

                if "guake" in name.lower():
                    guake_pids.add(pid)
        except Exception as e:
            logger.error(f"Failed to enumerate processes: {e}")
            return []

        if not guake_pids:
            logger.debug("No Guake processes found")
            return []

        sessions = []
        for pid, info in processes.items():
            name = info["name"]
            if name not in SHELL_PROCESS_NAMES:
                continue

            if not self._has_guake_ancestor(pid, processes, guake_pids):
                continue

            proc_path = info["path"]

            env = self._read_proc_environ(proc_path)
            tab_uuid = env.get("GUAKE_TAB_UUID")
            if not tab_uuid:
                continue

            cwd = self._read_proc_cwd(proc_path)
            if not cwd:
                continue

            sessions.append({"tab_uuid": tab_uuid, "cwd": cwd, "pid": pid})

        return sessions

    def session_exists(self, session_id: str) -> bool:
        if not session_id:
            return False

        logger.debug(f"Checking if Guake tab exists: {session_id}")

        # Check if any shell process has this tab UUID
        sessions = self._get_shell_processes()
        return any(s["tab_uuid"] == session_id for s in sessions)

    def session_in_directory(self, session_id: str, directory: Path) -> bool:
        if not session_id:
            return False

        logger.debug(f"Checking if tab {session_id} is in directory {directory}")

        sessions = self._get_shell_processes()
        target_path = str(directory.resolve())

        for session in sessions:
            if session["tab_uuid"] == session_id:
                return session["cwd"] == target_path

        return False

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        logger.debug(f"Switching to Guake tab: {session_id}")

        tab_index = self._call_gdbus_int("get_index_from_uuid", [session_id])
        if tab_index is None or tab_index < 0:
            logger.error(f"Tab with UUID {session_id} not found")
            return False

        if not self._call_gdbus("select_tab", [str(tab_index)]):
            return False

        visibility = self._call_gdbus_bool("get_visibility")
        if visibility is False:
            if not self._call_gdbus("show"):
                return False

        if session_init_script:
            if not self._call_gdbus("execute_command", [session_init_script + "\n"]):
                return False

        return True

    def open_new_tab(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        logger.debug(f"Opening new Guake tab for {working_directory}")

        if not self._call_gdbus("add_tab", [str(working_directory)]):
            return False

        visibility = self._call_gdbus_bool("get_visibility")
        if visibility is False:
            if not self._call_gdbus("show"):
                return False

        if session_init_script:
            if not self._call_gdbus("execute_command", [session_init_script + "\n"]):
                return False

        return True

    def open_new_window(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        # Guake is a dropdown terminal, it doesn't support multiple windows
        # Fall back to creating a new tab
        logger.debug("Guake doesn't support windows, creating tab instead")
        return self.open_new_tab(working_directory, session_init_script)

    def list_sessions(self) -> list[dict[str, str]]:
        logger.debug("Listing all Guake tabs")

        sessions = self._get_shell_processes()
        result = []

        # Deduplicate by tab_uuid (there may be multiple shells per tab due to splits)
        seen_uuids = set()
        for session in sessions:
            tab_uuid = session["tab_uuid"]
            if tab_uuid not in seen_uuids:
                seen_uuids.add(tab_uuid)
                result.append(
                    {
                        "session_id": tab_uuid,
                        "working_directory": session["cwd"],
                    }
                )

        logger.debug(f"Found {len(result)} Guake tabs")
        return result

    def find_session_by_working_directory(
        self, target_path: str, subdirectory_ok: bool = False
    ) -> str | None:
        sessions = self.list_sessions()
        target_path = str(Path(target_path).resolve())

        # First try exact match
        for session in sessions:
            session_path = str(Path(session["working_directory"]).resolve())
            if session_path == target_path:
                return session["session_id"]

        # Then try subdirectory match if allowed
        if subdirectory_ok:
            for session in sessions:
                session_path = str(Path(session["working_directory"]).resolve())
                if session_path.startswith(target_path + "/"):
                    return session["session_id"]

        return None

    def get_capabilities(self) -> Capabilities:
        return Capabilities(
            can_create_tabs=True,
            can_create_windows=False,  # Guake is a dropdown terminal
            can_list_sessions=True,
            can_switch_to_session=True,
            can_detect_session_id=True,
            can_detect_working_directory=True,
            can_paste_commands=True,
            can_run_in_active_session=True,
        )

    def run_in_active_session(self, command: str) -> bool:
        logger.debug(f"Running command in active Guake tab: {command}")
        if not self._call_gdbus("execute_command", [command + "\n"]):
            return False

        return True
