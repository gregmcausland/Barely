"""
FILE: barely/repl/undo.py
PURPOSE: Undo history tracking and reversal for REPL operations
EXPORTS:
  - UndoOperation (dataclass)
  - UndoHistory (class)
  - record_operation() -> None
  - undo_last_operation() -> bool
DEPENDENCIES:
  - dataclasses (stdlib)
  - typing (stdlib)
  - barely.core.service (for reversing operations)
  - barely.core.exceptions (error handling)
NOTES:
  - Tracks last operation for undo
  - Only supports single undo (last operation only)
  - Session-scoped (not persisted)
  - Supports: create, delete, complete, update_title, pull, mv
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

from ..core import service, repository
from ..core.exceptions import BarelyError, TaskNotFoundError


@dataclass
class UndoOperation:
    """
    Represents a single operation that can be undone.
    
    Attributes:
        operation: Type of operation ('create', 'delete', 'complete', 'update_title', 'pull', 'mv')
        task_id: ID of task involved (or None for multi-task operations)
        original_data: Snapshot of task before operation (for restore)
        new_data: Snapshot of task after operation (for reference)
        timestamp: When the operation occurred
    """
    operation: str
    task_id: Optional[int]
    original_data: Dict[str, Any]
    new_data: Dict[str, Any]
    timestamp: str


class UndoHistory:
    """
    Manages undo history for REPL session.
    
    Tracks last operation and provides undo functionality.
    Only maintains last operation (no full history by design).
    """
    
    def __init__(self):
        self._last_operation: Optional[UndoOperation] = None
    
    def record_operation(
        self,
        operation: str,
        task_id: Optional[int],
        original_data: Optional[Dict[str, Any]] = None,
        new_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record an operation for potential undo.
        
        Args:
            operation: Type of operation ('create', 'delete', 'complete', etc.)
            task_id: ID of task involved
            original_data: Snapshot before operation (for restore)
            new_data: Snapshot after operation (for reference)
        """
        self._last_operation = UndoOperation(
            operation=operation,
            task_id=task_id,
            original_data=original_data or {},
            new_data=new_data or {},
            timestamp=datetime.now().isoformat()
        )
    
    def can_undo(self) -> bool:
        """Check if there's an operation to undo."""
        return self._last_operation is not None
    
    def get_last_operation(self) -> Optional[UndoOperation]:
        """Get the last recorded operation."""
        return self._last_operation
    
    def clear(self) -> None:
        """Clear undo history."""
        self._last_operation = None


# Global undo history instance (session-scoped)
undo_history = UndoHistory()


def record_create(task_id: int) -> None:
    """Record a task creation operation."""
    # For create, we store the task data (it will be deleted on undo)
    try:
        task = repository.get_task(task_id)
        if task:
            undo_history.record_operation(
                operation="create",
                task_id=task_id,
                original_data=None,  # No original data for create
                new_data={
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "scope": task.scope,
                    "project_id": task.project_id,
                    "column_id": task.column_id,
                }
            )
    except Exception:
        pass  # Silently fail if we can't record


def record_delete(task_id: int, task_data: Dict[str, Any]) -> None:
    """Record a task deletion operation."""
    undo_history.record_operation(
        operation="delete",
        task_id=task_id,
        original_data=task_data,  # Store full task data for restore
        new_data=None  # Task is gone after delete
    )


def record_complete(task_id: int, original_status: str, original_completed_at: Optional[str], original_column_id: int) -> None:
    """Record a task completion operation."""
    undo_history.record_operation(
        operation="complete",
        task_id=task_id,
        original_data={
            "status": original_status,
            "completed_at": original_completed_at,
            "column_id": original_column_id,
        },
        new_data={"status": "done"}
    )


def record_update_title(task_id: int, original_title: str, new_title: str) -> None:
    """Record a task title update operation."""
    undo_history.record_operation(
        operation="update_title",
        task_id=task_id,
        original_data={"title": original_title},
        new_data={"title": new_title}
    )


def record_pull(task_id: int, original_scope: str, new_scope: str) -> None:
    """Record a task scope pull operation."""
    undo_history.record_operation(
        operation="pull",
        task_id=task_id,
        original_data={"scope": original_scope},
        new_data={"scope": new_scope}
    )


def record_mv(task_id: int, original_column_id: int, new_column_id: int) -> None:
    """Record a task move operation."""
    undo_history.record_operation(
        operation="mv",
        task_id=task_id,
        original_data={"column_id": original_column_id},
        new_data={"column_id": new_column_id}
    )


def undo_last_operation() -> tuple[bool, Optional[str]]:
    """
    Undo the last operation.
    
    Returns:
        Tuple of (success: bool, message: Optional[str])
        - success: True if undo succeeded, False otherwise
        - message: Human-readable message about what was undone
    """
    if not undo_history.can_undo():
        return False, "No operation to undo"
    
    op = undo_history.get_last_operation()
    if not op:
        return False, "No operation to undo"
    
    try:
        if op.operation == "create":
            # Undo create = delete the task
            if op.task_id:
                service.delete_task(op.task_id)
                undo_history.clear()
                return True, f"Undid: Created task {op.task_id}"
        
        elif op.operation == "delete":
            # Undo delete = recreate the task
            if op.task_id and op.original_data:
                # Recreate task with original data
                task = service.create_task(
                    title=op.original_data.get("title", ""),
                    column_id=op.original_data.get("column_id", 1),
                    project_id=op.original_data.get("project_id"),
                    scope=op.original_data.get("scope", "backlog")
                )
                # Update description if it existed
                if op.original_data.get("description"):
                    service.update_task_description(task.id, op.original_data["description"])
                undo_history.clear()
                return True, f"Undid: Deleted task (restored as task {task.id})"
        
        elif op.operation == "complete":
            # Undo complete = restore original status
            if op.task_id:
                task = repository.get_task(op.task_id)
                if task:
                    task.status = op.original_data.get("status", "todo")
                    task.completed_at = op.original_data.get("completed_at")
                    # Restore original column
                    original_column_id = op.original_data.get("column_id")
                    if original_column_id:
                        service.move_task(op.task_id, original_column_id)
                    # Update task status regardless
                    repository.update_task(task)
                    undo_history.clear()
                    return True, f"Undid: Completed task {op.task_id}"
        
        elif op.operation == "update_title":
            # Undo title update = restore original title
            if op.task_id:
                original_title = op.original_data.get("title", "")
                service.update_task_title(op.task_id, original_title)
                undo_history.clear()
                return True, f"Undid: Updated title (restored: '{original_title}')"
        
        elif op.operation == "pull":
            # Undo pull = restore original scope
            if op.task_id:
                original_scope = op.original_data.get("scope", "backlog")
                service.pull_task(op.task_id, original_scope)
                undo_history.clear()
                return True, f"Undid: Pulled task {op.task_id} (restored to '{original_scope}')"
        
        elif op.operation == "mv":
            # Undo mv = restore original column
            if op.task_id:
                original_column_id = op.original_data.get("column_id", 1)
                service.move_task(op.task_id, original_column_id)
                undo_history.clear()
                return True, f"Undid: Moved task {op.task_id} (restored to original column)"
        
        return False, f"Cannot undo operation type: {op.operation}"
    
    except TaskNotFoundError:
        return False, f"Cannot undo: Task {op.task_id} no longer exists"
    except BarelyError as e:
        return False, f"Cannot undo: {e}"
    except Exception as e:
        return False, f"Cannot undo: Unexpected error: {e}"

