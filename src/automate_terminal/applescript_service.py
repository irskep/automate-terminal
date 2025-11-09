import logging
import platform
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from automate_terminal.command_service import CommandService

logger = logging.getLogger(__name__)


class AppleScriptService:
    def __init__(self, command_service: "CommandService"):
        self.command_service = command_service
        self.dry_run = command_service.dry_run
        self.is_macos = platform.system() == "Darwin"

    def execute(self, script: str) -> bool:
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

    def escape(self, val: str | Path) -> str:
        return str(val).replace("\\", "\\\\").replace('"', '\\"')
