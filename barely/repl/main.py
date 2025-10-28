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
from .parser import parse_command, ParseResult
from .completer import create_completer
from . import style
from . import blitz
from . import pickers


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
        current_scope: Current scope filter ('today', 'week', 'backlog', or None for all)
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


def display_task(task: Task, message: str = "") -> None:
    """
    Display a single task with optional message.

    Args:
        task: Task object to display
        message: Optional message to show before task (e.g., "Created:")
    """
    if message:
        console.print(f"[green]{message}[/green]")

    console.print(f"  [cyan]{task.id}[/cyan]: {task.title} [dim]({task.status})[/dim]")


def display_tasks_table(tasks: list[Task]) -> None:
    """
    Display tasks in a formatted table.

    Args:
        tasks: List of Task objects to display
    """
    if not tasks:
        console.print("[dim]No tasks found[/dim]")
        return

    # Build project name cache for efficient lookups
    project_cache = {}
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
    table.add_column("Project", style="yellow", width=12)

    # Add rows for each task
    for task in tasks:
        # Resolve project name from cache
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

        table.add_row(
            str(task.id),
            task.title,
            f"[{scope_style}]{task.scope}[/{scope_style}]",
            project_name,
        )

    console.print(table)


def pick_task(title: str = "Select a task", filter_status: Optional[str] = None) -> Optional[List[int]]:
    """
    Show simple task picker filtered by current context.

    Args:
        title: Title for the picker
        filter_status: Optional status filter (e.g., "todo" for done command)

    Returns:
        List of selected task IDs or None if cancelled

    The picker shows only tasks that match the current REPL context
    (project and scope filters), making it easy to find relevant tasks.

    Displays a numbered list inline and prompts for selection.
    Supports comma-separated numbers for bulk operations (e.g., "1,3,5").
    """
    try:
        # Get all tasks
        tasks = service.list_tasks()

        # Apply context filtering
        if repl_context.current_project:
            tasks = [t for t in tasks if t.project_id == repl_context.current_project.id]
        if repl_context.current_scope:
            tasks = [t for t in tasks if t.scope == repl_context.current_scope]

        # Apply status filter if provided
        if filter_status:
            tasks = [t for t in tasks if t.status == filter_status]

        if not tasks:
            console.print("[yellow]No tasks available in current context[/yellow]")
            console.print("[dim]Tip: Use 'use' or 'scope' to change context, or specify task ID directly[/dim]")
            return None

        # Try compact overlay picker first (multi-select)
        selection = pickers.pick_tasks_overlay(title, tasks, multi=True)
        if selection:
            return selection

        # Limit to 20 tasks for readability in inline fallback
        tasks = tasks[:20]

        # Show title (fallback)
        console.print(f"\n[bold cyan]{title}[/bold cyan]")

        # Display numbered list
        for idx, task in enumerate(tasks, 1):
            # Color code scope
            scope_colors = {
                "today": "bright_magenta",
                "week": "blue",
                "backlog": "dim"
            }
            scope_color = scope_colors.get(task.scope, "white")
            scope_display = f"[{scope_color}]{task.scope}[/{scope_color}]"

            # Build display line
            console.print(f"  [{idx}] {task.title} [dim](id:{task.id}, {scope_display})[/dim]")

        # Prompt for selection (fallback)
        console.print()
        try:
            selection = input("Select number(s) - use commas for multiple (or press Enter to cancel): ").strip()

            if not selection:
                return None

            # Parse comma-separated selections
            selections = [s.strip() for s in selection.split(",")]
            task_ids = []

            for sel in selections:
                try:
                    selection_num = int(sel)
                    if 1 <= selection_num <= len(tasks):
                        selected_task = tasks[selection_num - 1]
                        task_ids.append(selected_task.id)
                    else:
                        console.print(f"[red]Error:[/red] Number {selection_num} out of range (1-{len(tasks)})")
                        return None
                except ValueError:
                    console.print(f"[red]Error:[/red] Invalid number: {sel}")
                    return None

            return task_ids if task_ids else None

        except (KeyboardInterrupt, EOFError):
            console.print()
            return None

    except Exception as e:
        console.print(f"[red]Error showing picker:[/red] {e}")
        return None


def handle_add_command(result: ParseResult) -> None:
    """
    Handle 'add' command - create new task.

    Args:
        result: Parsed command with args and flags

    Usage:
        add Buy groceries
        add "Task with spaces"
    """
    # Get title from args
    if not result.args:
        console.print("[red]Error:[/red] Task title required")
        console.print("[dim]Usage: add <title>[/dim]")
        return

    # Join all args as the title (in case they didn't use quotes)
    title = " ".join(result.args)

    try:
        # Default to context project if set
        project_id = None
        if repl_context.current_project:
            project_id = repl_context.current_project.id

        task = service.create_task(title, project_id=project_id)

        # Celebrate!
        style.celebrate_add()

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
    Handle 'ls' command - list tasks (excludes completed by default).

    Args:
        result: Parsed command with args and flags

    Usage:
        ls
        ls --status todo
        ls --project "Work"
        ls --done              (include completed tasks)
    """
    # Get optional filters from flags
    status = result.flags.get("status")
    project_name = result.flags.get("project")
    include_done = result.flags.get("done", False)

    try:
        # Determine project filter (flag overrides context)
        project_id = None
        if project_name:
            # User explicitly specified --project, use that
            projects = service.list_projects()
            # Case-insensitive project name matching
            project = next((p for p in projects if p.name.lower() == project_name.lower()), None)
            if not project:
                console.print(f"[red]Error:[/red] Project '{project_name}' not found")
                console.print("\n[dim]Available projects:[/dim]")
                for p in projects:
                    console.print(f"  - {p.name}")
                return
            project_id = project.id
        elif repl_context.current_project:
            # No flag, but context is set - use context
            project_id = repl_context.current_project.id

        # Get tasks with filters
        tasks = service.list_tasks(project_id=project_id, status=status, include_done=include_done)

        # Apply scope filter from context if set
        if repl_context.current_scope:
            tasks = [t for t in tasks if t.scope == repl_context.current_scope]

        display_tasks_table(tasks)
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
        # No args - show picker for todo tasks
        task_ids = pick_task(title="Mark task as done", filter_status="todo")
        if task_ids is None:
            return  # User cancelled

        # Process tasks from picker (supports bulk selection)
        completed_count = 0
        for task_id in task_ids:
            try:
                task = service.complete_task(task_id)
                style.celebrate_done()
                display_task(task, "✓ Completed:")
                completed_count += 1
            except TaskNotFoundError as e:
                console.print(f"[red]Error:[/red] {e}")
            except BarelyError as e:
                console.print(f"[red]Error:[/red] {e}")

        if completed_count > 1:
            bulk_msg = style.celebrate_bulk(completed_count, "completed")
            console.print(f"[green]{bulk_msg}[/green]")
        return

    try:
        # Parse comma-separated IDs
        ids = [id.strip() for id in result.args[0].split(",")]
        completed_count = 0

        for id_str in ids:
            try:
                task_id = int(id_str)
                task = service.complete_task(task_id)
                style.celebrate_done()
                display_task(task, "✓ Completed:")
                completed_count += 1
            except ValueError:
                console.print(f"[red]Error:[/red] Invalid task ID: {id_str}")
            except TaskNotFoundError as e:
                console.print(f"[red]Error:[/red] {e}")
            except BarelyError as e:
                console.print(f"[red]Error:[/red] {e}")

        if completed_count > 1:
            bulk_msg = style.celebrate_bulk(completed_count, "completed")
            console.print(f"[green]{bulk_msg}[/green]")
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


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
                service.delete_task(task_id)
                style.celebrate_delete()
                console.print(f"[green]✓ Deleted task {task_id}[/green]")
                deleted_count += 1
            except TaskNotFoundError as e:
                console.print(f"[red]Error:[/red] {e}")
            except BarelyError as e:
                console.print(f"[red]Error:[/red] {e}")

        if deleted_count > 1:
            bulk_msg = style.celebrate_bulk(deleted_count, "deleted")
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

            style.celebrate_delete()
            bulk_msg = style.celebrate_bulk(deleted_count, "deleted")
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
                service.delete_task(task_id)
                style.celebrate_delete()
                console.print(f"[green]✓ Deleted task {task_id}[/green]")
                deleted_count += 1
            except (TaskNotFoundError, BarelyError) as e:
                console.print(f"[red]Error:[/red] {e}")

        if deleted_count > 1:
            bulk_msg = style.celebrate_bulk(deleted_count, "deleted")
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
        task = service.update_task_title(task_id, new_title)
        display_task(task, "✎ Updated:")

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
            task = service.update_task_title(task_id, new_title)
            display_task(task, "✎ Updated:")
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
        created_rel = style.format_relative(task.created_at) if task.created_at else ""
        details.append(f"{created_rel}\n", style="white")

        if task.completed_at:
            details.append(f"Completed: ", style="dim")
            completed_rel = style.format_relative(task.completed_at)
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
        column = repository.get_column_by_name(column_name)
        if not column:
            console.print(f"[red]Error:[/red] Column '{column_name}' not found")
            console.print("\n[dim]Available columns:[/dim]")
            columns = service.list_columns()
            for col in columns:
                console.print(f"  - {col.name}")
            return

        # Move task
        task = service.move_task(task_id, column.id)
        display_task(task, f"→ Moved to {column.name}:")

    except ValueError:
        # First arg is not a number - treat entire input as column name, show picker
        column_name = " ".join(result.args)

        # Look up column by name first
        column = repository.get_column_by_name(column_name)
        if not column:
            console.print(f"[red]Error:[/red] Column '{column_name}' not found")
            console.print("\n[dim]Available columns:[/dim]")
            columns = service.list_columns()
            for col in columns:
                console.print(f"  - {col.name}")
            return

        # Show picker for task(s)
        task_ids = pick_task(title=f"Move task(s) to '{column.name}'")
        if task_ids is None:
            return  # User cancelled

        # Move tasks (supports bulk selection)
        moved_count = 0
        for task_id in task_ids:
            try:
                task = service.move_task(task_id, column.id)
                display_task(task, f"→ Moved to {column.name}:")
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
        projects = service.list_projects()
        project = next((p for p in projects if p.name.lower() == project_name.lower()), None)
        if not project:
            console.print(f"[red]Error:[/red] Project '{project_name}' not found")
            console.print("\n[dim]Available projects:[/dim]")
            for p in projects:
                console.print(f"  - {p.name}")
            return

        # Assign task to project
        task = service.assign_task_to_project(task_id, project.id)
        display_task(task, f"→ Assigned to {project.name}:")

    except ValueError:
        # First arg is not a number - treat entire input as project name, show picker
        project_name = " ".join(result.args)

        # Look up project by name first
        projects = service.list_projects()
        project = next((p for p in projects if p.name.lower() == project_name.lower()), None)
        if not project:
            console.print(f"[red]Error:[/red] Project '{project_name}' not found")
            console.print("\n[dim]Available projects:[/dim]")
            for p in projects:
                console.print(f"  - {p.name}")
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
                display_task(task, f"→ Assigned to {project.name}:")
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


# --- Pull-Based Workflow Commands ---


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
        display_tasks_table(tasks)
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
        display_tasks_table(tasks)
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
        display_tasks_table(tasks)
    except BarelyError as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def handle_history_command(result: ParseResult) -> None:
    """
    Handle 'history' command - view completed tasks.

    Args:
        result: Parsed command with args and flags

    Usage:
        history
    """
    try:
        tasks = service.list_completed()

        # Filter by context project if set
        if repl_context.current_project:
            tasks = [t for t in tasks if t.project_id == repl_context.current_project.id]

        if not tasks:
            console.print("[dim]No completed tasks[/dim]")
            return

        console.print("[bold cyan]History[/bold cyan]")
        display_tasks_table(tasks)
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
    valid_scopes = ("backlog", "week", "today")

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
    scope_emoji = {"backlog": "📋", "week": "📅", "today": "⭐"}

    for task_id in task_ids:
        try:
            task = service.pull_task(task_id, scope)
            style.celebrate_pull()
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
        bulk_msg = style.celebrate_bulk(pulled_count, f"pulled into {scope}")
        console.print(f"[green]{bulk_msg}[/green]")


def handle_project_add_command(result: ParseResult) -> None:
    """
    Handle 'project add' command - create new project.

    Args:
        result: Parsed command with args and flags

    Usage:
        project add Work
        project add "My Project"
    """
    if not result.args:
        console.print("[red]Error:[/red] Project name required")
        console.print("[dim]Usage: project add <name>[/dim]")
        return

    # Join all args as the name
    name = " ".join(result.args)

    try:
        project = service.create_project(name)
        console.print(f"[green]✓ Created project:[/green] [cyan]{project.id}[/cyan]: {project.name}")
    except InvalidInputError as e:
        console.print(f"[red]Error:[/red] {e}")
    except BarelyError as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def handle_project_ls_command(result: ParseResult) -> None:
    """
    Handle 'project ls' command - list projects.

    Args:
        result: Parsed command with args and flags

    Usage:
        project ls
    """
    try:
        projects = service.list_projects()

        if not projects:
            console.print("[dim]No projects found[/dim]")
            return

        # Create table with columns
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("ID", style="cyan", width=6)
        table.add_column("Name", style="white")
        table.add_column("Created", style="dim")

        # Add rows for each project
        for project in projects:
            # Show relative created time if available
            created_display = style.format_relative(project.created_at) if project.created_at else ""

            table.add_row(
                str(project.id),
                project.name,
                created_display,
            )

        console.print(table)
    except BarelyError as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def handle_project_rm_command(result: ParseResult) -> None:
    """
    Handle 'project rm' command - delete project(s).

    Supports:
    - project rm 42          - delete single project
    - project rm 1,2,3       - delete multiple projects
    - project rm *           - delete all projects

    Always confirms before deleting multiple projects.

    Args:
        result: Parsed command with args and flags

    Usage:
        project rm 42
        project rm 1,2,3
        project rm *
    """
    if not result.args:
        console.print("[red]Error:[/red] Project ID(s) required")
        console.print("[dim]Usage: project rm <project_id>[,<project_id>...] or project rm '*'[/dim]")
        return

    try:
        arg = result.args[0].strip()

        # Handle wildcard: delete all projects
        if arg == "*":
            all_projects = service.list_projects()

            if not all_projects:
                console.print("[yellow]No projects to delete[/yellow]")
                return

            # Confirm deletion
            if not ask_confirmation(f"Delete {len(all_projects)} projects?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

            # Delete all in batch
            deleted_count = 0
            for project in all_projects:
                try:
                    service.delete_project(project.id)
                    deleted_count += 1
                except (ProjectNotFoundError, BarelyError) as e:
                    console.print(f"[red]Error deleting project {project.id}:[/red] {e}")

            if deleted_count > 0:
                console.print("[dim]Tasks in these projects now have no project assigned[/dim]")
            bulk_msg = style.celebrate_bulk(deleted_count, "deleted")
            console.print(f"[green]{bulk_msg}[/green]")
            return

        # Parse comma-separated IDs
        ids = [id.strip() for id in arg.split(",")]

        # Collect valid project IDs
        all_projects = service.list_projects()
        project_dict = {p.id: p for p in all_projects}

        projects_to_delete = []
        invalid_ids = []

        for id_str in ids:
            try:
                project_id = int(id_str)

                # Check if project exists
                if project_id not in project_dict:
                    invalid_ids.append((id_str, "not found"))
                else:
                    projects_to_delete.append(project_id)
            except ValueError:
                invalid_ids.append((id_str, "invalid ID"))

        # Report invalid IDs
        for id_str, reason in invalid_ids:
            console.print(f"[yellow]Warning:[/yellow] Project {id_str} - {reason}")

        if not projects_to_delete:
            console.print("[yellow]No valid projects to delete[/yellow]")
            return

        # Confirm deletion for multiple projects
        if len(projects_to_delete) > 1:
            if not ask_confirmation(f"Delete {len(projects_to_delete)} projects?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        # Delete projects
        deleted_count = 0
        for project_id in projects_to_delete:
            try:
                service.delete_project(project_id)
                console.print(f"[green]✓ Deleted project {project_id}[/green]")
                deleted_count += 1
            except (ProjectNotFoundError, BarelyError) as e:
                console.print(f"[red]Error:[/red] {e}")

        if deleted_count > 0:
            console.print("[dim]Tasks in these projects now have no project assigned[/dim]")
        if deleted_count > 1:
            bulk_msg = style.celebrate_bulk(deleted_count, "deleted")
            console.print(f"[green]{bulk_msg}[/green]")

    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def handle_project_command(result: ParseResult) -> None:
    """
    Handle 'project' command - dispatch to subcommand.

    Args:
        result: Parsed command with args and flags

    Usage:
        project add <name>
        project ls
        project rm <id>
    """
    if not result.args:
        console.print("[red]Error:[/red] Project subcommand required")
        console.print("[dim]Usage: project <add|ls|rm> ...[/dim]")
        return

    subcommand = result.args[0].lower()
    # Create new ParseResult with subcommand as command and rest as args
    sub_result = ParseResult(subcommand, result.args[1:], result.flags)

    handlers = {
        "add": handle_project_add_command,
        "ls": handle_project_ls_command,
        "rm": handle_project_rm_command,
    }

    handler = handlers.get(subcommand)
    if handler:
        handler(sub_result)
    else:
        console.print(f"[red]Unknown project command:[/red] {subcommand}")
        console.print("[dim]Available: add, ls, rm[/dim]")


# --- Context Management Commands ---


def handle_use_command(result: ParseResult) -> None:
    """
    Handle 'use' command - set current working project.

    Args:
        result: Parsed command with args and flags

    Usage:
        use                 # Show current project
        use work            # Set to Work project
        use none            # Clear project context
    """
    if not result.args:
        # Show current context
        if repl_context.current_project:
            console.print(f"Current project: [cyan]{repl_context.current_project.name}[/cyan]")
        else:
            console.print("[dim]No project context set (showing all projects)[/dim]")
        return

    project_name = result.args[0]

    # Clear context
    if project_name.lower() in ("none", "clear", "."):
        repl_context.current_project = None
        console.print("✓ Cleared project context")
        return

    # Set project
    try:
        projects = service.list_projects()
        project = next((p for p in projects if p.name.lower() == project_name.lower()), None)

        if not project:
            console.print(f"[red]Error:[/red] Project '{project_name}' not found")
            console.print("\n[dim]Available projects:[/dim]")
            for p in projects:
                console.print(f"  - {p.name}")
            return

        repl_context.current_project = project
        console.print(f"✓ Now working in project: [cyan]{project.name}[/cyan]")

    except BarelyError as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def handle_scope_command(result: ParseResult) -> None:
    """
    Handle 'scope' command - set current scope filter.

    Args:
        result: Parsed command with args and flags

    Usage:
        scope               # Show current scope
        scope today         # Filter to today
        scope week          # Filter to week
        scope backlog       # Filter to backlog
        scope all           # Clear scope filter
    """
    if not result.args:
        # Show current scope
        if repl_context.current_scope:
            console.print(f"Current scope: [cyan]{repl_context.current_scope}[/cyan]")
        else:
            console.print("[dim]No scope filter (showing all scopes)[/dim]")
        return

    scope_name = result.args[0].lower()

    # Clear scope filter
    if scope_name in ("all", "none", "clear"):
        repl_context.current_scope = None
        console.print("✓ Cleared scope filter")
        return

    # Validate scope
    valid_scopes = ("today", "week", "backlog")
    if scope_name not in valid_scopes:
        console.print(f"[red]Error:[/red] Invalid scope '{scope_name}'")
        console.print(f"[dim]Valid scopes: {', '.join(valid_scopes)}, all[/dim]")
        return

    repl_context.current_scope = scope_name
    console.print(f"✓ Filtering to [cyan]{scope_name}[/cyan] tasks")


def handle_help_command(result: ParseResult) -> None:
    """
    Handle 'help' command - show available commands.

    Args:
        result: Parsed command (unused)
    """
    help_text = """
[bold cyan]Available Commands:[/bold cyan]

  [cyan]add <title>[/cyan]              Create a new task
  [cyan]ls [--status <status>] [--project <name>] [--done][/cyan]   List tasks
  [cyan]done [<id>[,<id>...]][/cyan]    Mark task(s) as complete (picker if no ID)
  [cyan]rm [<id>[,<id>...]][/cyan]      Delete task(s) (picker if no ID)
  [cyan]edit [<id>] <title>[/cyan]      Update task title (picker if no ID)
  [cyan]desc [<id>][/cyan]              Edit task description in $EDITOR (picker if no ID)
  [cyan]show [<id>][/cyan]              View full task details (picker if no ID)
  [cyan]mv [<id>] <column>[/cyan]       Move task to column (picker if no ID)
  [cyan]assign [<id>] <project>[/cyan]  Assign task to project (picker if no ID)
  [cyan]today[/cyan]                    List today's tasks
  [cyan]week[/cyan]                     List this week's tasks
  [cyan]backlog[/cyan]                  List backlog tasks
  [cyan]history[/cyan]                  View completed tasks
  [cyan]pull [<id>[,<id>...]] [scope][/cyan] Pull tasks into scope (defaults to today)
  [cyan]blitz[/cyan]                    Enter focused completion mode (with audio viz!)
  [cyan]use <project>[/cyan]           Set current working project
  [cyan]scope <scope>[/cyan]           Set current scope filter
  [cyan]project add <name>[/cyan]       Create a project
  [cyan]project ls[/cyan]               List projects
  [cyan]project rm <id>[,<id>...][/cyan] Delete project(s)
  [cyan]help[/cyan]                     Show this help
  [cyan]clear[/cyan]                    Clear the screen
  [cyan]exit[/cyan] or [cyan]quit[/cyan]            Exit REPL

[bold cyan]Flags:[/bold cyan]

  [cyan]--status <status>[/cyan]        Filter by status (todo, done, archived)
  [cyan]--project <name>[/cyan]         Filter by project name
  [cyan]--done[/cyan]                   Include completed tasks in ls output

[bold cyan]Examples:[/bold cyan]

  [dim]add Buy groceries
  add "Task with spaces in title"
  ls
  ls --status todo
  ls --project Work
  done 42
  done                        # Shows picker for todo tasks
  done 1,2,3                  # Mark multiple tasks as done
  edit 42 Updated title
  edit Updated title          # Shows picker to select task
  rm 5,6,7                    # Delete multiple tasks
  mv Done                     # Shows picker to select task
  mv 42 "In Progress"
  assign 42 Work              # Assign task 42 to Work project
  assign Work                 # Shows picker to select task
  today                       # View today's focus list
  week                        # View this week's commitment
  backlog                     # View all backlog tasks
  pull 3,5,7                  # Pull tasks into today (default)
  pull                        # Shows picker for today scope
  pull 42 week                # Pull specific task into week
  pull week                   # Shows picker for week scope
  pull 10 backlog             # Defer task to backlog
  blitz                       # Enter focused mode with audio viz
  use Work                    # Set current project to Work
  scope today                 # Filter to today's tasks
  use none                    # Clear project context
  scope all                   # Clear scope filter
  project add Work
  project ls
  project rm 2
  project rm 2,3,4            # Delete multiple projects[/dim]

[bold yellow]💡 Smart Pickers:[/bold yellow]
  [dim]Commands that need task IDs can show a numbered picker when you
  omit the ID. Pickers are filtered by your current context (project/scope),
  making it easy to find tasks. Enter a number to select, or use commas
  for bulk operations (e.g., "1,3,5" to select multiple).[/dim]
"""
    console.print(Panel(help_text, title="Barely REPL Help", border_style="cyan"))


def handle_clear_command(result: ParseResult) -> None:
    """
    Clear the screen.

    Args:
        result: Parsed command (no arguments used)
    """
    console.clear()
    console.print("[dim]Screen cleared[/dim]")


def handle_blitz_command(result: ParseResult) -> None:
    """
    Handle 'blitz' command - enter focused task completion mode.

    Args:
        result: Parsed command (no arguments used)

    Notes:
        - Displays tasks from current scope (or 'today' by default)
        - Respects current project filter if set
        - Shows live audio waveform visualization
        - Keyboard controls: d=done, s=skip, q=quit, ?=details
        - Returns to normal REPL when complete
    """
    # Pass REPL context to blitz mode
    project_id = repl_context.current_project.id if repl_context.current_project else None
    scope = repl_context.current_scope  # Could be None, will default to 'today'

    blitz.run_blitz_mode(project_id=project_id, scope=scope)


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
        "history": handle_history_command,
        "pull": handle_pull_command,
        "use": handle_use_command,
        "scope": handle_scope_command,
        "project": handle_project_command,
        "blitz": handle_blitz_command,
        "help": handle_help_command,
        "clear": handle_clear_command,
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
