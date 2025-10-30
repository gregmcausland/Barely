"""
FILE: barely/repl/display.py
PURPOSE: Display functions for tasks and tables
EXPORTS:
  - display_task() - Display a single task
  - display_tasks_table() - Display tasks in a formatted table
DEPENDENCIES:
  - rich (formatted output)
  - barely.core.service (business logic)
  - barely.core.models (Task model)
NOTES:
  - Avoids circular imports by accepting console and repl_context as parameters
  - Or importing them lazily after module initialization
"""

from rich.console import Console
from rich.table import Table
from ..core.models import Task

# Create console instance here to avoid circular import
console = Console()


def display_task(task: Task, message: str = "", console_instance: Console = None) -> None:
    """
    Display a single task with optional message.

    Args:
        task: Task object to display
        message: Optional message to show before task (e.g., "Created:")
        console_instance: Optional Rich console instance (defaults to module console)
    """
    if console_instance is None:
        console_instance = console
    
    if message:
        console_instance.print(f"[green]{message}[/green]")

    console_instance.print(f"  [cyan]{task.id}[/cyan]: {task.title} [dim]({task.status})[/dim]")


def display_tasks_table(tasks: list[Task], repl_context=None, console_instance: Console = None) -> None:
    """
    Display tasks in a formatted table.

    Args:
        tasks: List of Task objects to display
        repl_context: Optional REPLContext object for filtering (if None, shows all columns)
        console_instance: Optional Rich console instance (defaults to module console)
    """
    if console_instance is None:
        console_instance = console
    
    if not tasks:
        console_instance.print("[dim]No tasks found[/dim]")
        return

    # Import service lazily to avoid circular imports
    from ..core import service

    # Check if we're in a project context (all tasks from same project)
    in_project_context = False
    project_header_name = None
    
    if repl_context and repl_context.current_project:
        # We're in a project context - show project as header, hide column
        in_project_context = True
        project_header_name = repl_context.current_project.name
    else:
        # Check if all tasks share the same project (even without context)
        project_ids = {task.project_id for task in tasks if task.project_id}
        if len(project_ids) == 1:
            # All tasks from same project - show as header for clarity
            project_id = project_ids.pop()
            project = service.get_project(project_id)
            if project:
                in_project_context = True
                project_header_name = project.name

    # Show project header if in project context
    if in_project_context and project_header_name:
        console_instance.print(f"[bold cyan]Project:[/bold cyan] [cyan]{project_header_name}[/cyan]\n")

    # Build project name cache for efficient lookups (only if showing Project column)
    project_cache = {}
    if not in_project_context:
        project_ids = {task.project_id for task in tasks if task.project_id}
        for proj_id in project_ids:
            project = service.get_project(proj_id)
            if project:
                project_cache[proj_id] = project.name

    # Create table with columns
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("ID", style="cyan", width=6)
    table.add_column("Title", style="white")
    table.add_column("Scope", style="magenta", width=10)
    
    # Only add Project column if not in project context
    if not in_project_context:
        table.add_column("Project", style="yellow", width=12)

    # Add rows for each task
    for task in tasks:
        # Resolve project name from cache (only if showing Project column)
        if not in_project_context:
            if task.project_id:
                project_name = project_cache.get(task.project_id, f"[dim]ID:{task.project_id}[/dim]")
            else:
                project_name = "-"

        # Color code scope: backlog=dim, week=blue, today=bright_magenta
        scope_style_map = {
            "backlog": "dim",
            "week": "blue",
            "today": "bright_magenta",
        }
        scope_style = scope_style_map.get(task.scope, "white")

        # Build row - conditionally include project column
        row_data = [
            str(task.id),
            task.title,
            f"[{scope_style}]{task.scope}[/{scope_style}]",
        ]
        if not in_project_context:
            row_data.append(project_name)
        
        table.add_row(*row_data)

    console_instance.print(table)

