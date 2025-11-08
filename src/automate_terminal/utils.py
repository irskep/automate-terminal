"""Utility functions for automate-terminal."""

import logging
import shlex
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def run_command(
    cmd: list[str],
    cwd: Path | None = None,
    capture_output: bool = True,
    text: bool = True,
    timeout: int | None = None,
    description: str | None = None,
) -> subprocess.CompletedProcess:
    """Run a subprocess command with debug logging."""
    cmd_str = shlex.join(cmd)

    if description:
        logger.debug(f"{description}: {cmd_str}")
    else:
        logger.debug(f"Running: {cmd_str}")

    if cwd:
        logger.debug(f"Working directory: {cwd}")

    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=capture_output, text=text, timeout=timeout
        )

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
