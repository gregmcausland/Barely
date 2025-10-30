"""
FILE: barely/formatting.py
PURPOSE: Shared formatting utilities for CLI and REPL output
EXPORTS:
  - TaskFormatter: Class for formatting tasks
  - format_task_ids: Parse comma-separated task IDs
DEPENDENCIES:
  - rich (for table formatting)
  - json (for JSON serialization)
  - typing (type hints)
  - barely.core.models (Task, Project)
NOTES:
  - Centralized formatting logic for consistency
  - Used by both CLI and REPL
  - Avoids duplication of formatting code
"""

import json
from typing import List, Optional, Dict, Any
from rich.table import Table
from rich.text import Text

from .core.models import Task, Project


class TaskFormatter:
    """Centralized task display formatting."""

    @staticmethod
    def create_table(
        tasks: List[Task],
        title: str = "Tasks",
        show_project: bool = True,
        show_column: bool = False,
        show_scope: bool = True,
    ) -> Table:
        """
        Create Rich table for tasks.

        Args:
            tasks: List of tasks to display
            title: Table title
            show_project: Whether to show project column
            show_column: Whether to show column ID column
            show_scope: Whether to show scope column

        Returns:
            Rich Table object ready for display
        """
        table = Table(title=title, show_header=True, header_style="bold cyan")
        table.add_column("ID", style="cyan", width=6, no_wrap=True)
        table.add_column("Title", style="white")

        if show_scope:
            table.add_column("Scope", style="magenta", width=10)

        if show_project:
            table.add_column("Project", style="yellow", width=12)

        if show_column:
            table.add_column("Column", style="blue")

        # Build project name cache for efficient lookups
        project_cache = {}
        if show_project:
            project_ids = {task.project_id for task in tasks if task.project_id}
            for proj_id in project_ids:
                # Import here to avoid circular dependency
                from .core import service
                project = service.get_project(proj_id)
                if project:
                    project_cache[proj_id] = project.name

        # Add rows
        for task in tasks:
            row_data = [str(task.id), task.title]

            if show_scope:
                # Color code scope
                scope_style_map = {
                    "backlog": "dim",
                    "week": "blue",
                    "today": "bright_magenta",
                    "archived": "green",
                }
                scope_style = scope_style_map.get(task.scope, "white")
                row_data.append(f"[{scope_style}]{task.scope}[/{scope_style}]")

            if show_project:
                if task.project_id:
                    project_name = project_cache.get(
                        task.project_id, f"[dim]ID:{task.project_id}[/dim]"
                    )
                else:
                    project_name = "-"
                row_data.append(project_name)

            if show_column:
                row_data.append(str(task.column_id))

            table.add_row(*row_data)

        return table

    @staticmethod
    def to_json_array(tasks: List[Task]) -> str:
        """
        Convert task list to JSON array string.

        Args:
            tasks: List of tasks to serialize

        Returns:
            JSON string with array of task objects
        """
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
        return json.dumps(tasks_data, indent=2)

    @staticmethod
    def to_json_dict(task: Task) -> Dict[str, Any]:
        """
        Convert single task to JSON-serializable dict.

        Args:
            task: Task to serialize

        Returns:
            Dictionary with task data
        """
        return {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "scope": task.scope,
            "column_id": task.column_id,
            "project_id": task.project_id,
            "description": task.description,
            "created_at": task.created_at,
            "completed_at": task.completed_at,
            "updated_at": task.updated_at,
        }

    @staticmethod
    def to_raw_lines(tasks: List[Task]) -> List[str]:
        """
        Convert task list to plain text lines.

        Args:
            tasks: List of tasks to format

        Returns:
            List of formatted strings, one per task
        """
        lines = []
        for task in tasks:
            status_marker = "✓" if task.scope == "archived" else " "
            lines.append(f"{task.id}: [{status_marker}] {task.title}")
        return lines


def parse_task_ids(id_string: str) -> List[int]:
    """
    Parse comma-separated task IDs.

    Args:
        id_string: Comma-separated string of IDs (e.g., "1,2,3")

    Returns:
        List of integers

    Raises:
        ValueError: If any ID is not a valid integer
    """
    ids = [id.strip() for id in id_string.split(",")]
    return [int(id) for id in ids if id]


def parse_project_ids(id_string: str) -> List[int]:
    """
    Parse comma-separated project IDs.

    Args:
        id_string: Comma-separated string of IDs (e.g., "1,2,3")

    Returns:
        List of integers

    Raises:
        ValueError: If any ID is not a valid integer
    """
    ids = [id.strip() for id in id_string.split(",")]
    return [int(id) for id in ids if id]

