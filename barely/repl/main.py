"""
FILE: barely/repl/main.py
PURPOSE: Interactive REPL for task management with prompt-toolkit
EXPORTS:
  - main() - Entry point for REPL mode
  - run_repl() - Main REPL loop
DEPENDENCIES:
  - prompt_toolkit (REPL interface, history, completion)
  - rich (formatted output)
  - barely.core.service (business logic)
  - barely.core.exceptions (error handling)
  - barely.repl.parser (command parsing)
  - barely.repl.completer (autocomplete)
NOTES:
  - Uses prompt_toolkit for readline-like features
  - Command history automatic with PromptSession
  - Bottom toolbar shows task counts and rotating tips
  - Right prompt shows filtered task count in context
  - Ctrl+D or "exit"/"quit" to exit
  - Calls service layer directly (not CLI layer)
  - Rich formatting for tables and messages
"""

import sys
from dataclasses import dataclass
from typing import Optional, List

# Fix Windows console encoding for Unicode characters
# Only wrap if not already wrapped to prevent issues
if sys.platform == "win32":
    import io
    if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        except (AttributeError, ValueError):
            pass  # Already wrapped or unavailable
    if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except (AttributeError, ValueError):
            pass  # Already wrapped or unavailable

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.input import create_input
from prompt_toolkit.output import create_output
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..core import service, repository
from ..core.exceptions import (
    BarelyError,
    TaskNotFoundError,
    ProjectNotFoundError,
    ColumnNotFoundError,
    InvalidInputError,
)
from ..core.models import Task, Project
from ..utils import improve_title_with_ai
from .parser import parse_command, ParseResult
from .completer import create_completer
from . import style
from . import blitz
from . import undo


# Rich console for formatted output
console = Console()


# --- REPL Context (Persistent State) ---


@dataclass
class REPLContext:
    """
    Persistent context for the REPL session.

    Maintains current working project and scope filter.
    All commands respect this context unless explicitly overridden.

    Attributes:
        current_project: Currently selected project (or None for all)
        current_scope: Current scope filter ('today', 'week', 'backlog', 'archived', or None for all)
    """
    current_project: Optional[Project] = None
    current_scope: Optional[str] = None

    def get_prompt(self) -> str:
        """
        Generate prompt string based on current context.

        Returns:
            Prompt like "barely> " or "barely:[work]> " or "barely:[work|today]> "
        """
        parts = []

        if self.current_project:
            parts.append(self.current_project.name)

        if self.current_scope:
            parts.append(self.current_scope)

        if parts:
            context_str = " | ".join(parts)
            return f"barely:[{context_str}]> "

        return "barely> "

    def filter_tasks(self, tasks: List[Task]) -> List[Task]:
        """
        Filter tasks based on current context.

        Args:
            tasks: List of tasks to filter

        Returns:
            Filtered task list based on current project and scope
        """
        filtered = tasks

        # Filter by project if set
        if self.current_project:
            filtered = [t for t in filtered if t.project_id == self.current_project.id]

        # Filter by scope if set
        if self.current_scope:
            filtered = [t for t in filtered if t.scope == self.current_scope]

        return filtered


# Global REPL context (persists during session, resets on restart)
repl_context = REPLContext()


def format_prompt() -> HTML:
    """
    Create formatted prompt text with context and colors.

    Returns:
        HTML formatted prompt: "barely> " or "barely:[project | scope]> "
        with cyan project and magenta scope
    """
    parts = []

    if repl_context.current_project:
        parts.append(f'<cyan>{repl_context.current_project.name}</cyan>')

    if repl_context.current_scope:
        # Color code scope like in tables
        scope_colors = {
            "today": "ansibrightmagenta",
            "week": "ansiblue",
            "backlog": "ansigray"
        }
        scope_color = scope_colors.get(repl_context.current_scope, "white")
        parts.append(f'<{scope_color}>{repl_context.current_scope}</{scope_color}>')

    if parts:
        context_str = " | ".join(parts)
        return HTML(f"<b>barely:[{context_str}]&gt; </b>")

    return HTML("<b>barely&gt; </b>")


# Rotating tips for bottom toolbar
_TOOLBAR_TIPS = [
    "💡 Tip: Use 'done' without ID to get an interactive picker",
    "💡 Tip: Use 'use <project>' to set working context",
    "💡 Tip: Use 'scope today' to filter to today's tasks",
    "💡 Tip: Comma-separate IDs for bulk operations (e.g., 'done 1,2,3')",
    "💡 Tip: Press Ctrl+D or type 'exit' to quit",
    "💡 Tip: Use 'pull <id>' to move tasks into today",
    "💡 Tip: Type 'help' to see all available commands",
]
_tip_index = 0


def get_bottom_toolbar() -> HTML:
    """
    Create bottom toolbar showing task counts and rotating tips.

    Returns:
        HTML formatted toolbar with stats and tips
    """
    global _tip_index

    try:
        # Get task counts per scope
        today_count = len(service.list_today())
        week_count = len(service.list_week())
        backlog_count = len(service.list_backlog())

        # Get current tip
        tip = _TOOLBAR_TIPS[_tip_index % len(_TOOLBAR_TIPS)]

        # Build toolbar string
        stats = f"⭐ {today_count} today | 📅 {week_count} week | 📋 {backlog_count} backlog"
        toolbar_text = f"{stats} | {tip}"

        return HTML(f"<style bg='#444444' fg='#ffffff'> {toolbar_text} </style>")
    except Exception:
        # Fallback if there's an error
        return HTML("<style bg='#444444' fg='#ffffff'> Barely Task Manager </style>")


def get_right_prompt() -> HTML:
    """
    Create right prompt showing task count in current context.

    Returns:
        HTML formatted right prompt with filtered task count
    """
    try:
        # Get all tasks and filter by context
        tasks = service.list_tasks()
        filtered = repl_context.filter_tasks(tasks)

        if repl_context.current_project or repl_context.current_scope:
            count = len(filtered)
            return HTML(f"<style fg='#888888'>[{count} in view]</style>")
        else:
            # If no filter, show total
            total = len(tasks)
            return HTML(f"<style fg='#888888'>[{total} total]</style>")
    except Exception:
        return HTML("")


# Import command handlers from command modules
from .commands import (
    # Task handlers
    handle_add_command,
    handle_ls_command,
    handle_done_command,
    handle_rm_command,
    handle_edit_command,
    handle_desc_command,
    handle_show_command,
    handle_mv_command,
    handle_assign_command,
    # Workflow handlers
    handle_today_command,
    handle_week_command,
    handle_backlog_command,
    handle_archive_command,
    handle_pull_command,
    # Project handlers
    handle_use_command,
    handle_project_add_command,
    handle_project_ls_command,
    handle_project_rm_command,
    handle_project_command,
    # System handlers
    handle_help_command,
    handle_clear_command,
    handle_blitz_command,
    handle_undo_command,
    handle_scope_command,
)


# Import display functions from display module to avoid circular imports
from .display import display_task as _display_task, display_tasks_table as _display_tasks_table

# Re-export for backward compatibility (wrapper functions that use module-level repl_context)
def display_task(task: Task, message: str = "") -> None:
    """Wrapper that uses module-level console."""
    _display_task(task, message, console)


def display_tasks_table(tasks: list[Task]) -> None:
    """Wrapper that uses module-level repl_context and console."""
    _display_tasks_table(tasks, repl_context, console)


from .pickers import pick_task


def execute_command(result: ParseResult) -> bool:
    """
    Execute a parsed command.

    Args:
        result: Parsed command from parser

    Returns:
        True to continue REPL loop, False to exit

    Dispatches to appropriate handler based on command name.
    """
    command = result.command.lower()

    # Exit commands
    if command in ("exit", "quit"):
        console.print("[dim]Goodbye![/dim]")
        return False

    # Empty command (just Enter pressed)
    if not command:
        return True

    # Dispatch to command handlers
    handlers = {
        "add": handle_add_command,
        "ls": handle_ls_command,
        "done": handle_done_command,
        "rm": handle_rm_command,
        "edit": handle_edit_command,
        "desc": handle_desc_command,
        "show": handle_show_command,
        "view": handle_show_command,
        "mv": handle_mv_command,
        "assign": handle_assign_command,
        "today": handle_today_command,
        "week": handle_week_command,
        "backlog": handle_backlog_command,
        "archive": handle_archive_command,
        "pull": handle_pull_command,
        "use": handle_use_command,
        "scope": handle_scope_command,
        "project": handle_project_command,
        "blitz": handle_blitz_command,
        "help": handle_help_command,
        "clear": handle_clear_command,
        "undo": handle_undo_command,
    }

    handler = handlers.get(command)
    if handler:
        handler(result)
        # Add whitespace after command output for readability
        console.print()
    else:
        console.print(f"[red]Unknown command:[/red] {command}")
        console.print("[dim]Type 'help' for available commands[/dim]")
        console.print()

    return True


def run_repl() -> None:
    """
    Main REPL loop.

    Sets up prompt_toolkit session with:
    - Command history (in-memory, not persisted)
    - Autocomplete (commands, flags)
    - Custom prompt formatting

    Exits on:
    - Ctrl+D (EOFError)
    - Ctrl+C (KeyboardInterrupt)
    - "exit" or "quit" commands
    """
    # Check if we have a proper TTY
    # In piped/test environments, skip prompt_toolkit entirely
    import os
    has_tty = sys.stdin.isatty() and sys.stdout.isatty()

    session = None
    use_simple_input = not has_tty

    if has_tty:
        # Create prompt session with history and autocomplete
        history = InMemoryHistory()
        completer = create_completer()

        try:
            # Try to create a proper session with terminal support
            session = PromptSession(
                history=history,
                completer=completer,
                complete_while_typing=True,
                bottom_toolbar=get_bottom_toolbar,
                rprompt=get_right_prompt,
            )
        except Exception as e:
            # Fallback to simple input if prompt_toolkit fails
            console.print(f"[yellow]Warning:[/yellow] Running in simple input mode: {e}")
            use_simple_input = True

    # Welcome message
    console.print("[bold cyan]Barely REPL[/bold cyan] - Type 'help' for commands, 'exit' to quit")
    if use_simple_input:
        console.print("[dim](Running in simple mode - no autocomplete)[/dim]")
    console.print()

    # Main REPL loop
    while True:
        try:
            # Get user input
            if use_simple_input or session is None:
                # Use simple input() for non-TTY or when prompt_toolkit failed
                user_input = input(repl_context.get_prompt())
            else:
                try:
                    user_input = session.prompt(format_prompt())
                except Exception as e:
                    # If prompt fails, switch to simple mode
                    console.print(f"[yellow]Switching to simple input mode: {e}[/yellow]")
                    use_simple_input = True
                    user_input = input(repl_context.get_prompt())

            # Parse command
            result = parse_command(user_input)

            # Execute command (returns False to exit)
            if not execute_command(result):
                break

            # Rotate tip after each command
            global _tip_index
            _tip_index += 1

        except KeyboardInterrupt:
            # Ctrl+C - show message and continue
            console.print("[dim]^C (Press Ctrl+D or type 'exit' to quit)[/dim]")
            continue
        except EOFError:
            # Ctrl+D or end of input - exit cleanly
            console.print()
            console.print("[dim]Goodbye![/dim]")
            break
        except Exception as e:
            # Unexpected error - show but don't crash
            console.print(f"[red]Unexpected error:[/red] {e}")
            import traceback
            console.print("[dim]" + traceback.format_exc() + "[/dim]")


def main() -> None:
    """
    Entry point for REPL mode.

    Called when user runs: barely repl
    """
    try:
        run_repl()
    except Exception as e:
        console.print(f"[red]Fatal error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
