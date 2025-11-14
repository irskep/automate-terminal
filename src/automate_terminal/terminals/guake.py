"""Guake terminal implementation."""

import logging
import os
from pathlib import Path

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import dbus

    HAS_DBUS = True
except ImportError:
    HAS_DBUS = False
    dbus = None

from automate_terminal.models import Capabilities

from .base import BaseTerminal

logger = logging.getLogger(__name__)


class GuakeTerminal(BaseTerminal):
    # Requires Guake terminal and python-dbus

    @property
    def display_name(self) -> str:
        return "Guake"

    def detect(self, term_program: str | None, platform_name: str) -> bool:
        # Guake sets GUAKE_TAB_UUID environment variable
        # Also require psutil and dbus to be available
        return os.getenv("GUAKE_TAB_UUID") is not None and HAS_PSUTIL and HAS_DBUS

    def _get_dbus_interface(self):
        """Get Guake DBus interface."""
        if not HAS_DBUS:
            logger.error("dbus-python module not available")
            return None

        try:
            bus = dbus.SessionBus()
            obj = bus.get_object(
                "org.guake3.RemoteControl", "/org/guake3/RemoteControl"
            )
            return dbus.Interface(obj, "org.guake3.RemoteControl")
        except Exception as e:
            logger.error(f"Failed to connect to Guake DBus: {e}")
            return None

    def get_current_session_id(self) -> str | None:
        # Return current tab UUID from environment
        tab_uuid = os.getenv("GUAKE_TAB_UUID")
        logger.debug(f"Current Guake tab UUID: {tab_uuid}")
        return tab_uuid

    def supports_session_management(self) -> bool:
        return True

    def _get_shell_processes(self):
        """Get all shell processes running under Guake with their tab UUIDs and CWDs."""
        sessions = []

        if not HAS_PSUTIL:
            logger.warning("psutil not available, cannot list sessions")
            return sessions

        try:
            # Find Guake process
            guake_pids = [
                p.pid
                for p in psutil.process_iter(["name"])
                if "guake" in p.info["name"].lower()
            ]

            if not guake_pids:
                logger.debug("No Guake processes found")
                return sessions

            # Find all shell processes that are children of Guake
            for proc in psutil.process_iter(["pid", "name", "ppid", "cwd"]):
                try:
                    if proc.info["name"] in ["bash", "zsh", "fish", "sh", "dash"]:
                        # Check if it's a Guake child (direct or indirect)
                        parent = proc.parent()
                        while parent:
                            if (
                                parent.pid in guake_pids
                                or "guake" in parent.name().lower()
                            ):
                                # Get environment to find GUAKE_TAB_UUID
                                try:
                                    env = proc.environ()
                                    tab_uuid = env.get("GUAKE_TAB_UUID")
                                    if tab_uuid:
                                        sessions.append(
                                            {
                                                "tab_uuid": tab_uuid,
                                                "cwd": proc.info["cwd"],
                                                "pid": proc.info["pid"],
                                            }
                                        )
                                except (psutil.AccessDenied, AttributeError):
                                    pass
                                break
                            parent = parent.parent()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            return sessions

        except Exception as e:
            logger.error(f"Failed to get shell processes: {e}")
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

        iface = self._get_dbus_interface()
        if not iface:
            return False

        try:
            # Get tab index from UUID
            tab_index = iface.get_index_from_uuid(session_id)
            if tab_index < 0:
                logger.error(f"Tab with UUID {session_id} not found")
                return False

            # Select the tab
            iface.select_tab(tab_index)

            # Make sure Guake is visible
            if not iface.get_visibility():
                iface.show()

            # Execute script if provided
            if session_init_script:
                # Send the command to the terminal
                iface.execute_command(session_init_script + "\n")

            return True

        except Exception as e:
            logger.error(f"Failed to switch to tab: {e}")
            return False

    def open_new_tab(
        self, working_directory: Path, session_init_script: str | None = None
    ) -> bool:
        logger.debug(f"Opening new Guake tab for {working_directory}")

        iface = self._get_dbus_interface()
        if not iface:
            return False

        try:
            # Create new tab with working directory
            iface.add_tab(str(working_directory))

            # Make sure Guake is visible
            if not iface.get_visibility():
                iface.show()

            # Execute script if provided
            if session_init_script:
                # The new tab should now be selected, execute command
                iface.execute_command(session_init_script + "\n")

            return True

        except Exception as e:
            logger.error(f"Failed to create new tab: {e}")
            return False

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

        iface = self._get_dbus_interface()
        if not iface:
            return False

        try:
            iface.execute_command(command + "\n")
            return True

        except Exception as e:
            logger.error(f"Failed to run command in active tab: {e}")
            return False
