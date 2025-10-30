"""
FILE: barely/core/service.py
PURPOSE: Business logic layer for task operations
EXPORTS:
  - create_task(title, project_id, column_id, scope) -> Task
  - complete_task(task_id) -> Task
  - uncomplete_task(task_id) -> Task
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
from .constants import (
    VALID_SCOPES,
    ACTIVE_SCOPES,
    DEFAULT_SCOPE,
    DEFAULT_COLUMN_ID,
    SCOPE_BACKLOG,
    SCOPE_WEEK,
    SCOPE_TODAY,
    SCOPE_ARCHIVED,
)
from .exceptions import (
    TaskNotFoundError,
    ProjectNotFoundError,
    ColumnNotFoundError,
    InvalidInputError,
)


def create_task(
    title: str,
    column_id: int = DEFAULT_COLUMN_ID,  # Default to "Todo" column
    project_id: Optional[int] = None,
    scope: str = DEFAULT_SCOPE,  # Default to backlog
    description: Optional[str] = None,
) -> Task:
    """
    Create a new task with validation.

    Args:
        title: Task title (required, must not be empty)
        column_id: Column to place task in (defaults to 1 = "Todo")
        project_id: Optional project to associate with
        scope: Task scope (backlog, week, today) - defaults to backlog
        description: Optional task description

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

    # Validate scope (archived not allowed for new tasks)
    if scope not in ACTIVE_SCOPES:
        raise InvalidInputError(
            f"Invalid scope '{scope}'. Must be one of: {', '.join(ACTIVE_SCOPES)}"
        )

    # Sanitize description if provided
    description_value = description.strip() if description else None
    if description_value and not description_value:
        description_value = None

    # Create task via repository layer
    task = repository.create_task(
        title=title,
        column_id=column_id,
        project_id=project_id,
        scope=scope,
        description=description_value,
    )

    return task


def complete_task(task_id: int) -> Task:
    """
    Mark task as complete by moving it to archived scope.

    Args:
        task_id: ID of task to complete

    Returns:
        Updated Task object with scope='archived' and completed_at set

    Raises:
        TaskNotFoundError: If task_id doesn't exist

    Notes:
        - Sets completed_at to current timestamp
        - Moves task to 'archived' scope (consistent with pull-based workflow)
        - Automatically updates updated_at timestamp
        - Idempotent: completing an already-archived task is safe
        - To reactivate, use pull_task() to move back to backlog/week/today
    """
    # Fetch task (raises TaskNotFoundError if not found)
    task = repository.get_task(task_id)
    if not task:
        raise TaskNotFoundError(task_id)

    # Update task fields for completion
    task.scope = SCOPE_ARCHIVED
    task.completed_at = datetime.now().isoformat()

    # Persist changes
    repository.update_task(task)

    return task


def uncomplete_task(task_id: int, target_scope: str = DEFAULT_SCOPE) -> Task:
    """
    Mark task as incomplete by pulling it back from archived scope.

    Args:
        task_id: ID of task to un-complete
        target_scope: Scope to move task to (defaults to 'backlog')

    Returns:
        Updated Task object moved back to active scope

    Raises:
        TaskNotFoundError: If task_id doesn't exist
        InvalidInputError: If target_scope is invalid

    Notes:
        - Moves task from 'archived' scope back to active scope using pull_task()
        - Clears completed_at timestamp
        - Automatically updates updated_at timestamp
        - Idempotent: un-completing a non-archived task is safe (just moves it)
    """
    # Use pull_task to reactivate (it handles validation and updates)
    task = pull_task(task_id, target_scope)
    
    # Clear completed_at timestamp
    task.completed_at = None
    repository.update_task(task)
    
    return task


def list_tasks(
    project_id: Optional[int] = None,
    include_archived: bool = False,
) -> List[Task]:
    """
    List tasks with optional filters.

    Args:
        project_id: Filter by project ID (None = all projects)
        include_archived: Include archived/completed tasks (default False)

    Returns:
        List of tasks matching filters, ordered by creation date (newest first)

    Notes:
        - By default, excludes archived tasks (scope='archived')
        - Filtering happens in Python (repository returns all tasks)
        - Future: push filtering to repository layer for performance
    """
    # Get all tasks from repository
    tasks = repository.list_tasks()

    # Exclude archived tasks by default
    if not include_archived:
        tasks = [t for t in tasks if t.scope != SCOPE_ARCHIVED]

    # Apply filters in Python
    # Filter by project if specified
    if project_id is not None:
        tasks = [t for t in tasks if t.project_id == project_id]

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


def find_project_by_name(name: str) -> Optional[Project]:
    """
    Find project by name (case-insensitive).

    Args:
        name: Project name to search for

    Returns:
        Project object if found, None otherwise

    Notes:
        - Case-insensitive matching
        - Returns None if not found (use when existence is optional)
        - For errors, use find_project_by_name_or_raise() instead
    """
    projects = list_projects()
    return next((p for p in projects if p.name.lower() == name.lower()), None)


def find_project_by_name_or_raise(name: str) -> Project:
    """
    Find project by name (case-insensitive), raising error if not found.

    Args:
        name: Project name to search for

    Returns:
        Project object if found

    Raises:
        InvalidInputError: If project not found (with helpful message)

    Notes:
        - Case-insensitive matching
        - Use this when project must exist (e.g., assignment operations)
    """
    project = find_project_by_name(name)
    if not project:
        available = ", ".join([p.name for p in list_projects()])
        raise InvalidInputError(
            f"Project '{name}' not found. Available projects: {available}"
        )
    return project


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


def find_column_by_name(name: str) -> Optional[Column]:
    """
    Find column by name (case-insensitive).

    Args:
        name: Column name to search for

    Returns:
        Column object if found, None otherwise

    Notes:
        - Case-insensitive matching
        - Returns None if not found
        - For errors, use find_column_by_name_or_raise() instead
    """
    return repository.get_column_by_name(name)


def find_column_by_name_or_raise(name: str) -> Column:
    """
    Find column by name (case-insensitive), raising error if not found.

    Args:
        name: Column name to search for

    Returns:
        Column object if found

    Raises:
        InvalidInputError: If column not found (with helpful message)

    Notes:
        - Case-insensitive matching
        - Use this when column must exist (e.g., move operations)
    """
    column = repository.get_column_by_name(name)
    if not column:
        available = ", ".join([c.name for c in list_columns()])
        raise InvalidInputError(
            f"Column '{name}' not found. Available columns: {available}"
        )
    return column


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
        - Already filtered by scope, so no need to exclude archived
    """
    return repository.list_tasks_by_scope(SCOPE_BACKLOG)


def list_week() -> List[Task]:
    """
    List all tasks in the week scope.

    Returns:
        List of tasks with scope='week', ordered by creation date (newest first)

    Notes:
        - Week scope represents your weekly commitment
        - Tasks are manually pulled here from backlog (typically Monday planning)
        - Already filtered by scope, so no need to exclude archived
    """
    return repository.list_tasks_by_scope(SCOPE_WEEK)


def list_today() -> List[Task]:
    """
    List all tasks in the today scope.

    Returns:
        List of tasks with scope='today', ordered by creation date (newest first)

    Notes:
        - Today scope represents your daily focus list
        - Tasks are manually pulled here from week or backlog
        - This is the primary view for "blitz mode"
        - Already filtered by scope, so no need to exclude archived
    """
    return repository.list_tasks_by_scope(SCOPE_TODAY)


def list_completed() -> List[Task]:
    """
    List all completed tasks (those in archived scope).

    Returns:
        List of completed tasks, ordered by completion date (newest first)

    Notes:
        - Returns tasks with scope='archived'
        - Useful for reviewing completed work
        - Can be reactivated by pulling back to backlog/week/today
    """
    tasks = repository.list_tasks_by_scope(SCOPE_ARCHIVED)
    # Sort by completed_at if available, otherwise by updated_at
    tasks.sort(key=lambda t: t.completed_at or t.updated_at or "", reverse=True)
    return tasks


def pull_task(task_id: int, target_scope: str) -> Task:
    """
    Pull a task into a different scope (core of pull-based workflow).

    Args:
        task_id: ID of task to pull
        target_scope: Target scope ('backlog', 'week', 'today', or 'archived')

    Returns:
        Updated Task object with new scope

    Raises:
        TaskNotFoundError: If task_id doesn't exist
        InvalidInputError: If target_scope is invalid

    Notes:
        - This is the "commitment" operation that moves tasks through the workflow
        - Common flows: backlog → week, week → today, today → backlog (defer)
        - Can also move archived → backlog/week/today to reactivate completed tasks
        - Automatically updates updated_at timestamp
    """
    # Validate target scope (now includes archived)
    if target_scope not in VALID_SCOPES:
        raise InvalidInputError(
            f"Invalid scope '{target_scope}'. Must be one of: {', '.join(VALID_SCOPES)}"
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
    # Validate target scope once (now includes archived)
    if target_scope not in VALID_SCOPES:
        raise InvalidInputError(
            f"Invalid scope '{target_scope}'. Must be one of: {', '.join(VALID_SCOPES)}"
        )

    # Pull each task (let errors bubble up for CLI/REPL to handle)
    updated_tasks = []
    for task_id in task_ids:
        task = repository.update_task_scope(task_id, target_scope)
        updated_tasks.append(task)

    return updated_tasks
