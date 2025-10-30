"""
FILE: barely/repl/commands/tasks.py
PURPOSE: Task command handlers for REPL
"""

import sys
import os
import tempfile
import subprocess
from typing import Optional, List

from ..main import console, repl_context
from ..parser import ParseResult
from ...core import service, repository
from ...core.exceptions import (
    BarelyError,
    TaskNotFoundError,
    ProjectNotFoundError,
    ColumnNotFoundError,
    InvalidInputError,
)
from ...utils import improve_title_with_ai
from ..style import celebrate_add, celebrate_done, celebrate_delete, celebrate_bulk, format_relative
from ..undo import record_create, record_complete, record_delete, record_update_title, record_mv
from ..pickers import pick_task
from ..display import display_task, display_tasks_table

# Helper function
def ask_confirmation(message: str) -> bool:
    """Ask user for confirmation (y/n)."""
    response = input(f"{message} (y/n): ").strip().lower()
    return response in ('y', 'yes')

def handle_add_command(result: ParseResult) -> None:
    """
    Handle 'add' command - create new task.

    Args:
        result: Parsed command with args and flags

    Usage:
        add Buy groceries
        add "Task with spaces"
        add "my messy task" --ai
    """
    # Get title from args
    if not result.args:
        console.print("[red]Error:[/red] Task title required")
        console.print("[dim]Usage: add <title> [--ai][/dim]")
        return

    # Join all args as the title (in case they didn't use quotes)
    title = " ".join(result.args)

    # Check for --ai flag
    use_ai = result.flags.get("ai", False)
    
    # If --ai flag is set, improve the title using Claude
    original_title = title
    description = None
    if use_ai:
        console.print("[dim]Improving title with AI...[/dim]")
        ai_result = improve_title_with_ai(title)
        if ai_result:
            title = ai_result["title"]
            description = ai_result.get("description")  # Optional field
            console.print(f"[dim]Original: {original_title}[/dim]")
            console.print(f"[dim]Improved: {title}[/dim]")
            if description:
                console.print(f"[dim]Description: {description}[/dim]")
            console.print()
        else:
            console.print(f"[yellow]Warning:[/yellow] Could not improve title with AI. Make sure Claude CLI is installed and in your PATH.")
            console.print(f"[yellow]Using original title: {original_title}[/yellow]\n")

    try:
        # Default to context project if set
        project_id = None
        if repl_context.current_project:
            project_id = repl_context.current_project.id

        task = service.create_task(title, project_id=project_id, description=description)

        # Record for undo
        record_create(task.id)

        # Celebrate!
        celebrate_add()

        # Show which project it went to, always include task ID
        if repl_context.current_project:
            console.print(f"[green]✓ Created task [bold]#{task.id}[/bold] in [cyan]{repl_context.current_project.name}[/cyan]:[/green] {task.title}")
        else:
            console.print(f"[green]✓ Created task [bold]#{task.id}[/bold]:[/green] {task.title}")
    except InvalidInputError as e:
        console.print(f"[red]Error:[/red] {e}")
    except BarelyError as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def handle_ls_command(result: ParseResult) -> None:
    """
    Handle 'ls' command - list tasks (excludes archived by default).

    Args:
        result: Parsed command with args and flags

    Usage:
        ls
        ls --project "Work"
        ls --archived              (include archived/completed tasks)
    """
    # Get optional filters from flags
    project_name = result.flags.get("project")
    include_archived = result.flags.get("archived", False)

    try:
        # Determine project filter (flag overrides context)
        project_id = None
        if project_name:
            # User explicitly specified --project, use that
            try:
                project = service.find_project_by_name_or_raise(project_name)
                project_id = project.id
            except InvalidInputError as e:
                console.print(f"[red]Error:[/red] {e}")
                return
        elif repl_context.current_project:
            # No flag, but context is set - use context
            project_id = repl_context.current_project.id

        # Get tasks with filters
        # If scope filter is set to 'archived', automatically include archived tasks
        if repl_context.current_scope == 'archived':
            include_archived = True
        
        tasks = service.list_tasks(project_id=project_id, include_archived=include_archived)

        # Apply scope filter from context if set
        if repl_context.current_scope:
            tasks = [t for t in tasks if t.scope == repl_context.current_scope]

        display_tasks_table(tasks, repl_context, console)
    except InvalidInputError as e:
        console.print(f"[red]Error:[/red] {e}")
    except BarelyError as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def handle_done_command(result: ParseResult) -> None:
    """
    Handle 'done' command - mark task complete.

    Args:
        result: Parsed command with args and flags

    Usage:
        done 42
        done 1,2,3
        done           (shows picker)
    """
    if not result.args:
        # No args - show picker for active tasks (excludes archived)
        task_ids = pick_task(title="Mark task as done")
        if task_ids is None:
            return  # User cancelled

        # Process tasks from picker (supports bulk selection)
        completed_count = 0
        for task_id in task_ids:
            try:
                # Get original task data before completion
                original_task = repository.get_task(task_id)
                if original_task:
                    original_scope = original_task.scope
                    original_completed_at = original_task.completed_at
                    original_column_id = original_task.column_id
                else:
                    original_scope = "backlog"
                    original_completed_at = None
                    original_column_id = 1
                
                task = service.complete_task(task_id)
                
                # Record for undo (only track last operation)
                record_complete(task_id, original_scope, original_completed_at, original_column_id)
                
                celebrate_done()
                display_task(task, "✓ Completed:", console)
                completed_count += 1
            except TaskNotFoundError as e:
                console.print(f"[red]Error:[/red] {e}")
            except BarelyError as e:
                console.print(f"[red]Error:[/red] {e}")

        if completed_count > 1:
            bulk_msg = celebrate_bulk(completed_count, "completed")
            console.print(f"[green]{bulk_msg}[/green]")
        return

    try:
        # Parse comma-separated IDs
        ids = [id.strip() for id in result.args[0].split(",")]
        completed_count = 0

        for id_str in ids:
            try:
                task_id = int(id_str)
                
                # Get original task data before completion
                original_task = repository.get_task(task_id)
                if original_task:
                    original_scope = original_task.scope
                    original_completed_at = original_task.completed_at
                    original_column_id = original_task.column_id
                else:
                    original_scope = "backlog"
                    original_completed_at = None
                    original_column_id = 1
                
                task = service.complete_task(task_id)
                
                # Record for undo (only track last operation)
                record_complete(task_id, original_scope, original_completed_at, original_column_id)
                
                celebrate_done()
                display_task(task, "✓ Completed:", console)
                completed_count += 1
            except ValueError:
                console.print(f"[red]Error:[/red] Invalid task ID: {id_str}")
            except TaskNotFoundError as e:
                console.print(f"[red]Error:[/red] {e}")
            except BarelyError as e:
                console.print(f"[red]Error:[/red] {e}")

        if completed_count > 1:
            bulk_msg = celebrate_bulk(completed_count, "completed")
            console.print(f"[green]{bulk_msg}[/green]")
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


# Helper function
def ask_confirmation(message: str) -> bool:
    """
    Ask user for confirmation (y/n).

    Args:
        message: Message to display

    Returns:
        True if user confirms (y), False otherwise
    """
    response = input(f"{message} (y/n): ").strip().lower()
    return response in ('y', 'yes')


def handle_rm_command(result: ParseResult) -> None:
    """
    Handle 'rm' command - delete task(s).

    Supports:
    - rm 42              - delete single task
    - rm 1,2,3           - delete multiple tasks
    - rm *               - delete all tasks in current context (scope/project)
    - rm                 - show picker

    Respects current project/scope filters.
    Always confirms before deleting multiple tasks.

    Args:
        result: Parsed command with args and flags

    Usage:
        rm 42
        rm 1,2,3
        rm *
        rm             (shows picker)
    """
    if not result.args:
        # No args - show picker
        task_ids = pick_task(title="Delete task")
        if task_ids is None:
            return  # User cancelled

        # Confirm deletion for multiple tasks
        if len(task_ids) > 1:
            if not ask_confirmation(f"Delete {len(task_ids)} tasks?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        # Process tasks from picker (supports bulk selection)
        deleted_count = 0
        for task_id in task_ids:
            try:
                # Get task data before deletion (for undo)
                task_data = None
                task = repository.get_task(task_id)
                if task:
                    task_data = {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "status": task.status,
                        "scope": task.scope,
                        "project_id": task.project_id,
                        "column_id": task.column_id,
                    }
                
                service.delete_task(task_id)
                
                # Record for undo (only track last operation)
                if task_data:
                    record_delete(task_id, task_data)
                
                celebrate_delete()
                console.print(f"[green]✓ Deleted task {task_id}[/green]")
                deleted_count += 1
            except TaskNotFoundError as e:
                console.print(f"[red]Error:[/red] {e}")
            except BarelyError as e:
                console.print(f"[red]Error:[/red] {e}")

        if deleted_count > 1:
            bulk_msg = celebrate_bulk(deleted_count, "deleted")
            console.print(f"[green]{bulk_msg}[/green]")
        return

    try:
        arg = result.args[0].strip()

        # Handle wildcard: delete all tasks in current context
        if arg == "*":
            all_tasks = service.list_tasks()
            # Filter by current context (project/scope)
            tasks_to_delete = repl_context.filter_tasks(all_tasks)

            if not tasks_to_delete:
                console.print("[yellow]No tasks to delete in current context[/yellow]")
                return

            # Show what would be deleted
            context_desc = ""
            if repl_context.current_project or repl_context.current_scope:
                parts = []
                if repl_context.current_project:
                    parts.append(f"project '{repl_context.current_project.name}'")
                if repl_context.current_scope:
                    parts.append(f"scope '{repl_context.current_scope}'")
                context_desc = f" in {' and '.join(parts)}"
            else:
                context_desc = " (all tasks)"

            # Confirm deletion
            if not ask_confirmation(f"Delete {len(tasks_to_delete)} tasks{context_desc}?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

            # Delete all in batch
            deleted_count = 0
            for task in tasks_to_delete:
                try:
                    service.delete_task(task.id)
                    deleted_count += 1
                except (TaskNotFoundError, BarelyError) as e:
                    console.print(f"[red]Error deleting task {task.id}:[/red] {e}")

            celebrate_delete()
            bulk_msg = celebrate_bulk(deleted_count, "deleted")
            console.print(f"[green]{bulk_msg}[/green]")
            return

        # Handle comma-separated IDs
        ids = [id.strip() for id in arg.split(",")]

        # Collect valid task IDs (respect context)
        all_tasks = service.list_tasks()
        context_tasks = {t.id: t for t in repl_context.filter_tasks(all_tasks)}

        tasks_to_delete = []
        invalid_ids = []

        for id_str in ids:
            try:
                task_id = int(id_str)

                # Check if task exists in current context
                if task_id not in context_tasks:
                    # Task doesn't exist or not in current context
                    all_tasks_dict = {t.id: t for t in all_tasks}
                    if task_id not in all_tasks_dict:
                        invalid_ids.append((id_str, "not found"))
                    else:
                        invalid_ids.append((id_str, "not in current context"))
                else:
                    tasks_to_delete.append(task_id)
            except ValueError:
                invalid_ids.append((id_str, "invalid ID"))

        # Report invalid IDs
        for id_str, reason in invalid_ids:
            console.print(f"[yellow]Warning:[/yellow] Task {id_str} - {reason}")

        if not tasks_to_delete:
            console.print("[yellow]No valid tasks to delete[/yellow]")
            return

        # Confirm deletion for multiple tasks
        if len(tasks_to_delete) > 1:
            if not ask_confirmation(f"Delete {len(tasks_to_delete)} tasks?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        # Delete tasks
        deleted_count = 0
        for task_id in tasks_to_delete:
            try:
                # Get task data before deletion (for undo)
                task_data = None
                task = repository.get_task(task_id)
                if task:
                    task_data = {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "status": task.status,
                        "scope": task.scope,
                        "project_id": task.project_id,
                        "column_id": task.column_id,
                    }
                
                service.delete_task(task_id)
                
                # Record for undo (only track last operation)
                if task_data:
                    record_delete(task_id, task_data)
                
                celebrate_delete()
                console.print(f"[green]✓ Deleted task {task_id}[/green]")
                deleted_count += 1
            except (TaskNotFoundError, BarelyError) as e:
                console.print(f"[red]Error:[/red] {e}")

        if deleted_count > 1:
            bulk_msg = celebrate_bulk(deleted_count, "deleted")
            console.print(f"[green]{bulk_msg}[/green]")

    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def handle_edit_command(result: ParseResult) -> None:
    """
    Handle 'edit' command - update task title.

    Args:
        result: Parsed command with args and flags

    Usage:
        edit 42 New title
        edit 42 "Title with spaces"
        edit <new_title>      (shows picker for task selection)
    """
    if not result.args:
        console.print("[red]Error:[/red] Task ID and new title required")
        console.print("[dim]Usage: edit <task_id> <new_title> OR edit <new_title> (shows picker)[/dim]")
        return

    # Try to parse first arg as task ID
    try:
        task_id = int(result.args[0])
        # Traditional usage: edit <id> <title>
        if len(result.args) < 2:
            console.print("[red]Error:[/red] New title required")
            console.print("[dim]Usage: edit <task_id> <new_title>[/dim]")
            return

        # Join remaining args as new title
        new_title = " ".join(result.args[1:])
        
        # Get original title before update (for undo)
        original_task = repository.get_task(task_id)
        original_title = original_task.title if original_task else ""
        
        task = service.update_task_title(task_id, new_title)
        
        # Record for undo
        record_update_title(task_id, original_title, new_title)
        
        display_task(task, "✎ Updated:", console)

    except ValueError:
        # First arg is not a number - treat entire input as new title, show picker
        new_title = " ".join(result.args)

        task_ids = pick_task(title="Select task to edit")
        if task_ids is None:
            return  # User cancelled

        # Edit only supports single task - use first if multiple selected
        if len(task_ids) > 1:
            console.print(f"[yellow]Note:[/yellow] Edit only updates one task - using first selection")

        task_id = task_ids[0]

        try:
            # Get original title before update (for undo)
            original_task = repository.get_task(task_id)
            original_title = original_task.title if original_task else ""
            
            task = service.update_task_title(task_id, new_title)
            
            # Record for undo
            record_update_title(task_id, original_title, new_title)
            
            display_task(task, "✎ Updated:", console)
        except TaskNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
        except InvalidInputError as e:
            console.print(f"[red]Error:[/red] {e}")
        except BarelyError as e:
            console.print(f"[red]Unexpected error:[/red] {e}")
        return

    except TaskNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
    except InvalidInputError as e:
        console.print(f"[red]Error:[/red] {e}")
    except BarelyError as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def handle_desc_command(result: ParseResult) -> None:
    """
    Handle 'desc' command - edit task description in $EDITOR.

    Args:
        result: Parsed command with args and flags

    Usage:
        desc 42                (opens editor for task 42)
        desc                   (shows picker for task selection)
    """
    import os
    import tempfile
    import subprocess

    # Get task ID
    task_id = None
    if result.args:
        try:
            task_id = int(result.args[0])
        except ValueError:
            console.print("[red]Error:[/red] Invalid task ID")
            console.print("[dim]Usage: desc <task_id> OR desc (shows picker)[/dim]")
            return
    else:
        # No ID provided, show picker
        task_ids = pick_task(title="Select task to edit description")
        if task_ids is None:
            return  # User cancelled

        # desc only supports single task - use first if multiple selected
        if len(task_ids) > 1:
            console.print(f"[yellow]Note:[/yellow] Editing description for first selected task only")

        task_id = task_ids[0]

    try:
        # Get the task to edit
        task = repository.get_task(task_id)
        if not task:
            console.print(f"[red]Error:[/red] Task {task_id} not found")
            return

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
        console.print(f"[red]Error:[/red] {e}")
    except subprocess.CalledProcessError:
        console.print(f"[red]Error:[/red] Editor was closed without saving")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


def handle_show_command(result: ParseResult) -> None:
    """
    Handle 'show' command - display full task details including description.

    Args:
        result: Parsed command with args and flags

    Usage:
        show 42                (show full details for task 42)
        show                   (shows picker for task selection)
    """
    # Get task ID
    task_id = None
    if result.args:
        try:
            task_id = int(result.args[0])
        except ValueError:
            console.print("[red]Error:[/red] Invalid task ID")
            console.print("[dim]Usage: show <task_id> OR show (shows picker)[/dim]")
            return
    else:
        # No ID provided, show picker
        task_ids = pick_task(title="Select task to view")
        if task_ids is None:
            return  # User cancelled

        # show only supports single task - use first if multiple selected
        if len(task_ids) > 1:
            console.print(f"[yellow]Note:[/yellow] Showing first selected task only")

        task_id = task_ids[0]

    try:
        task = repository.get_task(task_id)
        if not task:
            console.print(f"[red]Error:[/red] Task {task_id} not found")
            return

        # Get project name if exists
        project_name = None
        if task.project_id:
            project = service.get_project(task.project_id)
            project_name = project.name if project else f"#{task.project_id}"

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
        created_rel = format_relative(task.created_at) if task.created_at else ""
        details.append(f"{created_rel}\n", style="white")

        if task.completed_at:
            details.append(f"Completed: ", style="dim")
            completed_rel = format_relative(task.completed_at)
            details.append(f"{completed_rel}\n", style="green")

        panel = Panel(details, border_style="blue", padding=(1, 2))
        console.print(panel)

    except BarelyError as e:
        console.print(f"[red]Error:[/red] {e}")


def handle_mv_command(result: ParseResult) -> None:
    """
    Handle 'mv' command - move task to different column.

    Args:
        result: Parsed command with args and flags

    Usage:
        mv 42 "In Progress"
        mv 42 Done
        mv <column_name>      (shows picker for task selection)
    """
    if not result.args:
        console.print("[red]Error:[/red] Task ID and column name required")
        console.print("[dim]Usage: mv <task_id> <column_name> OR mv <column_name> (shows picker)[/dim]")
        return

    # Try to parse first arg as task ID
    try:
        task_id = int(result.args[0])
        # Traditional usage: mv <id> <column>
        if len(result.args) < 2:
            console.print("[red]Error:[/red] Column name required")
            console.print("[dim]Usage: mv <task_id> <column_name>[/dim]")
            return

        # Join remaining args as column name
        column_name = " ".join(result.args[1:])

        # Look up column by name
        try:
            column = service.find_column_by_name_or_raise(column_name)
        except InvalidInputError as e:
            console.print(f"[red]Error:[/red] {e}")
            return

        # Move task
        # Get original column before move (for undo)
        original_task = repository.get_task(task_id)
        original_column_id = original_task.column_id if original_task else 1
        
        task = service.move_task(task_id, column.id)
        
        # Record for undo
        record_mv(task_id, original_column_id, column.id)
        
        display_task(task, f"→ Moved to {column.name}:", console)

    except ValueError:
        # First arg is not a number - treat entire input as column name, show picker
        column_name = " ".join(result.args)

        # Look up column by name first
        try:
            column = service.find_column_by_name_or_raise(column_name)
        except InvalidInputError as e:
            console.print(f"[red]Error:[/red] {e}")
            return

        # Show picker for task(s)
        task_ids = pick_task(title=f"Move task(s) to '{column.name}'")
        if task_ids is None:
            return  # User cancelled

        # Move tasks (supports bulk selection)
        moved_count = 0
        for task_id in task_ids:
            try:
                # Get original column before move (for undo)
                original_task = repository.get_task(task_id)
                original_column_id = original_task.column_id if original_task else 1
                
                task = service.move_task(task_id, column.id)
                
                # Record for undo (only track last operation)
                record_mv(task_id, original_column_id, column.id)
                
                display_task(task, f"→ Moved to {column.name}:", console)
                moved_count += 1
            except TaskNotFoundError as e:
                console.print(f"[red]Error:[/red] {e}")
            except ColumnNotFoundError as e:
                console.print(f"[red]Error:[/red] {e}")
            except BarelyError as e:
                console.print(f"[red]Unexpected error:[/red] {e}")

        if moved_count > 1:
            console.print(f"[green]✓ Moved {moved_count} tasks to {column.name}[/green]")
        return

    except TaskNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
    except ColumnNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
    except BarelyError as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def handle_assign_command(result: ParseResult) -> None:
    """
    Handle 'assign' command - assign task to project.

    Args:
        result: Parsed command with args and flags

    Usage:
        assign 42 "Work"
        assign 42 Personal
        assign <project>      (shows picker for task selection)
    """
    if not result.args:
        console.print("[red]Error:[/red] Task ID and project name required")
        console.print("[dim]Usage: assign <task_id> <project_name> OR assign <project_name> (shows picker)[/dim]")
        return

    # Try to parse first arg as task ID
    try:
        task_id = int(result.args[0])
        # Traditional usage: assign <id> <project>
        if len(result.args) < 2:
            console.print("[red]Error:[/red] Project name required")
            console.print("[dim]Usage: assign <task_id> <project_name>[/dim]")
            return

        # Join remaining args as project name
        project_name = " ".join(result.args[1:])

        # Look up project by name (case-insensitive)
        try:
            project = service.find_project_by_name_or_raise(project_name)
        except InvalidInputError as e:
            console.print(f"[red]Error:[/red] {e}")
            return

        # Assign task to project
        task = service.assign_task_to_project(task_id, project.id)
        display_task(task, f"→ Assigned to {project.name}:", console)

    except ValueError:
        # First arg is not a number - treat entire input as project name, show picker
        project_name = " ".join(result.args)

        # Look up project by name first
        try:
            project = service.find_project_by_name_or_raise(project_name)
        except InvalidInputError as e:
            console.print(f"[red]Error:[/red] {e}")
            return

        # Show picker for task(s)
        task_ids = pick_task(title=f"Assign task(s) to '{project.name}'")
        if task_ids is None:
            return  # User cancelled

        # Assign tasks (supports bulk selection)
        assigned_count = 0
        for task_id in task_ids:
            try:
                task = service.assign_task_to_project(task_id, project.id)
                display_task(task, f"→ Assigned to {project.name}:", console)
                assigned_count += 1
            except TaskNotFoundError as e:
                console.print(f"[red]Error:[/red] {e}")
            except ProjectNotFoundError as e:
                console.print(f"[red]Error:[/red] {e}")
            except BarelyError as e:
                console.print(f"[red]Unexpected error:[/red] {e}")

        if assigned_count > 1:
            console.print(f"[green]✓ Assigned {assigned_count} tasks to {project.name}[/green]")
        return

    except TaskNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
    except ProjectNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
    except BarelyError as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
