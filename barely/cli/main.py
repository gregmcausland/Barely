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
  - history() - View completed tasks
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


@app.command()
def version():
    """Show Barely version."""
    console.print(f"Barely v{__version__}")


@app.command()
def help():
    """Show available commands and usage."""
    console.print("\n[bold cyan]Barely[/bold cyan] - Minimalist terminal-native task manager\n")
    console.print(f"[dim]Version {__version__}[/dim]\n")

    console.print("[bold]Usage:[/bold]")
    console.print("  barely [command] [options]")
    console.print("  barely                    [dim]# Launch interactive REPL (default)[/dim]\n")

    console.print("[bold]Commands:[/bold]")

    commands = [
        ("add", "Create a new task", 'barely add "Task title"'),
        ("ls", "List tasks", "barely ls [--status todo|done] [--project ID]"),
        ("done", "Mark task as complete", "barely done <task_id>"),
        ("edit", "Update task title", 'barely edit <task_id> "New title"'),
        ("desc", "Edit task description", "barely desc <task_id>"),
        ("show", "View full task details", "barely show <task_id>"),
        ("rm", "Delete task(s)", 'barely rm <task_id> | "*"'),
        ("mv", "Move task to column", 'barely mv <task_id> "Column name"'),
        ("assign", "Assign task to project", 'barely assign <task_id> "Project name"'),
        ("today", "List today's tasks", "barely today"),
        ("week", "List this week's tasks", "barely week"),
        ("backlog", "List backlog tasks", "barely backlog"),
        ("history", "View completed tasks", "barely history"),
        ("pull", "Pull tasks into scope", "barely pull <task_id(s)> <scope>"),
        ("project add", "Create a project", 'barely project add "Project name"'),
        ("project ls", "List projects", "barely project ls"),
        ("project rm", "Delete project(s)", 'barely project rm <project_id> | "*"'),
        ("repl", "Launch interactive REPL", "barely repl"),
        ("blitz", "Focused task completion mode", "barely blitz"),
        ("version", "Show version", "barely version"),
        ("help", "Show this help message", "barely help"),
    ]

    for cmd, desc, example in commands:
        console.print(f"  [green]{cmd:8}[/green] {desc}")
        console.print(f"           [dim]{example}[/dim]\n")

    console.print("[bold]Global Options:[/bold]")
    console.print("  [yellow]--json[/yellow]    Output as JSON (for scripting)")
    console.print("  [yellow]--raw[/yellow]     Plain text output (no colors)")
    console.print("  [yellow]--help[/yellow]    Show detailed help for a command\n")

    console.print("[bold]Examples:[/bold]")
    console.print("  barely                         # Launch REPL (default)")
    console.print('  barely add "Write documentation"')
    console.print("  barely ls --status todo")
    console.print("  barely done 5")
    console.print("  barely done 3,5,7              # Mark multiple tasks as done")
    console.print('  barely edit 5 "Updated title"')
    console.print("  barely rm 5")
    console.print("  barely rm 3,5,7                # Delete multiple tasks")
    console.print("  barely mv 5 Done")
    console.print('  barely assign 5 "Work"         # Assign task to project')
    console.print("  barely today                   # View today's focus list")
    console.print("  barely week                    # View this week's commitment")
    console.print("  barely pull 3,5,7 today        # Pull tasks into today")
    console.print("  barely pull 10 backlog         # Defer task to backlog")
    console.print("  barely project add Work")
    console.print("  barely project rm 2,3          # Delete multiple projects")
    console.print("  barely ls --json\n")


@app.command()
def repl():
    """
    Launch interactive REPL mode.

    The REPL provides:
    - Command history (up/down arrows)
    - Autocomplete (Tab key)
    - All task management commands
    - Exit with Ctrl+D or type 'exit'

    Example:
        barely repl
    """
    # Import here to avoid loading REPL dependencies for one-shot commands
    from ..repl import main as repl_main

    try:
        repl_main()
    except Exception as e:
        error_console.print(f"[red]Error starting REPL:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def blitz():
    """
    Launch blitz mode for focused task completion.

    Blitz mode provides:
    - One task at a time from today's scope
    - Live audio waveform visualization
    - Keyboard controls (d=done, s=skip, q=quit, ?=details)
    - Progress tracking with strikethrough
    - Celebration on completion

    Example:
        barely blitz
    """
    # Import here to avoid loading dependencies for one-shot commands
    from ..repl.blitz import run_blitz_mode

    try:
        run_blitz_mode()
    except Exception as e:
        error_console.print(f"[red]Error in blitz mode:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def add(
    title: str = typer.Argument(..., help="Task title"),
    column_id: int = typer.Option(1, "--column", "-c", help="Column ID (default: 1 = Todo)"),
    project_name: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    Create a new task.

    Example:
        barely add "Write documentation"
        barely add "Fix bug" --project "Work" --column 2
    """
    try:
        # Look up project by name if provided (case-insensitive)
        project_id = None
        if project_name:
            projects = service.list_projects()
            project = next((p for p in projects if p.name.lower() == project_name.lower()), None)
            if not project:
                error_console.print(f"[red]Error:[/red] Project '{project_name}' not found")
                error_console.print("\n[dim]Available projects:[/dim]")
                for p in projects:
                    error_console.print(f"  - {p.name}")
                raise typer.Exit(1)
            project_id = project.id

        task = service.create_task(
            title=title,
            column_id=column_id,
            project_id=project_id,
        )

        if json_output:
            console.print(task.to_json())
        elif raw:
            console.print(f"{task.id}: {task.title}")
        else:
            console.print(f"[green]✓ Created task [bold]#{task.id}[/bold]:[/green] {task.title}")

    except InvalidInputError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def ls(
    project_name: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project name"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (todo/done/archived)"),
    include_done: bool = typer.Option(False, "--done", help="Include completed tasks"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    List tasks (excluding completed by default).

    Example:
        barely ls
        barely ls --status todo
        barely ls --project "Work"
        barely ls --done
        barely ls --json
    """
    try:
        # Look up project by name if provided (case-insensitive)
        project_id = None
        if project_name:
            projects = service.list_projects()
            project = next((p for p in projects if p.name.lower() == project_name.lower()), None)
            if not project:
                error_console.print(f"[red]Error:[/red] Project '{project_name}' not found")
                error_console.print("\n[dim]Available projects:[/dim]")
                for p in projects:
                    error_console.print(f"  - {p.name}")
                raise typer.Exit(1)
            project_id = project.id

        tasks = service.list_tasks(
            project_id=project_id,
            status=status,
            include_done=include_done,
        )

        if json_output:
            # Output as JSON array
            tasks_data = [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
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
                status_marker = "✓" if task.status == "done" else " "
                console.print(f"{task.id}: [{status_marker}] {task.title}")

        else:
            # Rich table output
            if not tasks:
                console.print("[dim]No tasks found[/dim]")
                return

            table = Table(title="Tasks")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Status", style="magenta")
            table.add_column("Scope", style="magenta")
            table.add_column("Title", style="white")
            table.add_column("Column", style="blue")

            for task in tasks:
                status_display = "✓" if task.status == "done" else "○"
                status_style = "green" if task.status == "done" else "yellow"

                # Color code scope: backlog=dim, week=blue, today=bright_magenta
                scope_style_map = {
                    "backlog": "dim",
                    "week": "blue",
                    "today": "bright_magenta",
                }
                scope_style = scope_style_map.get(task.scope, "white")

                table.add_row(
                    str(task.id),
                    f"[{status_style}]{status_display}[/{status_style}]",
                    f"[{scope_style}]{task.scope}[/{scope_style}]",
                    task.title,
                    str(task.column_id),
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(tasks)} task(s)[/dim]")

    except InvalidInputError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def done(
    task_ids: str = typer.Argument(..., help="Task ID(s) to complete (comma-separated)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    Mark one or more tasks as complete.

    Example:
        barely done 5
        barely done 3,5,7
        barely done 3 --json
    """
    try:
        # Parse comma-separated IDs
        ids = [id.strip() for id in task_ids.split(",")]
        completed_tasks = []
        errors = []

        for id_str in ids:
            try:
                task_id = int(id_str)
                task = service.complete_task(task_id)
                completed_tasks.append(task)
            except ValueError:
                errors.append(f"Invalid task ID: {id_str}")
            except TaskNotFoundError as e:
                errors.append(str(e))
            except BarelyError as e:
                errors.append(f"Error with task {id_str}: {e}")

        # Display results
        if json_output:
            tasks_data = [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "completed_at": t.completed_at,
                }
                for t in completed_tasks
            ]
            console.print(json.dumps(tasks_data, indent=2))
        elif raw:
            for task in completed_tasks:
                console.print(f"Completed: {task.title}")
        else:
            for task in completed_tasks:
                console.print(f"[green]✓[/green] Completed: {task.title}")

        # Show errors if any
        if errors:
            for error in errors:
                error_console.print(f"[red]Error:[/red] {error}")
            if not completed_tasks:
                raise typer.Exit(1)

    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def rm(
    task_ids: str = typer.Argument(..., help="Task ID(s) to delete (comma-separated or '*' for all)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt"),
):
    """
    Delete one or more tasks permanently.

    Supports:
    - barely rm 5           - delete single task
    - barely rm 3,5,7       - delete multiple tasks
    - barely rm '*'         - delete all tasks

    Confirms before deleting multiple tasks (use -y to skip).

    Example:
        barely rm 5
        barely rm 3,5,7
        barely rm '*'
        barely rm 3,5,7 --yes
    """
    try:
        # Handle wildcard: delete all tasks
        if task_ids.strip() == "*":
            all_tasks = service.list_tasks()

            if not all_tasks:
                console.print("[yellow]No tasks to delete[/yellow]")
                raise typer.Exit(0)

            # Confirm deletion unless --yes
            if not yes and len(all_tasks) > 0:
                console.print(f"[yellow]About to delete {len(all_tasks)} task(s)[/yellow]")
                response = typer.confirm("Continue?", default=False)
                if not response:
                    console.print("[yellow]Cancelled[/yellow]")
                    raise typer.Exit(0)

            # Delete all tasks
            deleted_tasks = []
            errors = []

            for task in all_tasks:
                try:
                    service.delete_task(task.id)
                    deleted_tasks.append({"id": task.id, "title": task.title})
                except (TaskNotFoundError, BarelyError) as e:
                    errors.append(f"Task {task.id}: {e}")

            # Display results
            if json_output:
                console.print(json.dumps(deleted_tasks, indent=2))
            elif raw:
                for task in deleted_tasks:
                    console.print(f"Deleted task {task['id']}: {task['title']}")
            else:
                console.print(f"[green]✓ Deleted {len(deleted_tasks)} task(s)[/green]")
                if errors:
                    for error in errors:
                        error_console.print(f"[red]Error:[/red] {error}")

            raise typer.Exit(0 if not errors else 1)

        # Parse comma-separated IDs
        ids = [id.strip() for id in task_ids.split(",")]
        deleted_tasks = []
        errors = []

        # Get all tasks once for efficiency
        all_tasks = service.list_tasks()
        all_tasks_dict = {t.id: t for t in all_tasks}

        # Validate IDs first
        valid_ids = []
        for id_str in ids:
            try:
                task_id = int(id_str)
                if task_id not in all_tasks_dict:
                    errors.append(f"Task {id_str} not found")
                else:
                    valid_ids.append(task_id)
            except ValueError:
                errors.append(f"Invalid task ID: {id_str}")

        if not valid_ids:
            for error in errors:
                error_console.print(f"[red]Error:[/red] {error}")
            raise typer.Exit(1)

        # Confirm deletion for multiple tasks unless --yes
        if not yes and len(valid_ids) > 1:
            console.print(f"[yellow]About to delete {len(valid_ids)} task(s)[/yellow]")
            response = typer.confirm("Continue?", default=False)
            if not response:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        # Delete tasks
        for task_id in valid_ids:
            try:
                task_to_delete = all_tasks_dict[task_id]
                service.delete_task(task_id)
                deleted_tasks.append({"id": task_id, "title": task_to_delete.title})
            except (TaskNotFoundError, BarelyError) as e:
                errors.append(f"Error deleting task {task_id}: {e}")

        # Display results
        if json_output:
            console.print(json.dumps(deleted_tasks, indent=2))
        elif raw:
            for task in deleted_tasks:
                console.print(f"Deleted task {task['id']}: {task['title']}")
        else:
            for task in deleted_tasks:
                console.print(f"[red]✗[/red] Deleted task {task['id']}: {task['title']}")

        # Show errors if any
        if errors:
            for error in errors:
                error_console.print(f"[red]Error:[/red] {error}")
            if not deleted_tasks:
                raise typer.Exit(1)

    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def edit(
    task_id: int = typer.Argument(..., help="Task ID to edit"),
    new_title: str = typer.Argument(..., help="New task title"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    Update a task's title.

    Example:
        barely edit 5 "Updated task title"
    """
    try:
        task = service.update_task_title(task_id, new_title)

        if json_output:
            console.print(task.to_json())
        elif raw:
            console.print(f"Updated task {task.id}: {task.title}")
        else:
            console.print(f"[blue]✎[/blue] Updated task {task.id}: {task.title}")

    except TaskNotFoundError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except InvalidInputError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def desc(
    task_id: int = typer.Argument(..., help="Task ID to edit description"),
):
    """
    Edit a task's description in your default text editor.

    Opens $EDITOR (or notepad on Windows) with the task's current description.
    Save and close the editor to update the description.

    Example:
        barely desc 5
    """
    import os
    import tempfile
    import subprocess

    try:
        # Get the task to edit
        task = repository.get_task(task_id)
        if not task:
            error_console.print(f"[red]Error:[/red] Task {task_id} not found")
            raise typer.Exit(1)

        # Determine editor
        editor = os.environ.get('EDITOR')
        if not editor:
            editor = 'notepad' if sys.platform == 'win32' else 'nano'

        # Create temp file with current description
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            if task.description:
                f.write(task.description)
            temp_path = f.name

        try:
            # Open editor
            subprocess.run([editor, temp_path], check=True)

            # Read back the content
            with open(temp_path, 'r', encoding='utf-8') as f:
                new_description = f.read()

            # Update task
            task = service.update_task_description(task_id, new_description)

            if new_description.strip():
                console.print(f"[blue]✎[/blue] Updated description for task {task.id}: {task.title}")
            else:
                console.print(f"[blue]✎[/blue] Cleared description for task {task.id}: {task.title}")

        finally:
            # Clean up temp file
            os.unlink(temp_path)

    except TaskNotFoundError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except subprocess.CalledProcessError:
        error_console.print(f"[red]Error:[/red] Editor was closed without saving")
        raise typer.Exit(1)
    except Exception as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def show(
    task_id: int = typer.Argument(..., help="Task ID to view"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    Show full details for a task including description.

    Example:
        barely show 5
    """
    try:
        task = repository.get_task(task_id)
        if not task:
            error_console.print(f"[red]Error:[/red] Task {task_id} not found")
            raise typer.Exit(1)

        if json_output:
            console.print(task.to_json())
            return

        # Get project name if exists
        project_name = None
        if task.project_id:
            project = service.get_project(task.project_id)
            project_name = project.name if project else f"#{task.project_id}"

        if raw:
            console.print(f"Task #{task.id}")
            console.print(f"Title: {task.title}")
            if task.description:
                console.print(f"Description: {task.description}")
            console.print(f"Status: {task.status}")
            console.print(f"Scope: {task.scope}")
            if project_name:
                console.print(f"Project: {project_name}")
            console.print(f"Created: {task.created_at}")
            if task.completed_at:
                console.print(f"Completed: {task.completed_at}")
        else:
            # Rich formatted output
            from rich.panel import Panel
            from rich.text import Text

            details = Text()
            details.append(f"Task #{task.id}\n", style="bold cyan")
            details.append(f"{task.title}\n\n", style="bold white")

            if task.description:
                details.append("Description:\n", style="dim")
                details.append(f"{task.description}\n\n", style="white")

            details.append(f"Status: ", style="dim")
            details.append(f"{task.status}\n", style="yellow" if task.status == "todo" else "green")

            details.append(f"Scope: ", style="dim")
            scope_color = "bright_magenta" if task.scope == "today" else "blue" if task.scope == "week" else "dim"
            details.append(f"{task.scope}\n", style=scope_color)

            if project_name:
                details.append(f"Project: ", style="dim")
                details.append(f"{project_name}\n", style="cyan")

            details.append(f"Created: ", style="dim")
            details.append(f"{task.created_at}\n", style="white")

            if task.completed_at:
                details.append(f"Completed: ", style="dim")
                details.append(f"{task.completed_at}\n", style="green")

            panel = Panel(details, border_style="blue", padding=(1, 2))
            console.print(panel)

    except BarelyError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def mv(
    task_id: int = typer.Argument(..., help="Task ID to move"),
    column_name: str = typer.Argument(..., help="Target column name (e.g., 'Todo', 'In Progress', 'Done')"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    Move a task to a different column.

    Example:
        barely mv 5 "In Progress"
        barely mv 3 Done
    """
    try:
        # Look up column by name
        column = repository.get_column_by_name(column_name)
        if not column:
            error_console.print(f"[red]Error:[/red] Column '{column_name}' not found")
            error_console.print("\n[dim]Available columns:[/dim]")
            columns = service.list_columns()
            for col in columns:
                error_console.print(f"  - {col.name}")
            raise typer.Exit(1)

        # Move task
        task = service.move_task(task_id, column.id)

        if json_output:
            console.print(task.to_json())
        elif raw:
            console.print(f"Moved task {task.id} to {column.name}")
        else:
            console.print(f"[blue]→[/blue] Moved task {task.id} to [cyan]{column.name}[/cyan]")

    except TaskNotFoundError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except ColumnNotFoundError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def assign(
    task_id: int = typer.Argument(..., help="Task ID to assign"),
    project_name: str = typer.Argument(..., help="Project name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    Assign a task to a project.

    Example:
        barely assign 5 "Work"
        barely assign 3 Personal
    """
    try:
        # Look up project by name (case-insensitive)
        projects = service.list_projects()
        project = next((p for p in projects if p.name.lower() == project_name.lower()), None)
        if not project:
            error_console.print(f"[red]Error:[/red] Project '{project_name}' not found")
            error_console.print("\n[dim]Available projects:[/dim]")
            for p in projects:
                error_console.print(f"  - {p.name}")
            raise typer.Exit(1)

        # Assign task to project
        task = service.assign_task_to_project(task_id, project.id)

        if json_output:
            console.print(task.to_json())
        elif raw:
            console.print(f"Assigned task {task.id} to {project.name}")
        else:
            console.print(f"[cyan]→[/cyan] Assigned task {task.id} to [cyan]{project.name}[/cyan]")

    except TaskNotFoundError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except ProjectNotFoundError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


# --- Pull-Based Workflow Commands ---


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
                status_marker = "✓" if task.status == "done" else " "
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
                status_display = "✓" if task.status == "done" else "○"
                status_style = "green" if task.status == "done" else "yellow"

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
                status_marker = "✓" if task.status == "done" else " "
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
                status_display = "✓" if task.status == "done" else "○"
                status_style = "green" if task.status == "done" else "yellow"

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
                status_marker = "✓" if task.status == "done" else " "
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
                status_display = "✓" if task.status == "done" else "○"
                status_style = "green" if task.status == "done" else "yellow"

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
def history(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    View completed tasks (your work history).

    Shows tasks that have been marked as done and moved to the Done column.
    You can reopen tasks with 'mv <id> Todo'.

    Example:
        barely history
        barely history --json
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
                console.print("[dim]No completed tasks[/dim]")
                return

            table = Table(title="History")
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


# --- Project Commands ---


@project_app.command("add")
def project_add(
    name: str = typer.Argument(..., help="Project name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    Create a new project.

    Example:
        barely project add "Work"
        barely project add "Personal" --json
    """
    try:
        project = service.create_project(name)

        if json_output:
            console.print(project.to_json())
        elif raw:
            console.print(f"{project.id}: {project.name}")
        else:
            console.print(f"[green]✓[/green] Created project {project.id}: {project.name}")

    except InvalidInputError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@project_app.command("ls")
def project_ls(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    List all projects.

    Example:
        barely project ls
        barely project ls --json
    """
    try:
        projects = service.list_projects()

        if json_output:
            # Output as JSON array
            projects_data = [
                {
                    "id": p.id,
                    "name": p.name,
                    "created_at": p.created_at,
                }
                for p in projects
            ]
            console.print(json.dumps(projects_data, indent=2))

        elif raw:
            # Plain text, one per line
            for project in projects:
                console.print(f"{project.id}: {project.name}")

        else:
            # Rich table output
            if not projects:
                console.print("[dim]No projects found[/dim]")
                return

            table = Table(title="Projects")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="white")
            table.add_column("Created", style="dim")

            for project in projects:
                # Format created_at as just the date if available
                created_display = project.created_at.split("T")[0] if project.created_at else ""

                table.add_row(
                    str(project.id),
                    project.name,
                    created_display,
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(projects)} project(s)[/dim]")

    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@project_app.command("rm")
def project_rm(
    project_ids: str = typer.Argument(..., help="Project ID(s) to delete (comma-separated or '*' for all)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt"),
):
    """
    Delete one or more projects permanently.

    Supports:
    - barely project rm 2           - delete single project
    - barely project rm 2,3,5       - delete multiple projects
    - barely project rm '*'         - delete all projects

    Tasks associated with deleted projects will have their project_id set to NULL.

    Confirms before deleting multiple projects (use -y to skip).

    Example:
        barely project rm 2
        barely project rm 2,3,5
        barely project rm '*'
        barely project rm 2,3,5 --yes
    """
    try:
        # Handle wildcard: delete all projects
        if project_ids.strip() == "*":
            all_projects = service.list_projects()

            if not all_projects:
                console.print("[yellow]No projects to delete[/yellow]")
                raise typer.Exit(0)

            # Confirm deletion unless --yes
            if not yes and len(all_projects) > 0:
                console.print(f"[yellow]About to delete {len(all_projects)} project(s)[/yellow]")
                response = typer.confirm("Continue?", default=False)
                if not response:
                    console.print("[yellow]Cancelled[/yellow]")
                    raise typer.Exit(0)

            # Delete all projects
            deleted_projects = []
            errors = []

            for project in all_projects:
                try:
                    service.delete_project(project.id)
                    deleted_projects.append({"id": project.id, "name": project.name})
                except (ProjectNotFoundError, BarelyError) as e:
                    errors.append(f"Project {project.id}: {e}")

            # Display results
            if json_output:
                console.print(json.dumps(deleted_projects, indent=2))
            elif raw:
                for project in deleted_projects:
                    console.print(f"Deleted project {project['id']}: {project['name']}")
            else:
                console.print(f"[green]✓ Deleted {len(deleted_projects)} project(s)[/green]")
                if deleted_projects:
                    console.print("[dim]Tasks in these projects now have no project assigned[/dim]")
                if errors:
                    for error in errors:
                        error_console.print(f"[red]Error:[/red] {error}")

            raise typer.Exit(0 if not errors else 1)

        # Parse comma-separated IDs
        ids = [id.strip() for id in project_ids.split(",")]
        deleted_projects = []
        errors = []

        # Get all projects once for efficiency
        all_projects = service.list_projects()
        all_projects_dict = {p.id: p for p in all_projects}

        # Validate IDs first
        valid_ids = []
        for id_str in ids:
            try:
                project_id = int(id_str)
                if project_id not in all_projects_dict:
                    errors.append(f"Project {id_str} not found")
                else:
                    valid_ids.append(project_id)
            except ValueError:
                errors.append(f"Invalid project ID: {id_str}")

        if not valid_ids:
            for error in errors:
                error_console.print(f"[red]Error:[/red] {error}")
            raise typer.Exit(1)

        # Confirm deletion for multiple projects unless --yes
        if not yes and len(valid_ids) > 1:
            console.print(f"[yellow]About to delete {len(valid_ids)} project(s)[/yellow]")
            response = typer.confirm("Continue?", default=False)
            if not response:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        # Delete projects
        for project_id in valid_ids:
            try:
                project_to_delete = all_projects_dict[project_id]
                service.delete_project(project_id)
                deleted_projects.append({"id": project_id, "name": project_to_delete.name})
            except (ProjectNotFoundError, BarelyError) as e:
                errors.append(f"Error deleting project {project_id}: {e}")

        # Display results
        if json_output:
            console.print(json.dumps(deleted_projects, indent=2))
        elif raw:
            for project in deleted_projects:
                console.print(f"Deleted project {project['id']}: {project['name']}")
        else:
            for project in deleted_projects:
                console.print(f"[red]✗[/red] Deleted project {project['id']}: {project['name']}")
            if deleted_projects:
                console.print("[dim]Tasks in these projects now have no project assigned[/dim]")

        # Show errors if any
        if errors:
            for error in errors:
                error_console.print(f"[red]Error:[/red] {error}")
            if not deleted_projects:
                raise typer.Exit(1)

    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


def main():
    """Main entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
