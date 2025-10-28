"""
FILE: barely/core/exceptions.py
PURPOSE: Custom exception classes for error handling
EXPORTS:
  - BarelyError (base exception)
  - TaskNotFoundError
  - ProjectNotFoundError
  - ColumnNotFoundError
  - InvalidInputError
DEPENDENCIES:
  - None (stdlib only)
NOTES:
  - All exceptions inherit from BarelyError for easy catching
  - Exceptions include context (IDs, names) for helpful error messages
  - Service layer raises these, UI layers catch and display
"""


class BarelyError(Exception):
    """Base exception for all Barely errors."""
    pass


class TaskNotFoundError(BarelyError):
    """Task with given ID doesn't exist."""

    def __init__(self, task_id: int):
        self.task_id = task_id
        super().__init__(f"Task {task_id} not found")


class ProjectNotFoundError(BarelyError):
    """Project with given ID doesn't exist."""

    def __init__(self, project_id: int):
        self.project_id = project_id
        super().__init__(f"Project {project_id} not found")


class ColumnNotFoundError(BarelyError):
    """Column with given ID doesn't exist."""

    def __init__(self, column_id: int):
        self.column_id = column_id
        super().__init__(f"Column {column_id} not found")


class InvalidInputError(BarelyError):
    """Input validation failed."""

    def __init__(self, message: str):
        super().__init__(message)
