from dataclasses import dataclass


@dataclass(frozen=True)
class Capabilities:
    can_create_tabs: bool
    """Whether creating tabs is supported"""

    can_create_windows: bool
    """Whether creating windows is supported"""

    can_list_sessions: bool
    """Whether we can list all sessions with their working directories"""

    can_switch_to_session: bool
    """Whether we are able to switch to a specific session by ID or by working directory"""

    can_detect_session_id: bool
    """Whether we can determine a unique ID for a given session, other than working directory"""

    can_detect_working_directory: bool
    """Whether we can figure out which session responds to a given working directory"""

    can_paste_commands: bool
    """Whether we can insert text into new sessions."""

    can_run_in_active_session: bool
    """Whether we can insert text into the user's current session."""
