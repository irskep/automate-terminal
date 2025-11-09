import logging
import shlex
import subprocess

logger = logging.getLogger(__name__)


class CommandService:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def execute_r(
        self, cmd: list[str], timeout: int = 30, description: str | None = None
    ) -> bool:
        """Execute a read-only shell command and return success status.

        Read-only commands always execute, even in dry-run mode.
        """
        try:
            result = _run_command_impl(
                cmd,
                timeout=timeout,
                description=description,
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to run command {cmd}: {e}")
            return False

    def execute_r_with_output(
        self, cmd: list[str], timeout: int = 30, description: str | None = None
    ) -> str | None:
        """Execute a read-only shell command and return output string.

        Read-only commands always execute, even in dry-run mode.
        """
        try:
            result = _run_command_impl(
                cmd,
                timeout=timeout,
                description=description,
            )

            if result.returncode != 0:
                logger.error(f"Command failed with exit code {result.returncode}")
                return None

            return result.stdout.strip()

        except Exception as e:
            logger.error(f"Failed to run command {cmd}: {e}")
            return None

    def execute_rw(
        self, cmd: list[str], timeout: int = 30, description: str | None = None
    ) -> bool:
        """Execute a read-write shell command that respects dry-run mode.

        Read-write commands are logged but not executed in dry-run mode.
        """
        try:
            if self.dry_run:
                cmd_str = shlex.join(cmd)
                logger.info(f"DRY RUN - Would execute: {cmd_str}")
                return True

            result = _run_command_impl(
                cmd,
                timeout=timeout,
                description=description,
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to run command {cmd}: {e}")
            return False


def _run_command_impl(
    cmd: list[str],
    timeout: int = 30,
    description: str | None = None,
) -> subprocess.CompletedProcess:
    """Internal implementation for running subprocess commands with debug logging."""
    cmd_str = shlex.join(cmd)

    if description:
        logger.debug(f"{description}: {cmd_str}")
    else:
        logger.debug(f"Running: {cmd_str}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

        if result.returncode == 0:
            logger.debug(f"Command succeeded (exit code: {result.returncode})")
        else:
            if result.stderr and result.stderr.strip():
                logger.warning(
                    f"Command failed (exit code: {result.returncode}): {result.stderr.strip()}"
                )
            else:
                logger.debug(f"Command completed (exit code: {result.returncode})")

        return result

    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout}s: {cmd_str}")
        raise
    except Exception as e:
        logger.error(f"Command failed with exception: {e}")
        raise
