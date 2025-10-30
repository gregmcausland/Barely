"""
FILE: barely/cli/commands/tasks.py
PURPOSE: Task management commands (add, ls, done, rm, edit, desc, show, mv, assign)
"""

import sys
import json
import os
import tempfile
import subprocess
from typing import Optional

import typer
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ..main import app, console, error_console
from ...core import service, repository
from ...core.exceptions import (
    BarelyError,
    TaskNotFoundError,
    ProjectNotFoundError,
    ColumnNotFoundError,
    InvalidInputError,
)
from ...utils import improve_title_with_ai

@app.command()
def add(
    title: str = typer.Argument(..., help="Task title"),
    column_id: int = typer.Option(1, "--column", "-c", help="Column ID (default: 1 = Todo)"),
    project_name: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
    ai: bool = typer.Option(False, "--ai", help="Improve task title using AI (Claude CLI)"),
):
    """
    Create a new task.

    Example:
        barely add "Write documentation"
        barely add "Fix bug" --project "Work" --column 2
        barely add "my stupid task braindump" --ai
    """
    try:
        # If --ai flag is set, improve the title using Claude
        original_title = title
        description = None
        if ai:
            if not raw and not json_output:
                console.print("[dim]Improving title with AI...[/dim]")
            ai_result = improve_title_with_ai(title)
            if ai_result:
                title = ai_result["title"]
                description = ai_result.get("description")  # Optional field
                if not raw and not json_output:
                    console.print(f"[dim]Original: {original_title}[/dim]")
                    console.print(f"[dim]Improved: {title}[/dim]")
                    if description:
                        console.print(f"[dim]Description: {description}[/dim]")
                    console.print()
            else:
                if not raw and not json_output:
                    error_console.print(f"[yellow]Warning:[/yellow] Could not improve title with AI. Make sure Claude CLI is installed and in your PATH.")
                    error_console.print(f"[yellow]Using original title: {original_title}[/yellow]\n")
        
        # Look up project by name if provided (case-insensitive)
        project_id = None
        if project_name:
            try:
                project = service.find_project_by_name_or_raise(project_name)
                project_id = project.id
            except InvalidInputError as e:
                error_console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1)

        task = service.create_task(
            title=title,
            column_id=column_id,
            project_id=project_id,
            description=description,
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
    include_archived: bool = typer.Option(False, "--archived", help="Include archived/completed tasks"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    List tasks (excluding archived/completed by default).

    Example:
        barely ls
        barely ls --project "Work"
        barely ls --archived
        barely ls --json
    """
    try:
        # Look up project by name if provided (case-insensitive)
        project_id = None
        if project_name:
            try:
                project = service.find_project_by_name_or_raise(project_name)
                project_id = project.id
            except InvalidInputError as e:
                error_console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1)

        tasks = service.list_tasks(
            project_id=project_id,
            include_archived=include_archived,
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
                status_marker = "✓" if task.scope == "archived" else " "
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
                status_display = "✓" if task.scope == "archived" else "○"
                status_style = "green" if task.scope == "archived" else "yellow"

                # Color code scope: backlog=dim, week=blue, today=bright_magenta, archived=green
                scope_style_map = {
                    "backlog": "dim",
                    "week": "blue",
                    "today": "bright_magenta",
                    "archived": "green",
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
            # Use relative date formatting
            from ...repl import style
            created_rel = style.format_relative(task.created_at) if task.created_at else "-"
            details.append(f"{created_rel}\n", style="white")

            if task.completed_at:
                details.append(f"Completed: ", style="dim")
                completed_rel = style.format_relative(task.completed_at)
                details.append(f"{completed_rel}\n", style="green")

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
        try:
            column = service.find_column_by_name_or_raise(column_name)
        except InvalidInputError as e:
            error_console.print(f"[red]Error:[/red] {e}")
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
        try:
            project = service.find_project_by_name_or_raise(project_name)
        except InvalidInputError as e:
            error_console.print(f"[red]Error:[/red] {e}")
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
