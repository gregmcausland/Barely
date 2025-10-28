"""
FILE: barely/core/models.py
PURPOSE: Domain models for tasks, projects, and columns
EXPORTS:
  - Task (dataclass)
  - Project (dataclass)
  - Column (dataclass)
DEPENDENCIES:
  - dataclasses (stdlib)
  - json (stdlib)
  - typing (stdlib)
NOTES:
  - All models have from_row() for SQLite row conversion
  - All models have to_json() for serialization
  - Optional fields use None as default
  - Timestamps stored as ISO-8601 strings
"""

from dataclasses import dataclass, asdict
from typing import Optional
import json


@dataclass
class Task:
    """A task with title, description, and workflow tracking."""

    id: int
    title: str
    column_id: int
    status: str = "todo"
    scope: str = "backlog"
    description: Optional[str] = None
    project_id: Optional[int] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "Task":
        """Convert SQLite row to Task object."""
        # Handle scope field with backwards compatibility
        try:
            scope = row["scope"]
        except (KeyError, IndexError):
            scope = "backlog"  # Default for old databases without scope field

        return cls(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            project_id=row["project_id"],
            column_id=row["column_id"],
            status=row["status"],
            scope=scope,
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            updated_at=row["updated_at"],
        )

    def to_json(self) -> str:
        """Serialize task to JSON string."""
        return json.dumps(asdict(self), indent=2)


@dataclass
class Project:
    """A project for organizing related tasks."""

    id: int
    name: str
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "Project":
        """Convert SQLite row to Project object."""
        return cls(
            id=row["id"],
            name=row["name"],
            created_at=row["created_at"],
        )

    def to_json(self) -> str:
        """Serialize project to JSON string."""
        return json.dumps(asdict(self), indent=2)


@dataclass
class Column:
    """A workflow column (e.g., Todo, In Progress, Done)."""

    id: int
    name: str
    position: int = 0

    @classmethod
    def from_row(cls, row) -> "Column":
        """Convert SQLite row to Column object."""
        return cls(
            id=row["id"],
            name=row["name"],
            position=row["position"],
        )

    def to_json(self) -> str:
        """Serialize column to JSON string."""
        return json.dumps(asdict(self), indent=2)
