"""Command execution service with testability."""

import logging

from automate_terminal.utils import run_command

logger = logging.getLogger(__name__)


class CommandService:
    """Service for executing shell commands."""

    def execute(
        self, cmd: list[str], timeout: int = 10, description: str | None = None
    ) -> bool:
        """Execute a shell command and return success status.

        Args:
            cmd: Command and arguments as a list
            timeout: Timeout in seconds
            description: Optional description for logging

        Returns:
            True if command succeeded (exit code 0), False otherwise
        """
        try:
            result = run_command(
                cmd,
                timeout=timeout,
                description=description,
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to run command {cmd}: {e}")
            return False
