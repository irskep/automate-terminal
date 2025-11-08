"""Data models for automate-terminal."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Capabilities:
    """Terminal capabilities."""

    can_create_tabs: bool
    can_create_windows: bool
    can_list_sessions: bool
    can_switch_to_session: bool
    can_detect_session_id: bool
    can_detect_working_directory: bool
    can_paste_commands: bool
