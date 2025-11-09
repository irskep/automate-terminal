"""Programmatic terminal automation for macOS."""

__version__ = "0.1.0"

# High-level function-based API
from .api import (
    check,
    get_current_session_id,
    get_shell_name,
    list_sessions,
    new_tab,
    new_window,
    switch_to_session,
)

# Core classes and models (for advanced usage)
from .models import Capabilities
from .terminal_service import TerminalNotFoundError

__all__ = [
    # High-level API functions
    "check",
    "new_tab",
    "new_window",
    "switch_to_session",
    "list_sessions",
    "get_current_session_id",
    "get_shell_name",
    # Core classes and exceptions
    "Capabilities",
    "TerminalNotFoundError",
    # Version
    "__version__",
]
