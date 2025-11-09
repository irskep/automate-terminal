"""Command execution service with testability and dry-run support."""

import logging

from automate_terminal.utils import run_command_r, run_command_rw

logger = logging.getLogger(__name__)


class CommandService:
    """Service for executing shell commands with optional dry-run mode."""

    def __init__(self, dry_run: bool = False):
        """Initialize command service.

        Args:
            dry_run: If True, log write commands instead of executing them
        """
        self.dry_run = dry_run

    def execute_r(
        self, cmd: list[str], timeout: int = 10, description: str | None = None
    ) -> bool:
        """Execute a read-only shell command and return success status.

        Read-only commands always execute, even in dry-run mode.

        Args:
            cmd: Command and arguments as a list
            timeout: Timeout in seconds
            description: Optional description for logging

        Returns:
            True if command succeeded (exit code 0), False otherwise
        """
        try:
            result = run_command_r(
                cmd,
                timeout=timeout,
                description=description,
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to run command {cmd}: {e}")
            return False

    def execute_rw(
        self, cmd: list[str], timeout: int = 10, description: str | None = None
    ) -> bool:
        """Execute a read-write shell command that respects dry-run mode.

        Read-write commands are logged but not executed in dry-run mode.

        Args:
            cmd: Command and arguments as a list
            timeout: Timeout in seconds
            description: Optional description for logging

        Returns:
            True if command succeeded (exit code 0), False otherwise
        """
        try:
            result = run_command_rw(
                cmd,
                timeout=timeout,
                description=description,
                dry_run=self.dry_run,
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to run command {cmd}: {e}")
            return False
