"""Utility functions for automate-terminal."""

import logging
import shlex
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _run_command_impl(
    cmd: list[str],
    cwd: Path | None = None,
    capture_output: bool = True,
    text: bool = True,
    timeout: int | None = None,
    description: str | None = None,
) -> subprocess.CompletedProcess:
    """Internal implementation for running subprocess commands with debug logging."""
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


def run_command_r(
    cmd: list[str],
    cwd: Path | None = None,
    capture_output: bool = True,
    text: bool = True,
    timeout: int | None = None,
    description: str | None = None,
) -> subprocess.CompletedProcess:
    """Run a read-only subprocess command with debug logging.

    Read-only commands always execute, even in dry-run mode, because they
    query information without making changes (like listing sessions, getting
    working directories, etc.).

    Args:
        cmd: Command and arguments as a list
        cwd: Working directory for command
        capture_output: Whether to capture stdout/stderr
        text: Whether to decode output as text
        timeout: Timeout in seconds
        description: Optional description for logging

    Returns:
        CompletedProcess instance with result
    """
    return _run_command_impl(cmd, cwd, capture_output, text, timeout, description)


def run_command_rw(
    cmd: list[str],
    cwd: Path | None = None,
    capture_output: bool = True,
    text: bool = True,
    timeout: int | None = None,
    description: str | None = None,
    dry_run: bool = False,
) -> subprocess.CompletedProcess:
    """Run a read-write subprocess command that respects dry-run mode.

    Read-write commands are those that make changes (create windows, send keys,
    switch sessions, etc.). In dry-run mode, these commands are logged but not
    executed.

    Args:
        cmd: Command and arguments as a list
        cwd: Working directory for command
        capture_output: Whether to capture stdout/stderr
        text: Whether to decode output as text
        timeout: Timeout in seconds
        description: Optional description for logging
        dry_run: If True, log command instead of executing it

    Returns:
        CompletedProcess instance with result (or mock result in dry-run mode)
    """
    cmd_str = shlex.join(cmd)

    if dry_run:
        logger.info(f"DRY RUN - Would execute: {cmd_str}")
        if cwd:
            logger.info(f"DRY RUN - Working directory: {cwd}")

        # Return a mock successful result
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    return _run_command_impl(cmd, cwd, capture_output, text, timeout, description)
