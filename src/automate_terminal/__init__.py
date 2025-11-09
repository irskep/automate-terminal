"""Programmatic terminal automation for macOS."""

__version__ = "0.1.0"

from .api import (
    check,
    get_current_session_id,
    get_shell_name,
    list_sessions,
    new_tab,
    new_window,
    run_in_active_session,
    switch_to_session,
)
from .models import Capabilities
from .terminal_service import TerminalNotFoundError

__all__ = [
    "check",
    "new_tab",
    "new_window",
    "switch_to_session",
    "list_sessions",
    "get_current_session_id",
    "get_shell_name",
    "run_in_active_session",
    "Capabilities",
    "TerminalNotFoundError",
    "__version__",
]
