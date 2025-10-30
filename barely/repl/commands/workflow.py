"""
FILE: barely/repl/commands/workflow.py
PURPOSE: Workflow command handlers for REPL
"""

from ..main import console, repl_context
from ..parser import ParseResult
from ...core import service, repository
from ...core.exceptions import (
    BarelyError,
    TaskNotFoundError,
    InvalidInputError,
)
from ..style import celebrate_pull, celebrate_bulk
from ..undo import record_pull
from ..display import display_tasks_table
from ..pickers import pick_task

# Helper function
def ask_confirmation(message: str) -> bool:
    """Ask user for confirmation (y/n)."""
    response = input(f"{message} (y/n): ").strip().lower()
    return response in ('y', 'yes')

def handle_today_command(result: ParseResult) -> None:
    """
    Handle 'today' command - list today's tasks.

    Args:
        result: Parsed command with args and flags

    Usage:
        today
    """
    try:
        tasks = service.list_today()

        # Filter by context project if set
        if repl_context.current_project:
            tasks = [t for t in tasks if t.project_id == repl_context.current_project.id]

        if not tasks:
            console.print("[dim]No tasks for today[/dim]")
            console.print("[dim]Use 'pull <task_id>' to add tasks[/dim]")
            return

        console.print("[bold cyan]Today's Tasks[/bold cyan]")
        display_tasks_table(tasks, repl_context, console)
    except BarelyError as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def handle_week_command(result: ParseResult) -> None:
    """
    Handle 'week' command - list this week's tasks.

    Args:
        result: Parsed command with args and flags

    Usage:
        week
    """
    try:
        tasks = service.list_week()

        # Filter by context project if set
        if repl_context.current_project:
            tasks = [t for t in tasks if t.project_id == repl_context.current_project.id]

        if not tasks:
            console.print("[dim]No tasks for this week[/dim]")
            console.print("[dim]Use 'pull <task_id> week' to add tasks[/dim]")
            return

        console.print("[bold cyan]This Week's Tasks[/bold cyan]")
        display_tasks_table(tasks, repl_context, console)
    except BarelyError as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def handle_backlog_command(result: ParseResult) -> None:
    """
    Handle 'backlog' command - list backlog tasks.

    Args:
        result: Parsed command with args and flags

    Usage:
        backlog
    """
    try:
        tasks = service.list_backlog()

        # Filter by context project if set
        if repl_context.current_project:
            tasks = [t for t in tasks if t.project_id == repl_context.current_project.id]

        if not tasks:
            console.print("[dim]Backlog is empty[/dim]")
            return

        console.print("[bold cyan]Backlog[/bold cyan]")
        display_tasks_table(tasks, repl_context, console)
    except BarelyError as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def handle_archive_command(result: ParseResult) -> None:
    """
    Handle 'archive' command - view archived/completed tasks.

    Args:
        result: Parsed command with args and flags

    Usage:
        archive
    """
    try:
        tasks = service.list_completed()

        # Filter by context project if set
        if repl_context.current_project:
            tasks = [t for t in tasks if t.project_id == repl_context.current_project.id]

        if not tasks:
            console.print("[dim]No archived tasks[/dim]")
            return

        console.print("[bold cyan]Archive[/bold cyan]")
        display_tasks_table(tasks, repl_context, console)
    except BarelyError as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def handle_pull_command(result: ParseResult) -> None:
    """
    Handle 'pull' command - pull tasks into scope (defaults to today).

    Args:
        result: Parsed command with args and flags

    Usage:
        pull               (shows picker, defaults to today)
        pull 42            (pull task 42 to today)
        pull 1,2,3         (pull multiple to today)
        pull 42 week       (pull task 42 to week)
        pull week          (shows picker for week scope)
        pull *             (pull all tasks in current context to today)
        pull * week        (pull all tasks in current context to week)
    """
    valid_scopes = ("backlog", "week", "today", "archived")

    # No args: show picker, default to today
    if not result.args:
        scope = "today"
        task_ids = pick_task(title=f"Pull task(s) into '{scope}'")
        if task_ids is None:
            return  # User cancelled

    # One arg: could be scope, task IDs, or wildcard
    elif len(result.args) == 1:
        arg = result.args[0].strip()

        # Check for wildcard
        if arg == "*":
            # Pull all tasks in current context to today
            scope = "today"
            all_tasks = service.list_tasks()
            tasks_to_pull = repl_context.filter_tasks(all_tasks)

            # Exclude tasks already in the target scope
            tasks_to_pull = [t for t in tasks_to_pull if t.scope != scope and t.status == "todo"]

            if not tasks_to_pull:
                console.print("[yellow]No tasks to pull in current context[/yellow]")
                return

            # Show what would be pulled
            context_desc = ""
            if repl_context.current_project or repl_context.current_scope:
                parts = []
                if repl_context.current_project:
                    parts.append(f"project '{repl_context.current_project.name}'")
                if repl_context.current_scope:
                    parts.append(f"scope '{repl_context.current_scope}'")
                context_desc = f" from {' and '.join(parts)}"
            else:
                context_desc = " (all tasks)"

            # Confirm pull
            if not ask_confirmation(f"Pull {len(tasks_to_pull)} tasks{context_desc} into '{scope}'?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

            task_ids = [t.id for t in tasks_to_pull]

        # Check if it's a valid scope
        elif arg.lower() in valid_scopes:
            # It's a scope - show picker
            scope = arg.lower()
            task_ids = pick_task(title=f"Pull task(s) into '{scope}'")
            if task_ids is None:
                return  # User cancelled
        else:
            # Not a scope or wildcard - treat as task ID(s), default to today
            scope = "today"
            try:
                # Parse comma-separated IDs
                ids = [int(id.strip()) for id in arg.split(",")]
                task_ids = ids
            except ValueError:
                console.print(f"[red]Error:[/red] Invalid task ID(s) or scope: '{arg}'")
                console.print("[dim]Usage: pull <task_id>[,<task_id>...] [scope][/dim]")
                console.print(f"[dim]Valid scopes: {', '.join(valid_scopes)} (defaults to 'today')[/dim]")
                return

    # Two args: pull <ids|*> <scope>
    else:
        arg = result.args[0].strip()

        # Scope is second arg
        scope = result.args[1].lower()

        # Validate scope
        if scope not in valid_scopes:
            console.print(f"[red]Error:[/red] Invalid scope '{scope}'")
            console.print(f"[dim]Valid scopes: {', '.join(valid_scopes)}[/dim]")
            return

        # Check for wildcard
        if arg == "*":
            # Pull all tasks in current context to specified scope
            all_tasks = service.list_tasks()
            tasks_to_pull = repl_context.filter_tasks(all_tasks)

            # Exclude tasks already in the target scope
            tasks_to_pull = [t for t in tasks_to_pull if t.scope != scope and t.status == "todo"]

            if not tasks_to_pull:
                console.print(f"[yellow]No tasks to pull in current context[/yellow]")
                return

            # Show what would be pulled
            context_desc = ""
            if repl_context.current_project or repl_context.current_scope:
                parts = []
                if repl_context.current_project:
                    parts.append(f"project '{repl_context.current_project.name}'")
                if repl_context.current_scope:
                    parts.append(f"scope '{repl_context.current_scope}'")
                context_desc = f" from {' and '.join(parts)}"
            else:
                context_desc = " (all tasks)"

            # Confirm pull
            if not ask_confirmation(f"Pull {len(tasks_to_pull)} tasks{context_desc} into '{scope}'?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

            task_ids = [t.id for t in tasks_to_pull]
        else:
            # Parse comma-separated IDs from first arg
            try:
                ids = [int(id.strip()) for id in arg.split(",")]
                task_ids = ids
            except ValueError:
                console.print(f"[red]Error:[/red] Invalid task ID(s): '{arg}'")
                return

    # Pull tasks (common path for all branches)
    pulled_count = 0
    scope_emoji = {"backlog": "📋", "week": "📅", "today": "⭐", "archived": "✓"}

    for task_id in task_ids:
        try:
            # Get original scope before pull (for undo)
            original_task = repository.get_task(task_id)
            original_scope = original_task.scope if original_task else "backlog"
            
            task = service.pull_task(task_id, scope)
            
            # Record for undo (only track last operation)
            record_pull(task_id, original_scope, scope)
            
            celebrate_pull()
            console.print(
                f"[blue]{scope_emoji.get(scope, '→')}[/blue] "
                f"Pulled task {task.id} into [cyan]{scope}[/cyan]: {task.title}"
            )
            pulled_count += 1
        except TaskNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
        except InvalidInputError as e:
            console.print(f"[red]Error:[/red] {e}")
        except BarelyError as e:
            console.print(f"[red]Error:[/red] {e}")

    if pulled_count > 1:
        bulk_msg = celebrate_bulk(pulled_count, f"pulled into {scope}")
        console.print(f"[green]{bulk_msg}[/green]")


