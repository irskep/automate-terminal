"""AppleScript execution service with dry-run support."""

import logging
import platform

from automate_terminal.utils import run_command

logger = logging.getLogger(__name__)


class AppleScriptService:
    """Service for executing AppleScript with optional dry-run mode."""

    def __init__(self, dry_run: bool = False):
        """Initialize AppleScript service.

        Args:
            dry_run: If True, log scripts instead of executing them
        """
        self.dry_run = dry_run
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

        try:
            result = run_command(
                ["osascript", "-e", script],
                timeout=30,
                description="Execute AppleScript",
            )

            success = result.returncode == 0
            if success:
                logger.debug("AppleScript executed successfully")
            else:
                logger.error(f"AppleScript failed: {result.stderr}")

            return success

        except Exception as e:
            logger.error(f"Failed to run AppleScript: {e}")
            return False

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

        try:
            result = run_command(
                ["osascript", "-e", script],
                timeout=30,
                description="Execute AppleScript for output",
            )

            if result.returncode != 0:
                logger.error(f"AppleScript failed: {result.stderr}")
                return None

            return result.stdout.strip()

        except Exception as e:
            logger.error(f"Failed to run AppleScript: {e}")
            return None
