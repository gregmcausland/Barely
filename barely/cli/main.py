"""
FILE: barely/cli/main.py
PURPOSE: Typer-based CLI for one-shot task management commands
EXPORTS:
  - app (Typer application)
  - main() (entry point)
  - version() - Show version
  - help() - Show command list and usage
  - repl() - Launch interactive REPL
  - blitz() - Launch blitz mode (focused task completion)
  - add() - Create task
  - ls() - List tasks
  - done() - Complete task
  - rm() - Delete task
  - edit() - Update task title
  - desc() - Edit task description in $EDITOR
  - show() - View full task details
  - archive() - View archived/completed tasks
  - mv() - Move task to column
  - assign() - Assign task to project
  - today() - List today's tasks
  - week() - List this week's tasks
  - backlog() - List backlog tasks
  - pull() - Pull tasks into scope (backlog/week/today)
  - project_add() - Create project
  - project_ls() - List projects
  - project_rm() - Delete project
DEPENDENCIES:
  - typer (CLI framework)
  - rich (formatted output)
  - barely.core.service (business logic)
  - barely.core.exceptions (error handling)
  - barely.repl (interactive mode)
  - barely.core.repository (for column/project lookup by name)
NOTES:
  - All commands support --json and --raw flags
  - Error messages go to stderr
  - Exit codes: 0=success, 1=error
  - Calls service layer directly (no repository access except column/project name lookup)
"""

import sys
import json
from typing import Optional

# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import typer
from rich.console import Console
from rich.table import Table

from ..core import service, repository
from ..core.exceptions import (
    BarelyError,
    TaskNotFoundError,
    ProjectNotFoundError,
    ColumnNotFoundError,
    InvalidInputError,
)
from ..utils import improve_title_with_ai

# Typer app setup
app = typer.Typer(
    name="barely",
    help="Minimalist terminal-native task manager",
    add_completion=False,
)

# Project sub-command group
project_app = typer.Typer(
    name="project",
    help="Project management commands",
)
app.add_typer(project_app, name="project")

# Rich console for formatted output
console = Console()
error_console = Console(stderr=True)

# Version
__version__ = "0.3.0"


@app.callback(invoke_without_command=True)
def default_command(ctx: typer.Context):
    """
    Default callback - launches REPL when no command is specified.

    If a subcommand is invoked, this does nothing.
    If no subcommand is invoked (just 'barely'), launch the REPL.
    """
    if ctx.invoked_subcommand is None:
        # No command specified, launch REPL
        from ..repl import main as repl_main
        try:
            repl_main()
        except Exception as e:
            error_console.print(f"[red]Error starting REPL:[/red] {e}")
            raise typer.Exit(1)


# Import command modules to register commands with app
# Commands are decorated with @app.command() in their modules
from .commands import (
    # System commands
    version,
    help,
    repl,
    blitz,
    # Task commands
    add,
    ls,
    done,
    rm,
    edit,
    desc,
    show,
    mv,
    assign,
    # Workflow commands
    today,
    week,
    backlog,
    archive,
    pull,
    # Project commands
    project_add,
    project_ls,
    project_rm,
)


# Commands are now imported from command modules above
# Old command definitions removed - see commands/ directory


def main():
    """Main entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
