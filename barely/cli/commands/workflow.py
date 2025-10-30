"""
FILE: barely/cli/commands/workflow.py
PURPOSE: Workflow commands (today, week, backlog, archive, pull)
"""

import json
from typing import Optional

import typer
from rich.table import Table

from ..main import app, console, error_console
from ...core import service
from ...core.exceptions import (
    BarelyError,
    TaskNotFoundError,
    InvalidInputError,
)

@app.command()
def today(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    List all tasks in today's scope (your daily focus list).

    This shows tasks you've pulled into today for immediate work.

    Example:
        barely today
        barely today --json
    """
    try:
        tasks = service.list_today()

        if json_output:
            # Output as JSON array
            tasks_data = [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "scope": t.scope,
                    "column_id": t.column_id,
                    "project_id": t.project_id,
                    "created_at": t.created_at,
                    "completed_at": t.completed_at,
                    "updated_at": t.updated_at,
                }
                for t in tasks
            ]
            console.print(json.dumps(tasks_data, indent=2))

        elif raw:
            # Plain text, one per line
            for task in tasks:
                status_marker = "✓" if task.scope == "archived" else " "
                console.print(f"{task.id}: [{status_marker}] {task.title}")

        else:
            # Rich table output
            if not tasks:
                console.print("[dim]No tasks for today[/dim]")
                console.print("[dim]Use 'barely pull <task_id> today' to add tasks[/dim]")
                return

            table = Table(title="Today's Tasks")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Status", style="magenta")
            table.add_column("Title", style="white")
            table.add_column("Column", style="blue")

            for task in tasks:
                status_display = "✓" if task.scope == "archived" else "○"
                status_style = "green" if task.scope == "archived" else "yellow"

                table.add_row(
                    str(task.id),
                    f"[{status_style}]{status_display}[/{status_style}]",
                    task.title,
                    str(task.column_id),
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(tasks)} task(s)[/dim]")

    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def week(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    List all tasks in this week's scope (your weekly commitment).

    This shows tasks you've pulled into this week for completion.

    Example:
        barely week
        barely week --json
    """
    try:
        tasks = service.list_week()

        if json_output:
            # Output as JSON array
            tasks_data = [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "scope": t.scope,
                    "column_id": t.column_id,
                    "project_id": t.project_id,
                    "created_at": t.created_at,
                    "completed_at": t.completed_at,
                    "updated_at": t.updated_at,
                }
                for t in tasks
            ]
            console.print(json.dumps(tasks_data, indent=2))

        elif raw:
            # Plain text, one per line
            for task in tasks:
                status_marker = "✓" if task.scope == "archived" else " "
                console.print(f"{task.id}: [{status_marker}] {task.title}")

        else:
            # Rich table output
            if not tasks:
                console.print("[dim]No tasks for this week[/dim]")
                console.print("[dim]Use 'barely pull <task_id> week' to add tasks[/dim]")
                return

            table = Table(title="This Week's Tasks")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Status", style="magenta")
            table.add_column("Title", style="white")
            table.add_column("Column", style="blue")

            for task in tasks:
                status_display = "✓" if task.scope == "archived" else "○"
                status_style = "green" if task.scope == "archived" else "yellow"

                table.add_row(
                    str(task.id),
                    f"[{status_style}]{status_display}[/{status_style}]",
                    task.title,
                    str(task.column_id),
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(tasks)} task(s)[/dim]")

    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def backlog(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    List all tasks in the backlog (everything not yet committed to).

    This is where all tasks start by default until you pull them into week or today.

    Example:
        barely backlog
        barely backlog --json
    """
    try:
        tasks = service.list_backlog()

        if json_output:
            # Output as JSON array
            tasks_data = [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "scope": t.scope,
                    "column_id": t.column_id,
                    "project_id": t.project_id,
                    "created_at": t.created_at,
                    "completed_at": t.completed_at,
                    "updated_at": t.updated_at,
                }
                for t in tasks
            ]
            console.print(json.dumps(tasks_data, indent=2))

        elif raw:
            # Plain text, one per line
            for task in tasks:
                status_marker = "✓" if task.scope == "archived" else " "
                console.print(f"{task.id}: [{status_marker}] {task.title}")

        else:
            # Rich table output
            if not tasks:
                console.print("[dim]Backlog is empty[/dim]")
                return

            table = Table(title="Backlog")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Status", style="magenta")
            table.add_column("Title", style="white")
            table.add_column("Column", style="blue")

            for task in tasks:
                status_display = "✓" if task.scope == "archived" else "○"
                status_style = "green" if task.scope == "archived" else "yellow"

                table.add_row(
                    str(task.id),
                    f"[{status_style}]{status_display}[/{status_style}]",
                    task.title,
                    str(task.column_id),
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(tasks)} task(s)[/dim]")

    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def archive(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    View archived/completed tasks.

    Shows tasks that have been marked as done and moved to archived scope.
    You can reactivate tasks by pulling them back: 'pull <id> backlog'.

    Example:
        barely archive
        barely archive --json
    """
    try:
        tasks = service.list_completed()

        if json_output:
            # Output as JSON array
            tasks_data = [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "scope": t.scope,
                    "column_id": t.column_id,
                    "project_id": t.project_id,
                    "created_at": t.created_at,
                    "completed_at": t.completed_at,
                    "updated_at": t.updated_at,
                }
                for t in tasks
            ]
            console.print(json.dumps(tasks_data, indent=2))

        elif raw:
            # Plain text, one per line
            for task in tasks:
                console.print(f"{task.id}: [✓] {task.title}")

        else:
            # Rich table output
            if not tasks:
                console.print("[dim]No archived tasks[/dim]")
                return

            table = Table(title="Archive")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Title", style="white")
            table.add_column("Scope", style="blue")
            table.add_column("Completed", style="dim")

            for task in tasks:
                # Get scope color
                scope_color = "bright_magenta" if task.scope == "today" else "blue" if task.scope == "week" else "dim"

                table.add_row(
                    str(task.id),
                    task.title,
                    f"[{scope_color}]{task.scope}[/{scope_color}]",
                    task.completed_at or task.updated_at or "",
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(tasks)} completed task(s)[/dim]")
            console.print(f"[dim]Tip: Use 'barely mv <id> Todo' to reopen a task[/dim]")

    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def pull(
    task_ids: str = typer.Argument(..., help="Task ID(s) to pull (comma-separated)"),
    scope: str = typer.Argument(..., help="Target scope: 'backlog', 'week', or 'today'"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    Pull one or more tasks into a different scope (commitment operation).

    Common workflows:
    - Pull from backlog to week: Plan your week
    - Pull from week to today: Set your daily focus
    - Pull from today to backlog: Defer a task

    Example:
        barely pull 5 today          # Pull single task into today
        barely pull 3,5,7 week       # Pull multiple tasks into week
        barely pull 10 backlog       # Defer task back to backlog
    """
    try:
        # Validate scope
        valid_scopes = ("backlog", "week", "today")
        if scope not in valid_scopes:
            error_console.print(
                f"[red]Error:[/red] Invalid scope '{scope}'. "
                f"Must be one of: {', '.join(valid_scopes)}"
            )
            raise typer.Exit(1)

        # Parse comma-separated IDs
        ids = [id.strip() for id in task_ids.split(",")]
        pulled_tasks = []
        errors = []

        for id_str in ids:
            try:
                task_id = int(id_str)
                task = service.pull_task(task_id, scope)
                pulled_tasks.append(task)
            except ValueError:
                errors.append(f"Invalid task ID: {id_str}")
            except TaskNotFoundError as e:
                errors.append(str(e))
            except InvalidInputError as e:
                errors.append(str(e))
            except BarelyError as e:
                errors.append(f"Error with task {id_str}: {e}")

        # Display results
        if json_output:
            tasks_data = [
                {
                    "id": t.id,
                    "title": t.title,
                    "scope": t.scope,
                    "status": t.status,
                }
                for t in pulled_tasks
            ]
            console.print(json.dumps(tasks_data, indent=2))
        elif raw:
            for task in pulled_tasks:
                console.print(f"Pulled task {task.id} into {scope}: {task.title}")
        else:
            scope_emoji = {"backlog": "📋", "week": "📅", "today": "⭐"}
            for task in pulled_tasks:
                console.print(
                    f"[blue]{scope_emoji.get(scope, '→')}[/blue] "
                    f"Pulled task {task.id} into [cyan]{scope}[/cyan]: {task.title}"
                )

        # Show errors if any
        if errors:
            for error in errors:
                error_console.print(f"[red]Error:[/red] {error}")
            if not pulled_tasks:
                raise typer.Exit(1)

    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)

