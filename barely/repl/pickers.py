"""
FILE: barely/repl/pickers.py
PURPOSE: Compact overlay pickers for REPL selections using prompt_toolkit dialogs
EXPORTS:
  - pick_tasks_overlay(title: str, tasks: list, multi: bool = True) -> list[int] | None
  - pick_single_task_overlay(title: str, tasks: list) -> int | None
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

