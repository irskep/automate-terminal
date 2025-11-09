"""CLI for automate-terminal."""

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path

from automate_terminal import __version__
from automate_terminal.applescript_service import AppleScriptService
from automate_terminal.command_service import CommandService
from automate_terminal.terminal_service import (
    EMPTY_CAPABILITIES,
    TerminalNotFoundError,
    TerminalService,
)

logger = logging.getLogger(__name__)


def setup_logging(debug: bool = False, dry_run: bool = False):
    """Setup logging configuration."""
    if debug:
        level = logging.DEBUG
    elif dry_run:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(
        level=level, format="%(name)s: %(levelname)s: %(message)s", stream=sys.stderr
    )


def output(fmt: str, data: dict, text: str):
    if fmt == "json":
        print(json.dumps(data, indent=2))
    elif fmt == "text":
        print(text)
    elif fmt == "none":
        pass
    else:
        raise ValueError("Unknown output format: %s", fmt)


def astext(dataclass_instance, indent: int = 0) -> str:
    """Convert a dataclass to indented text output.

    Args:
        dataclass_instance: Dataclass instance to convert
        indent: Number of spaces to prefix each line

    Returns:
        Multi-line string with key-value pairs
    """
    data = asdict(dataclass_instance)
    prefix = " " * indent
    lines = [f"{prefix}{key}: {value}" for key, value in data.items()]
    return "\n".join(lines)


def output_error(message: str, output_format: str = "text", **extra_data):
    """Output error message to stderr.

    Args:
        message: Error message
        output_format: Output format (json, text, none)
        **extra_data: Additional fields to include in JSON output
    """
    if output_format == "json":
        data = {"success": False, "error": message}
        data.update(extra_data)
        print(json.dumps(data, indent=2), file=sys.stderr)
    elif output_format == "text":
        print(f"Error: {message}", file=sys.stderr)


def _get_terminal_service(args) -> TerminalService | None:
    """Create terminal service, handling errors.

    Args:
        args: Parsed command-line arguments

    Returns:
        TerminalService instance or None if terminal not supported
    """
    try:
        dry_run = getattr(args, "dry_run", False)
        command_service = CommandService(dry_run=dry_run)
        applescript_service = AppleScriptService(command_service)
        return TerminalService(applescript_service)
    except TerminalNotFoundError:
        output_error("Terminal not supported", args.output)
        return None


def get_paste_script(args, service: TerminalService) -> str | None:
    """Get the appropriate paste script based on shell detection and args."""
    shell_name = service.get_shell_name()

    # Check shell-specific flags first
    shell_specific_map = {
        "bash": args.paste_and_run_bash,
        "zsh": args.paste_and_run_zsh,
        "fish": args.paste_and_run_fish,
        "powershell": args.paste_and_run_powershell,
        "nushell": args.paste_and_run_nushell,
    }

    scripts: list[str] = []

    if shell_name and shell_name in shell_specific_map:
        shell_specific = shell_specific_map[shell_name]
        if shell_specific:
            scripts.append(shell_specific)

    if args.paste_and_run:
        scripts.append(args.paste_and_run)

    if not scripts:
        return None

    # semicolon works for bash, zsh, fish, powershell, nushell, and most shells
    return "; ".join(scripts)


def will_paste_script_execute(
    paste_script: str | None, service: TerminalService
) -> bool | None:
    """Determine if the paste script will be executed.

    Returns:
        True if paste script will be executed
        False if paste script was provided but terminal doesn't support it
        None if no paste script was provided
    """
    if paste_script is None:
        return None

    caps = service.get_capabilities()
    return caps.can_paste_commands


def cmd_check(args):
    """Check terminal capabilities."""
    service = _get_terminal_service(args)
    if not service:
        # For check command, provide more detailed error info
        term_program = os.getenv("TERM_PROGRAM", "unknown")

        data = {
            "terminal": "unknown",
            "term_program": term_program,
            "shell": "unknown",
            "current_session_id": None,
            "current_working_directory": str(Path.cwd()),
            "capabilities": asdict(EMPTY_CAPABILITIES),
            "error": f"Terminal '{term_program}' is not supported",
        }

        text = (
            f"Error: Terminal '{term_program}' is not supported\n"
            f"Supported terminals: iTerm2, Terminal.app, Ghostty (macOS only)"
        )

        output(args.output, data, text)
        return 1

    # Get capabilities
    caps = service.get_capabilities()

    override = os.getenv("AUTOMATE_TERMINAL_OVERRIDE")
    data = {
        "terminal": service.get_terminal_name(),
        "term_program": os.getenv("TERM_PROGRAM", ""),
        "shell": service.get_shell_name() or "unknown",
        "current_session_id": service.get_current_session_id(),
        "current_working_directory": str(Path.cwd()),
        "capabilities": asdict(caps),
        "version": __version__,
    }
    if override:
        data["override"] = override

    text_lines = [
        f"Terminal: {data['terminal']}"
        + (f" (overridden: {override})" if override else ""),
        f"Terminal Program: {data['term_program']}",
        f"Shell: {data['shell']}",
        f"Current session ID: {data['current_session_id'] or 'N/A'}",
        f"Current working directory: {data['current_working_directory']}",
        "",
        "Capabilities:",
        astext(caps, indent=2),
    ]
    text = "\n".join(text_lines)

    output(args.output, data, text)
    return 0


def cmd_switch_to(args):
    """Switch to existing session."""
    service = _get_terminal_service(args)
    if not service:
        return 1

    session_id = args.session_id
    working_directory = Path(args.working_directory) if args.working_directory else None

    if not session_id and not working_directory:
        output_error("Must provide --session-id or --working-directory", args.output)
        return 1

    paste_script = get_paste_script(args, service)
    subdirectory_ok = getattr(args, "subdirectory_ok", False)

    try:
        success = service.switch_to_session(
            session_id=session_id,
            working_directory=working_directory,
            paste_script=paste_script,
            subdirectory_ok=subdirectory_ok,
        )

        if success:
            paste_executed = will_paste_script_execute(paste_script, service)
            data = {
                "success": True,
                "action": "switched_to_existing",
                "terminal": service.get_terminal_name(),
                "shell": service.get_shell_name(),
            }
            if session_id:
                data["session_id"] = session_id
            if working_directory:
                data["working_directory"] = str(working_directory)
            if paste_executed is not None:
                data["paste_script_executed"] = paste_executed

            output(args.output, data, "Switched to existing session")
            return 0
        else:
            # Check if subdirectories exist when exact match failed
            error_msg = "No matching session found"
            if not subdirectory_ok and working_directory:
                found_in_subdir = service.find_session_by_directory(
                    working_directory, subdirectory_ok=True
                )
                if found_in_subdir:
                    error_msg = f"No session found in {working_directory}, but sessions exist in subdirectories. Use --subdirectory-ok to match them."

            output_error(
                error_msg,
                args.output,
                terminal=service.get_terminal_name(),
            )
            return 1

    except RuntimeError as e:
        output_error(str(e), args.output)
        return 1


def cmd_new_tab(args):
    """Create new tab."""
    service = _get_terminal_service(args)
    if not service:
        return 1

    working_directory = Path(args.working_directory)
    paste_script = get_paste_script(args, service)

    try:
        success = service.new_tab(working_directory, paste_script)

        if success:
            paste_executed = will_paste_script_execute(paste_script, service)
            data = {
                "success": True,
                "action": "created_new_tab",
                "working_directory": str(working_directory),
                "terminal": service.get_terminal_name(),
                "shell": service.get_shell_name(),
            }
            if paste_executed is not None:
                data["paste_script_executed"] = paste_executed

            output(args.output, data, f"Created new tab in {working_directory}")
            return 0
        else:
            output_error(
                "Failed to create tab",
                args.output,
                terminal=service.get_terminal_name(),
            )
            return 1

    except RuntimeError as e:
        output_error(str(e), args.output)
        return 1


def cmd_new_window(args):
    """Create new window."""
    service = _get_terminal_service(args)
    if not service:
        return 1

    working_directory = Path(args.working_directory)
    paste_script = get_paste_script(args, service)

    try:
        success = service.new_window(working_directory, paste_script)

        if success:
            paste_executed = will_paste_script_execute(paste_script, service)
            data = {
                "success": True,
                "action": "created_new_window",
                "working_directory": str(working_directory),
                "terminal": service.get_terminal_name(),
                "shell": service.get_shell_name(),
            }
            if paste_executed is not None:
                data["paste_script_executed"] = paste_executed

            output(args.output, data, f"Created new window in {working_directory}")
            return 0
        else:
            output_error(
                "Failed to create window",
                args.output,
                terminal=service.get_terminal_name(),
            )
            return 1

    except RuntimeError as e:
        output_error(str(e), args.output)
        return 1


def cmd_list_sessions(args):
    """List all sessions."""
    service = _get_terminal_service(args)
    if not service:
        return 1

    try:
        sessions = service.list_sessions()

        data = {"terminal": service.get_terminal_name(), "sessions": sessions}

        lines = [f"{service.get_terminal_name()} Sessions:"]
        for session in sessions:
            components = []
            if "session_id" in session:
                session_id = session["session_id"]
                components.append(f"{session_id} ->")
            if "working_directory" in session:
                components.append(session["working_directory"])
            if "shell" in session:
                shell = session["shell"]
                components.append(f"({shell})")
            if components:
                lines.append(" ".join(components))
            else:
                lines.append("(unknown)")

        text = "\n".join(lines)

        output(args.output, data, text)
        return 0

    except RuntimeError as e:
        output_error(str(e), args.output)
        return 1


def cmd_run_in_active_session(args):
    """Run command in active session."""
    service = _get_terminal_service(args)
    if not service:
        return 1

    command = args.script

    try:
        success = service.run_in_active_session(command)

        if success:
            data = {
                "success": True,
                "terminal": service.get_terminal_name(),
                "command": command,
            }

            output(args.output, data, "Command sent to active session")
            return 0
        else:
            output_error(
                "Failed to run command in active session",
                args.output,
                terminal=service.get_terminal_name(),
            )
            return 1

    except RuntimeError as e:
        output_error(str(e), args.output)
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="automate-terminal",
        description="Programmatic terminal automation for macOS",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Common arguments for all commands
    def add_common_args(subparser):
        subparser.add_argument(
            "--output",
            choices=["json", "text", "none"],
            default="text",
            help="Output format (default: text)",
        )
        subparser.add_argument(
            "--debug", action="store_true", help="Enable debug logging"
        )
        subparser.add_argument(
            "--dry-run",
            action="store_true",
            help="Log actions instead of executing them",
        )

    # Common arguments for paste-and-run
    def add_paste_args(subparser):
        subparser.add_argument("--paste-and-run", help="Shell-agnostic script to paste")
        subparser.add_argument("--paste-and-run-bash", help="Bash-specific script")
        subparser.add_argument("--paste-and-run-zsh", help="Zsh-specific script")
        subparser.add_argument("--paste-and-run-fish", help="Fish-specific script")
        subparser.add_argument(
            "--paste-and-run-powershell", help="PowerShell-specific script"
        )
        subparser.add_argument(
            "--paste-and-run-nushell", help="Nushell-specific script"
        )

    # check command
    check_parser = subparsers.add_parser("check", help="Check terminal capabilities")
    check_parser.add_argument(
        "--output",
        choices=["json", "text", "none"],
        default="text",
        help="Output format (default: text)",
    )
    check_parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )

    # switch-to command
    switch_parser = subparsers.add_parser(
        "switch-to", help="Switch to existing session"
    )
    add_common_args(switch_parser)
    add_paste_args(switch_parser)
    switch_parser.add_argument(
        "--session-id", "--id", dest="session_id", help="Target session ID"
    )
    switch_parser.add_argument(
        "--working-directory",
        "--wd",
        dest="working_directory",
        help="Target working directory",
    )
    switch_parser.add_argument(
        "--subdirectory-ok",
        action="store_true",
        help="Allow matching sessions in subdirectories of target directory",
    )

    # new-tab command
    tab_parser = subparsers.add_parser("new-tab", help="Create new tab")
    add_common_args(tab_parser)
    add_paste_args(tab_parser)
    tab_parser.add_argument("working_directory", help="Working directory for new tab")

    # new-window command
    window_parser = subparsers.add_parser("new-window", help="Create new window")
    add_common_args(window_parser)
    add_paste_args(window_parser)
    window_parser.add_argument(
        "working_directory", help="Working directory for new window"
    )

    # list-sessions command
    list_parser = subparsers.add_parser("list-sessions", help="List all sessions")
    add_common_args(list_parser)

    # run-in-active-session command
    run_parser = subparsers.add_parser(
        "run-in-active-session", help="Run command in active session"
    )
    add_common_args(run_parser)
    run_parser.add_argument("script", help="Command to run in active session")

    args = parser.parse_args()

    # Setup logging
    setup_logging(
        debug=args.debug if hasattr(args, "debug") else False,
        dry_run=args.dry_run if hasattr(args, "dry_run") else False,
    )

    # Execute command
    if args.command == "check":
        return cmd_check(args)
    elif args.command == "switch-to":
        return cmd_switch_to(args)
    elif args.command == "new-tab":
        return cmd_new_tab(args)
    elif args.command == "new-window":
        return cmd_new_window(args)
    elif args.command == "list-sessions":
        return cmd_list_sessions(args)
    elif args.command == "run-in-active-session":
        return cmd_run_in_active_session(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
