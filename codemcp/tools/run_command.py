#!/usr/bin/env python3

import shlex
from typing import List, Optional, Union

from .code_command import get_command_from_config, run_code_command

__all__ = [
    "run_command",
]


async def run_command(
    project_dir: str,
    command: str,
    arguments: Optional[Union[List[str], str]] = None,
    chat_id: str = None,
) -> str:
    """Run a command that is configured in codemcp.toml.

    Args:
        project_dir: The directory path containing the codemcp.toml file
        command: The type of command to run (e.g., "format", "lint", "test")
        arguments: Optional arguments to pass to the command. If a single string is
                  provided, it will be parsed into a list of arguments using shell-style
                  tokenization (spaces separate arguments, quotes can be used for arguments
                  containing spaces, etc.)
        chat_id: The unique ID of the current chat session

    Returns:
        A string containing the result of the command operation
    """
    command_list = get_command_from_config(project_dir, command)

    # If arguments are provided, extend the command with them
    if arguments and command_list:
        command_list = command_list.copy()

        # If a single string is provided, parse it into a list of arguments
        if isinstance(arguments, str):
            parsed_args = shlex.split(arguments)
            command_list.extend(parsed_args)
        else:
            command_list.extend(arguments)

    return await run_code_command(
        project_dir, command, command_list, f"Auto-commit {command} changes", chat_id
    )
