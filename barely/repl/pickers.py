"""
FILE: barely/repl/pickers.py
PURPOSE: Compact overlay pickers for REPL selections using prompt_toolkit dialogs
EXPORTS:
  - pick_tasks_overlay(title: str, tasks: list, multi: bool = True) -> list[int] | None
  - pick_single_task_overlay(title: str, tasks: list) -> int | None
  - pick_task(title: str, filter_scope: Optional[str] = None) -> Optional[List[int]]
DEPENDENCIES:
  - prompt_toolkit.shortcuts.dialogs (checkboxlist_dialog, radiolist_dialog)
  - typing (type hints)
NOTES:
  - Falls back gracefully by returning None if dialogs are unavailable
  - Labels include task title and brief scope tag
"""

from typing import List, Optional


def _task_label(task) -> str:
    title = (task.title or "").strip()
    title_short = title if len(title) <= 50 else title[:47] + "..."
    scope = task.scope or ""
    return f"{title_short}  [id:{task.id} • {scope}]"


def pick_tasks_overlay(title: str, tasks: List, multi: bool = True) -> Optional[List[int]]:
    """
    Show a compact overlay picker for tasks. Returns selected task IDs.

    Args:
        title: Dialog title
        tasks: List of Task objects
        multi: If True, allow multi-select
    """
    try:
        from prompt_toolkit.shortcuts.dialogs import (
            checkboxlist_dialog,
            radiolist_dialog,
        )
    except Exception:
        return None

    if not tasks:
        return None

    # Build choices as (value, label)
    if multi:
        choices = [(t.id, _task_label(t)) for t in tasks]
        result = checkboxlist_dialog(
            title=title,
            text="Select one or more tasks",
            values=choices,
            ok_text="OK",
            cancel_text="Cancel",
        ).run()
        return list(result) if result else None
    else:
        choices = [(t.id, _task_label(t)) for t in tasks]
        result = radiolist_dialog(
            title=title,
            text="Select a task",
            values=choices,
            ok_text="OK",
            cancel_text="Cancel",
        ).run()
        return [result] if result is not None else None


def pick_single_task_overlay(title: str, tasks: List) -> Optional[int]:
    ids = pick_tasks_overlay(title, tasks, multi=False)
    return ids[0] if ids else None


def pick_task(title: str = "Select a task", filter_scope: Optional[str] = None) -> Optional[List[int]]:
    """
    Show simple task picker filtered by current context.

    Args:
        title: Title for the picker
        filter_scope: Optional scope filter (e.g., "todo" for done command - now deprecated)

    Returns:
        List of selected task IDs or None if cancelled

    The picker shows only tasks that match the current REPL context
    (project and scope filters), making it easy to find relevant tasks.

    Displays a numbered list inline and prompts for selection.
    Supports comma-separated numbers for bulk operations (e.g., "1,3,5").
    """
    # Import here to avoid circular imports
    from ..core import service
    from .main import repl_context, console
    
    try:
        # Get all tasks
        tasks = service.list_tasks()

        # Apply context filtering
        if repl_context.current_project:
            tasks = [t for t in tasks if t.project_id == repl_context.current_project.id]
        if repl_context.current_scope:
            tasks = [t for t in tasks if t.scope == repl_context.current_scope]

        # Exclude archived tasks by default for picker (they're completed)
        tasks = [t for t in tasks if t.scope != "archived"]

        if not tasks:
            console.print("[yellow]No tasks available in current context[/yellow]")
            console.print("[dim]Tip: Use 'use' or 'scope' to change context, or specify task ID directly[/dim]")
            return None

        # Limit to 20 tasks for readability
        tasks = tasks[:20]

        # Show title
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

        # Prompt for selection
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
