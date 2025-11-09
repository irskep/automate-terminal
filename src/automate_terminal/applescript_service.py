"""AppleScript execution service with dry-run support."""

import logging
import platform
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from automate_terminal.command_service import CommandService

logger = logging.getLogger(__name__)


class AppleScriptService:
    """Service for executing AppleScript with optional dry-run mode."""

    def __init__(self, command_service: "CommandService"):
        """Initialize AppleScript service.

        Args:
            command_service: Service for executing shell commands
        """
        self.command_service = command_service
        self.dry_run = command_service.dry_run
        self.is_macos = platform.system() == "Darwin"

    def execute(self, script: str) -> bool:
        """Execute AppleScript and return success status.

        Args:
            script: AppleScript code to execute

        Returns:
            True if successful (or in dry-run mode), False otherwise
        """
        if not self.is_macos:
            logger.warning("AppleScript not available on this platform")
            return False

        if self.dry_run:
            logger.info("DRY RUN - Would execute AppleScript:")
            logger.info(script)
            return True

        return self.command_service.execute_r(
            ["osascript", "-e", script],
            timeout=30,
            description="Execute AppleScript",
        )

    def execute_with_result(self, script: str) -> str | None:
        """Execute AppleScript and return the output string.

        Note: This runs even in dry-run mode since it's a read-only query.

        Args:
            script: AppleScript code to execute

        Returns:
            Script output if successful, None otherwise
        """
        if not self.is_macos:
            logger.warning("AppleScript not available on this platform")
            return None

        if self.dry_run:
            logger.debug("DRY RUN - Executing query AppleScript:")
            logger.debug(script)

        return self.command_service.execute_r_with_output(
            ["osascript", "-e", script],
            timeout=30,
            description="Execute AppleScript for output",
        )

    def escape_string(self, text: str) -> str:
        """Escape text for use in AppleScript strings.

        Args:
            text: Text to escape

        Returns:
            Escaped text safe for AppleScript string literals
        """
        return text.replace("\\", "\\\\").replace('"', '\\"')

    def escape_path(self, path: Path) -> str:
        """Escape a path for use in AppleScript strings.

        Args:
            path: Path to escape

        Returns:
            Escaped path safe for AppleScript string literals
        """
        return str(path).replace("\\", "\\\\").replace('"', '\\"')
