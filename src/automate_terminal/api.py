"""
Python-importable equivalents of cli commands. The canonical API of
automate-terminal is the command line, but if you're already writing a Python
program, and autoamte-terminal is written in Python, we might as well have an
API.
"""

import os
from dataclasses import asdict
from pathlib import Path

from .applescript_service import AppleScriptService
from .command_service import CommandService
from .models import Capabilities
from .terminal_service import TerminalService


def _get_terminal_service(
    dry_run: bool = False, debug: bool = False
) -> TerminalService:
    command_service = CommandService(dry_run=dry_run)
    applescript_service = AppleScriptService(command_service=command_service)
    return TerminalService(applescript_service=applescript_service)


def check(dry_run: bool = False, debug: bool = False) -> dict[str, str | Capabilities]:
    service = _get_terminal_service(dry_run=dry_run, debug=debug)
    caps = service.get_capabilities()

    return {
        "terminal": service.get_terminal_name(),
        "term_program": os.getenv("TERM_PROGRAM", ""),
        "shell": service.get_shell_name() or "unknown",
        "current_session_id": service.get_current_session_id(),
        "current_working_directory": str(Path.cwd()),
        "capabilities": asdict(caps),
    }


def new_tab(
    working_directory: Path | str,
    paste_script: str | None = None,
    dry_run: bool = False,
    debug: bool = False,
) -> bool:
    service = _get_terminal_service(dry_run=dry_run, debug=debug)
    working_directory = Path(working_directory)
    return service.new_tab(
        working_directory=working_directory, paste_script=paste_script
    )


def new_window(
    working_directory: Path | str,
    paste_script: str | None = None,
    dry_run: bool = False,
    debug: bool = False,
) -> bool:
    service = _get_terminal_service(dry_run=dry_run, debug=debug)
    working_directory = Path(working_directory)
    return service.new_window(
        working_directory=working_directory, paste_script=paste_script
    )


def switch_to_session(
    session_id: str | None = None,
    working_directory: Path | str | None = None,
    paste_script: str | None = None,
    subdirectory_ok: bool = False,
    dry_run: bool = False,
    debug: bool = False,
) -> bool:
    service = _get_terminal_service(dry_run=dry_run, debug=debug)

    if working_directory is not None:
        working_directory = Path(working_directory)

    return service.switch_to_session(
        session_id=session_id,
        working_directory=working_directory,
        paste_script=paste_script,
        subdirectory_ok=subdirectory_ok,
    )


def list_sessions(
    dry_run: bool = False,
    debug: bool = False,
) -> list[dict[str, str]]:
    service = _get_terminal_service(dry_run=dry_run, debug=debug)
    return service.list_sessions()


def get_current_session_id(
    dry_run: bool = False,
    debug: bool = False,
) -> str | None:
    service = _get_terminal_service(dry_run=dry_run, debug=debug)
    return service.get_current_session_id()


def get_shell_name(
    dry_run: bool = False,
    debug: bool = False,
) -> str | None:
    service = _get_terminal_service(dry_run=dry_run, debug=debug)
    return service.get_shell_name()


def run_in_active_session(
    command: str,
    dry_run: bool = False,
    debug: bool = False,
) -> bool:
    service = _get_terminal_service(dry_run=dry_run, debug=debug)
    return service.run_in_active_session(command)


__all__ = [
    "check",
    "new_tab",
    "new_window",
    "switch_to_session",
    "list_sessions",
    "get_current_session_id",
    "get_shell_name",
    "run_in_active_session",
]
