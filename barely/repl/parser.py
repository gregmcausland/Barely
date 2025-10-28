"""
FILE: barely/repl/parser.py
PURPOSE: Parse user input into commands and arguments for REPL
EXPORTS:
  - ParseResult (dataclass for parsed commands)
  - parse_command(input_str) -> ParseResult
DEPENDENCIES:
  - shlex (for shell-like parsing with quotes)
  - dataclasses (for ParseResult)
  - typing (type hints)
NOTES:
  - Handles quoted strings: add "task with spaces"
  - Supports flags: --json, --raw, --status todo
  - Preserves argument order for positional args
  - Case-insensitive command names
"""

import shlex
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class ParseResult:
    """
    Result of parsing a REPL command.

    Attributes:
        command: The command name (e.g., "add", "ls", "done")
        args: Positional arguments (e.g., ["task title", "123"])
        flags: Flag arguments as dict (e.g., {"status": "todo", "json": True})
        raw_input: Original input string
    """
    command: str
    args: List[str] = field(default_factory=list)
    flags: Dict[str, str | bool] = field(default_factory=dict)
    raw_input: str = ""


def parse_command(input_str: str) -> ParseResult:
    """
    Parse REPL input into command, args, and flags.

    Examples:
        >>> parse_command("add Buy milk")
        ParseResult(command="add", args=["Buy milk"], flags={})

        >>> parse_command('add "Task with spaces"')
        ParseResult(command="add", args=["Task with spaces"], flags={})

        >>> parse_command("ls --status todo")
        ParseResult(command="ls", args=[], flags={"status": "todo"})

        >>> parse_command("done 42")
        ParseResult(command="done", args=["42"], flags={})

        >>> parse_command("ls --json")
        ParseResult(command="ls", args=[], flags={"json": True})

    Args:
        input_str: Raw user input from REPL prompt

    Returns:
        ParseResult with command, args, and flags extracted

    Notes:
        - Command is always the first token (case-insensitive)
        - Flags start with -- (e.g., --status, --json)
        - Boolean flags don't need values (--json sets json=True)
        - Value flags expect next token as value (--status todo)
        - Remaining tokens are positional args
        - Quoted strings are treated as single args
        - Empty input returns command="" with no args/flags
    """
    # Handle empty input
    input_str = input_str.strip()
    if not input_str:
        return ParseResult(command="", args=[], flags={}, raw_input=input_str)

    # Use shlex to handle quoted strings properly
    # shlex.split handles: add "task with spaces" --status todo
    try:
        tokens = shlex.split(input_str)
    except ValueError:
        # If parsing fails (e.g., unclosed quote), treat as plain split
        tokens = input_str.split()

    if not tokens:
        return ParseResult(command="", args=[], flags={}, raw_input=input_str)

    # First token is always the command (case-insensitive)
    command = tokens[0].lower()

    # Parse remaining tokens into args and flags
    args = []
    flags = {}
    i = 1

    while i < len(tokens):
        token = tokens[i]

        # Check if this is a flag (starts with --)
        if token.startswith("--"):
            flag_name = token[2:]  # Remove the --

            # Check if next token is a value or another flag/arg
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                # Next token is the value for this flag
                flag_value = tokens[i + 1]
                flags[flag_name] = flag_value
                i += 2  # Skip both flag and value
            else:
                # Boolean flag (no value)
                flags[flag_name] = True
                i += 1
        else:
            # Regular positional argument
            args.append(token)
            i += 1

    return ParseResult(
        command=command,
        args=args,
        flags=flags,
        raw_input=input_str
    )
