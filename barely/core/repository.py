"""
FILE: barely/core/repository.py
PURPOSE: Database operations and SQLite connection management
EXPORTS:
  - get_connection() -> Connection
  - init_database() -> None
  - create_task(title, column_id, project_id, scope) -> Task
  - get_task(task_id) -> Task | None
  - list_tasks() -> List[Task]
  - list_tasks_by_scope(scope) -> List[Task]
  - update_task(task) -> None
  - update_task_scope(task_id, scope) -> Task
  - delete_task(task_id) -> None
  - create_project(name) -> Project
  - get_project(project_id) -> Project | None
  - list_projects() -> List[Project]
  - delete_project(project_id) -> None
  - create_column(name, position) -> Column
  - get_column(column_id) -> Column | None
  - get_column_by_name(name) -> Column | None
  - list_columns() -> List[Column]
  - move_task(task_id, column_id) -> Task
DEPENDENCIES:
  - sqlite3 (stdlib)
  - pathlib (stdlib)
  - datetime (stdlib)
  - barely.core.models (Task, Project, Column)
  - barely.core.exceptions (TaskNotFoundError, ProjectNotFoundError, ColumnNotFoundError)
NOTES:
  - Database stored at ~/.barely/barely.db
  - Auto-creates directory and initializes schema on first run
  - Returns domain objects (Task, etc.), never raw dicts
  - Uses row_factory for dict-like row access
  - Scope field enables pull-based workflow (backlog -> week -> today)
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .models import Task, Project, Column
from .exceptions import TaskNotFoundError, ProjectNotFoundError, ColumnNotFoundError


# Database file location (cross-platform)
DB_DIR = Path.home() / ".barely"
DB_PATH = DB_DIR / "barely.db"

# Schema file location (relative to this file)
SCHEMA_PATH = Path(__file__).parent.parent.parent / "db" / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """
    Get SQLite connection to Barely database.

    Creates ~/.barely directory if it doesn't exist.
    Enables row_factory for dict-like row access.
    Enables foreign key constraints.
    Initializes database schema on first connection.
    """
    # Ensure directory exists
    DB_DIR.mkdir(parents=True, exist_ok=True)

    # Connect with row factory for named column access
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Enable foreign key constraints (required for ON DELETE CASCADE/SET NULL)
    conn.execute("PRAGMA foreign_keys = ON")

    # Initialize schema if needed
    init_database(conn)

    return conn


def init_database(conn: sqlite3.Connection) -> None:
    """
    Initialize database schema if tables don't exist.

    Executes schema.sql to create tables and default data.
    Safe to call multiple times (uses CREATE TABLE IF NOT EXISTS).
    """
    # Check if tables exist by querying sqlite_master
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
    )
    tables_exist = cursor.fetchone() is not None

    if not tables_exist:
        # Read and execute schema file
        with open(SCHEMA_PATH, "r") as f:
            schema_sql = f.read()

        conn.executescript(schema_sql)
        conn.commit()


def create_task(
    title: str,
    column_id: int,
    project_id: Optional[int] = None,
    scope: str = "backlog"
) -> Task:
    """
    Create a new task.

    Args:
        title: Task title (required)
        column_id: Column to place task in (required)
        project_id: Optional project to associate with
        scope: Task scope (backlog, week, today) - defaults to backlog

    Returns:
        Newly created Task object

    Note:
        Sets created_at and updated_at automatically.
        Task starts with status='todo' and scope='backlog' (unless specified).
    """
    conn = get_connection()
    now = datetime.now().isoformat()

    cursor = conn.execute(
        """
        INSERT INTO tasks (title, column_id, project_id, status, scope, created_at, updated_at)
        VALUES (?, ?, ?, 'todo', ?, ?, ?)
        """,
        (title, column_id, project_id, scope, now, now),
    )
    conn.commit()

    # SQLite doesn't support RETURNING, so fetch the inserted row
    task_id = cursor.lastrowid
    task = get_task(task_id)

    if not task:
        # This should never happen, but handle gracefully
        raise TaskNotFoundError(task_id)

    return task


def get_task(task_id: int) -> Optional[Task]:
    """
    Fetch single task by ID.

    Returns:
        Task object if found, None otherwise
    """
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()

    return Task.from_row(row) if row else None


def list_tasks() -> List[Task]:
    """
    List all tasks.

    Returns:
        List of all tasks in database, ordered by creation date (newest first)
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tasks ORDER BY created_at DESC"
    ).fetchall()

    return [Task.from_row(row) for row in rows]


def update_task(task: Task) -> None:
    """
    Update existing task.

    Args:
        task: Task object with updated fields

    Note:
        Automatically updates updated_at timestamp.
        Updates all fields (title, description, status, scope, completed_at, etc.)
    """
    conn = get_connection()
    now = datetime.now().isoformat()

    conn.execute(
        """
        UPDATE tasks
        SET title = ?,
            description = ?,
            project_id = ?,
            column_id = ?,
            status = ?,
            scope = ?,
            completed_at = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            task.title,
            task.description,
            task.project_id,
            task.column_id,
            task.status,
            task.scope,
            task.completed_at,
            now,
            task.id,
        ),
    )
    conn.commit()


def delete_task(task_id: int) -> None:
    """
    Delete task by ID.

    Args:
        task_id: ID of task to delete

    Raises:
        TaskNotFoundError: If task doesn't exist

    Note:
        Permanent deletion. No soft-delete or archiving (yet).
    """
    conn = get_connection()

    # Verify task exists before deleting
    task = get_task(task_id)
    if not task:
        raise TaskNotFoundError(task_id)

    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()


# --- Scope Operations (Pull-Based Workflow) ---


def list_tasks_by_scope(scope: str) -> List[Task]:
    """
    List all tasks in a specific scope.

    Args:
        scope: Task scope ('backlog', 'week', 'today')

    Returns:
        List of tasks in the scope, ordered by creation date (newest first)

    Note:
        This is the core function for pull-based workflow views.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE scope = ? ORDER BY created_at DESC",
        (scope,)
    ).fetchall()

    return [Task.from_row(row) for row in rows]


def update_task_scope(task_id: int, scope: str) -> Task:
    """
    Update a task's scope (pull task to different scope).

    Args:
        task_id: ID of task to update
        scope: Target scope ('backlog', 'week', 'today')

    Returns:
        Updated Task object

    Raises:
        TaskNotFoundError: If task doesn't exist

    Note:
        This is the core "pull" operation.
        Automatically updates updated_at timestamp.
    """
    conn = get_connection()

    # Verify task exists
    task = get_task(task_id)
    if not task:
        raise TaskNotFoundError(task_id)

    # Update scope
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE tasks SET scope = ?, updated_at = ? WHERE id = ?",
        (scope, now, task_id),
    )
    conn.commit()

    # Return updated task
    updated_task = get_task(task_id)
    if not updated_task:
        raise TaskNotFoundError(task_id)

    return updated_task


# --- Project Operations ---


def create_project(name: str) -> Project:
    """
    Create a new project.

    Args:
        name: Project name (must be unique)

    Returns:
        Newly created Project object

    Raises:
        sqlite3.IntegrityError: If project name already exists

    Note:
        Sets created_at automatically.
    """
    conn = get_connection()
    now = datetime.now().isoformat()

    cursor = conn.execute(
        "INSERT INTO projects (name, created_at) VALUES (?, ?)",
        (name, now),
    )
    conn.commit()

    # Fetch the inserted project
    project_id = cursor.lastrowid
    project = get_project(project_id)

    if not project:
        raise ProjectNotFoundError(project_id)

    return project


def get_project(project_id: int) -> Optional[Project]:
    """
    Fetch single project by ID.

    Returns:
        Project object if found, None otherwise
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM projects WHERE id = ?", (project_id,)
    ).fetchone()

    return Project.from_row(row) if row else None


def list_projects() -> List[Project]:
    """
    List all projects.

    Returns:
        List of all projects in database, ordered by creation date (newest first)
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM projects ORDER BY created_at DESC"
    ).fetchall()

    return [Project.from_row(row) for row in rows]


def delete_project(project_id: int) -> None:
    """
    Delete project by ID.

    Args:
        project_id: ID of project to delete

    Raises:
        ProjectNotFoundError: If project doesn't exist

    Note:
        Tasks associated with this project will have their project_id set to NULL
        (enforced by ON DELETE SET NULL in schema).
    """
    conn = get_connection()

    # Verify project exists before deleting
    project = get_project(project_id)
    if not project:
        raise ProjectNotFoundError(project_id)

    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()


# --- Column Operations ---


def create_column(name: str, position: int = 0) -> Column:
    """
    Create a new column.

    Args:
        name: Column name (must be unique)
        position: Display position (default: 0)

    Returns:
        Newly created Column object

    Raises:
        sqlite3.IntegrityError: If column name already exists
    """
    conn = get_connection()

    cursor = conn.execute(
        "INSERT INTO columns (name, position) VALUES (?, ?)",
        (name, position),
    )
    conn.commit()

    # Fetch the inserted column
    column_id = cursor.lastrowid
    column = get_column(column_id)

    if not column:
        raise ColumnNotFoundError(column_id)

    return column


def get_column(column_id: int) -> Optional[Column]:
    """
    Fetch single column by ID.

    Returns:
        Column object if found, None otherwise
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM columns WHERE id = ?", (column_id,)
    ).fetchone()

    return Column.from_row(row) if row else None


def get_column_by_name(name: str) -> Optional[Column]:
    """
    Fetch single column by name.

    Returns:
        Column object if found, None otherwise

    Note:
        Useful for CLI/REPL commands where users specify column by name
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM columns WHERE name = ?", (name,)
    ).fetchone()

    return Column.from_row(row) if row else None


def list_columns() -> List[Column]:
    """
    List all columns.

    Returns:
        List of all columns in database, ordered by position
    """
    conn = get_connection()
    rows = conn.execute("SELECT * FROM columns ORDER BY position").fetchall()

    return [Column.from_row(row) for row in rows]


def move_task(task_id: int, column_id: int) -> Task:
    """
    Move task to a different column.

    Args:
        task_id: ID of task to move
        column_id: ID of target column

    Returns:
        Updated Task object

    Raises:
        TaskNotFoundError: If task doesn't exist
        ColumnNotFoundError: If column doesn't exist

    Note:
        Automatically updates updated_at timestamp.
    """
    conn = get_connection()

    # Verify task exists
    task = get_task(task_id)
    if not task:
        raise TaskNotFoundError(task_id)

    # Verify column exists
    column = get_column(column_id)
    if not column:
        raise ColumnNotFoundError(column_id)

    # Update task's column
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE tasks SET column_id = ?, updated_at = ? WHERE id = ?",
        (column_id, now, task_id),
    )
    conn.commit()

    # Return updated task
    updated_task = get_task(task_id)
    if not updated_task:
        raise TaskNotFoundError(task_id)

    return updated_task
