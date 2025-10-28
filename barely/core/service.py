"""
FILE: barely/core/service.py
PURPOSE: Business logic layer for task operations
EXPORTS:
  - create_task(title, project_id, column_id, scope) -> Task
  - complete_task(task_id) -> Task
  - list_tasks(project_id, status) -> List[Task]
  - update_task_title(task_id, new_title) -> Task
  - update_task_description(task_id, new_description) -> Task
  - delete_task(task_id) -> None
  - create_project(name) -> Project
  - list_projects() -> List[Project]
  - get_project(project_id) -> Optional[Project]
  - delete_project(project_id) -> None
  - list_columns() -> List[Column]
  - move_task(task_id, column_id) -> Task
  - assign_task_to_project(task_id, project_id) -> Task
  - list_tasks_by_project(project_id) -> List[Task]
  - list_tasks_by_column(column_id) -> List[Task]
  - list_backlog() -> List[Task]
  - list_week() -> List[Task]
  - list_today() -> List[Task]
  - list_completed() -> List[Task]
  - pull_task(task_id, target_scope) -> Task
  - pull_tasks(task_ids, target_scope) -> List[Task]
DEPENDENCIES:
  - barely.core.models (Task, Project, Column)
  - barely.core.repository (all CRUD functions)
  - barely.core.exceptions (TaskNotFoundError, ProjectNotFoundError, ColumnNotFoundError, InvalidInputError)
  - datetime (for timestamps)
  - typing (type hints)
NOTES:
  - All functions validate input and raise descriptive errors
  - No direct database access (use repository layer)
  - Returns domain objects, never dicts or raw SQL results
  - Business rules enforced here (e.g., validation, status transitions)
  - Pull-based workflow: backlog -> week -> today
"""

from datetime import datetime
from typing import List, Optional

from . import repository
from .models import Task, Project, Column
from .exceptions import (
    TaskNotFoundError,
    ProjectNotFoundError,
    ColumnNotFoundError,
    InvalidInputError,
)


def create_task(
    title: str,
    column_id: int = 1,  # Default to "Todo" column
    project_id: Optional[int] = None,
    scope: str = "backlog",  # Default to backlog
) -> Task:
    """
    Create a new task with validation.

    Args:
        title: Task title (required, must not be empty)
        column_id: Column to place task in (defaults to 1 = "Todo")
        project_id: Optional project to associate with
        scope: Task scope (backlog, week, today) - defaults to backlog

    Returns:
        Newly created Task object

    Raises:
        InvalidInputError: If title is empty or whitespace-only or scope is invalid

    Notes:
        - Trims whitespace from title
        - Validates title is not empty after trimming
        - Validates scope is valid ('backlog', 'week', 'today')
        - Sets created_at and updated_at automatically via repository
        - Task starts with status='todo' and scope='backlog' (unless specified)
    """
    # Validate and sanitize title
    title = title.strip()
    if not title:
        raise InvalidInputError("Task title cannot be empty")

    # Validate scope
    valid_scopes = ("backlog", "week", "today")
    if scope not in valid_scopes:
        raise InvalidInputError(
            f"Invalid scope '{scope}'. Must be one of: {', '.join(valid_scopes)}"
        )

    # Create task via repository layer
    task = repository.create_task(
        title=title,
        column_id=column_id,
        project_id=project_id,
        scope=scope,
    )

    return task


def complete_task(task_id: int) -> Task:
    """
    Mark task as complete.

    Args:
        task_id: ID of task to complete

    Returns:
        Updated Task object with status='done' and completed_at set

    Raises:
        TaskNotFoundError: If task_id doesn't exist

    Notes:
        - Sets completed_at to current timestamp
        - Changes status to 'done'
        - Moves task to 'Done' column (column_id=3)
        - Automatically updates updated_at timestamp
        - Idempotent: completing an already-done task is safe
    """
    # Fetch task (raises TaskNotFoundError if not found)
    task = repository.get_task(task_id)
    if not task:
        raise TaskNotFoundError(task_id)

    # Update task fields for completion
    task.status = "done"
    task.completed_at = datetime.now().isoformat()
    task.column_id = 3  # Move to "Done" column

    # Persist changes
    repository.update_task(task)

    return task


def list_tasks(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    include_done: bool = False,
) -> List[Task]:
    """
    List tasks with optional filters.

    Args:
        project_id: Filter by project ID (None = all projects)
        status: Filter by status ('todo', 'done', 'archived', None = all)
        include_done: Include completed tasks (column_id=3, default False)

    Returns:
        List of tasks matching filters, ordered by creation date (newest first)

    Raises:
        InvalidInputError: If status is invalid

    Notes:
        - By default, excludes completed tasks (Done column)
        - Validates status against allowed values
        - Filtering happens in Python (repository returns all tasks)
        - Future: push filtering to repository layer for performance
    """
    # Validate status if provided
    if status and status not in ("todo", "done", "archived"):
        raise InvalidInputError(
            f"Invalid status '{status}'. Must be 'todo', 'done', or 'archived'"
        )

    # Get all tasks from repository
    tasks = repository.list_tasks()

    # Exclude completed tasks by default (those in Done column)
    if not include_done:
        tasks = [t for t in tasks if t.column_id != 3]

    # Apply filters in Python
    # Filter by project if specified
    if project_id is not None:
        tasks = [t for t in tasks if t.project_id == project_id]

    # Filter by status if specified
    if status is not None:
        tasks = [t for t in tasks if t.status == status]

    return tasks


def update_task_title(task_id: int, new_title: str) -> Task:
    """
    Update task title.

    Args:
        task_id: ID of task to update
        new_title: New title for the task

    Returns:
        Updated Task object

    Raises:
        TaskNotFoundError: If task_id doesn't exist
        InvalidInputError: If new_title is empty

    Notes:
        - Validates new title is not empty
        - Trims whitespace from new title
        - Automatically updates updated_at timestamp
    """
    # Validate new title
    new_title = new_title.strip()
    if not new_title:
        raise InvalidInputError("Task title cannot be empty")

    # Fetch task (raises TaskNotFoundError if not found)
    task = repository.get_task(task_id)
    if not task:
        raise TaskNotFoundError(task_id)

    # Update title
    task.title = new_title

    # Persist changes
    repository.update_task(task)

    return task


def update_task_description(task_id: int, new_description: str) -> Task:
    """
    Update task description.

    Args:
        task_id: ID of task to update
        new_description: New description for the task (can be empty to clear)

    Returns:
        Updated Task object

    Raises:
        TaskNotFoundError: If task_id doesn't exist

    Notes:
        - Description can be empty (unlike title)
        - Strips leading/trailing whitespace but preserves internal newlines
        - Automatically updates updated_at timestamp
    """
    # Strip outer whitespace but keep internal formatting
    new_description = new_description.strip() if new_description else None

    # Fetch task (raises TaskNotFoundError if not found)
    task = repository.get_task(task_id)
    if not task:
        raise TaskNotFoundError(task_id)

    # Update description (can be None/empty to clear)
    task.description = new_description

    # Persist changes
    repository.update_task(task)

    return task


def delete_task(task_id: int) -> None:
    """
    Delete task permanently.

    Args:
        task_id: ID of task to delete

    Raises:
        TaskNotFoundError: If task_id doesn't exist

    Notes:
        - Permanent deletion (no soft-delete or archiving yet)
        - Repository layer validates task exists before deleting
    """
    # Repository handles existence check and deletion
    repository.delete_task(task_id)


# --- Project Management ---


def create_project(name: str) -> Project:
    """
    Create a new project with validation.

    Args:
        name: Project name (required, must not be empty or whitespace-only)

    Returns:
        Newly created Project object

    Raises:
        InvalidInputError: If name is empty or whitespace-only
        sqlite3.IntegrityError: If project name already exists (bubbles from repository)

    Notes:
        - Trims whitespace from name
        - Validates name is not empty after trimming
        - Project names must be unique (enforced by database)
    """
    # Validate and sanitize name
    name = name.strip()
    if not name:
        raise InvalidInputError("Project name cannot be empty")

    # Create project via repository layer
    project = repository.create_project(name)

    return project


def list_projects() -> List[Project]:
    """
    List all projects.

    Returns:
        List of all projects, ordered by creation date (newest first)
    """
    return repository.list_projects()


def get_project(project_id: int) -> Optional[Project]:
    """
    Get a single project by ID.

    Args:
        project_id: ID of project to retrieve

    Returns:
        Project object if found, None otherwise

    Notes:
        - Returns None rather than raising error for not found
        - Use this when project existence is optional (e.g., display)
    """
    return repository.get_project(project_id)


def delete_project(project_id: int) -> None:
    """
    Delete project permanently.

    Args:
        project_id: ID of project to delete

    Raises:
        ProjectNotFoundError: If project_id doesn't exist

    Notes:
        - Permanent deletion
        - Tasks associated with this project will have their project_id set to NULL
        - Repository layer validates project exists before deleting
    """
    repository.delete_project(project_id)


# --- Column Management ---


def list_columns() -> List[Column]:
    """
    List all workflow columns.

    Returns:
        List of all columns, ordered by position
    """
    return repository.list_columns()


def move_task(task_id: int, column_id: int) -> Task:
    """
    Move task to a different column.

    Args:
        task_id: ID of task to move
        column_id: ID of target column

    Returns:
        Updated Task object

    Raises:
        TaskNotFoundError: If task_id doesn't exist
        ColumnNotFoundError: If column_id doesn't exist

    Notes:
        - Automatically updates updated_at timestamp
        - Repository validates both task and column exist
    """
    return repository.move_task(task_id, column_id)


def assign_task_to_project(task_id: int, project_id: int) -> Task:
    """
    Assign task to a project.

    Args:
        task_id: ID of task to assign
        project_id: ID of target project

    Returns:
        Updated Task object

    Raises:
        TaskNotFoundError: If task_id doesn't exist
        ProjectNotFoundError: If project_id doesn't exist

    Notes:
        - Automatically updates updated_at timestamp
        - Repository validates both task and project exist
    """
    # Fetch task (raises TaskNotFoundError if not found)
    task = repository.get_task(task_id)
    if not task:
        raise TaskNotFoundError(task_id)

    # Validate project exists (raises ProjectNotFoundError if not found)
    project = repository.get_project(project_id)
    if not project:
        raise ProjectNotFoundError(project_id)

    # Update task's project_id
    task.project_id = project_id

    # Persist changes
    repository.update_task(task)

    return task


# --- Task Filtering ---


def list_tasks_by_project(project_id: int) -> List[Task]:
    """
    List all tasks for a specific project.

    Args:
        project_id: ID of project to filter by

    Returns:
        List of tasks in the project, ordered by creation date (newest first)

    Notes:
        - Returns empty list if project doesn't exist or has no tasks
        - Does not validate that project exists (allows querying non-existent projects)
    """
    tasks = repository.list_tasks()
    return [t for t in tasks if t.project_id == project_id]


def list_tasks_by_column(column_id: int) -> List[Task]:
    """
    List all tasks in a specific column.

    Args:
        column_id: ID of column to filter by

    Returns:
        List of tasks in the column, ordered by creation date (newest first)

    Notes:
        - Returns empty list if column doesn't exist or has no tasks
        - Does not validate that column exists (allows querying non-existent columns)
    """
    tasks = repository.list_tasks()
    return [t for t in tasks if t.column_id == column_id]


# --- Pull-Based Workflow (Scope Management) ---


def list_backlog() -> List[Task]:
    """
    List all tasks in the backlog scope.

    Returns:
        List of tasks with scope='backlog', ordered by creation date (newest first)

    Notes:
        - Backlog is the default scope for new tasks
        - This is where tasks live until pulled into week or today
        - Excludes completed tasks (Done column)
    """
    tasks = repository.list_tasks_by_scope("backlog")
    return [t for t in tasks if t.column_id != 3]


def list_week() -> List[Task]:
    """
    List all tasks in the week scope.

    Returns:
        List of tasks with scope='week', ordered by creation date (newest first)

    Notes:
        - Week scope represents your weekly commitment
        - Tasks are manually pulled here from backlog (typically Monday planning)
        - Excludes completed tasks (Done column)
    """
    tasks = repository.list_tasks_by_scope("week")
    return [t for t in tasks if t.column_id != 3]


def list_today() -> List[Task]:
    """
    List all tasks in the today scope.

    Returns:
        List of tasks with scope='today', ordered by creation date (newest first)

    Notes:
        - Today scope represents your daily focus list
        - Tasks are manually pulled here from week or backlog
        - This is the primary view for "blitz mode"
        - Excludes completed tasks (Done column)
    """
    tasks = repository.list_tasks_by_scope("today")
    return [t for t in tasks if t.column_id != 3]


def list_completed() -> List[Task]:
    """
    List all completed tasks (those in Done column).

    Returns:
        List of completed tasks, ordered by completion date (newest first)

    Notes:
        - Returns tasks in the Done column (column_id=3)
        - Useful for reviewing completed work
        - Can be pulled back to reopen tasks
    """
    tasks = repository.list_tasks()
    completed = [t for t in tasks if t.column_id == 3]
    # Sort by completed_at if available, otherwise by updated_at
    completed.sort(key=lambda t: t.completed_at or t.updated_at or "", reverse=True)
    return completed


def pull_task(task_id: int, target_scope: str) -> Task:
    """
    Pull a task into a different scope (core of pull-based workflow).

    Args:
        task_id: ID of task to pull
        target_scope: Target scope ('backlog', 'week', or 'today')

    Returns:
        Updated Task object with new scope

    Raises:
        TaskNotFoundError: If task_id doesn't exist
        InvalidInputError: If target_scope is invalid

    Notes:
        - This is the "commitment" operation that moves tasks through the workflow
        - Common flows: backlog → week, week → today, today → backlog (defer)
        - Automatically updates updated_at timestamp
    """
    # Validate target scope
    valid_scopes = ("backlog", "week", "today")
    if target_scope not in valid_scopes:
        raise InvalidInputError(
            f"Invalid scope '{target_scope}'. Must be one of: {', '.join(valid_scopes)}"
        )

    # Repository handles existence check and update
    return repository.update_task_scope(task_id, target_scope)


def pull_tasks(task_ids: List[int], target_scope: str) -> List[Task]:
    """
    Pull multiple tasks into a different scope (bulk operation).

    Args:
        task_ids: List of task IDs to pull
        target_scope: Target scope ('backlog', 'week', or 'today')

    Returns:
        List of successfully updated Task objects

    Raises:
        InvalidInputError: If target_scope is invalid
        TaskNotFoundError: If any task_id doesn't exist (raised for first failure)

    Notes:
        - Validates scope once, then pulls each task individually
        - If a task fails, the error bubbles up (not caught here)
        - Use this for bulk pulls like "pull 1,2,3 into week"
    """
    # Validate target scope once
    valid_scopes = ("backlog", "week", "today")
    if target_scope not in valid_scopes:
        raise InvalidInputError(
            f"Invalid scope '{target_scope}'. Must be one of: {', '.join(valid_scopes)}"
        )

    # Pull each task (let errors bubble up for CLI/REPL to handle)
    updated_tasks = []
    for task_id in task_ids:
        task = repository.update_task_scope(task_id, target_scope)
        updated_tasks.append(task)

    return updated_tasks
