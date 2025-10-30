"""
Test suite for Phase 5: Projects and Organization

Tests repository, service, CLI, and REPL integration for:
- Project management (create, list, get, delete)
- Column operations (create, list, move tasks)
- Task filtering by project and column
"""

import pytest
import sqlite3
from pathlib import Path
import tempfile
import os
import subprocess
import sys
import json as json_module

# Path setup handled by conftest.py for pytest runs
# For direct execution, add project root to path
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from barely.core import repository, service, models, exceptions


# Helper function for subprocess calls with proper encoding
def run_cli(*args, **kwargs):
    """Run CLI command with proper encoding for Windows."""
    kwargs.setdefault('capture_output', True)
    kwargs.setdefault('text', True)
    kwargs.setdefault('encoding', 'utf-8')
    kwargs.setdefault('errors', 'replace')
    return subprocess.run(args, **kwargs)


# --- Test Fixtures ---

@pytest.fixture(autouse=True)
def temp_db(monkeypatch, tmp_path):
    """Use temporary database for all tests."""
    db_path = tmp_path / "test_barely.db"
    monkeypatch.setattr(repository, "DB_PATH", db_path)
    monkeypatch.setattr(repository, "DB_DIR", tmp_path)
    yield db_path


# --- Repository Layer Tests: Projects ---

def test_create_project():
    """Test creating a new project."""
    project = repository.create_project("Work")

    assert project.id is not None
    assert project.name == "Work"
    assert project.created_at is not None


def test_create_project_duplicate_name():
    """Test that duplicate project names raise an error."""
    repository.create_project("Work")

    with pytest.raises(sqlite3.IntegrityError):
        repository.create_project("Work")


def test_get_project():
    """Test fetching a project by ID."""
    created = repository.create_project("Personal")

    fetched = repository.get_project(created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "Personal"


def test_get_project_nonexistent():
    """Test fetching nonexistent project returns None."""
    result = repository.get_project(999)
    assert result is None


def test_list_projects():
    """Test listing all projects."""
    repository.create_project("Work")
    repository.create_project("Personal")
    repository.create_project("Hobbies")

    projects = repository.list_projects()

    assert len(projects) == 3
    names = [p.name for p in projects]
    assert "Work" in names
    assert "Personal" in names
    assert "Hobbies" in names


def test_list_projects_empty():
    """Test listing projects when none exist."""
    projects = repository.list_projects()
    assert projects == []


def test_delete_project():
    """Test deleting a project."""
    project = repository.create_project("ToDelete")
    project_id = project.id

    repository.delete_project(project_id)

    result = repository.get_project(project_id)
    assert result is None


def test_delete_project_nonexistent():
    """Test deleting nonexistent project raises error."""
    with pytest.raises(exceptions.ProjectNotFoundError):
        repository.delete_project(999)


def test_delete_project_sets_tasks_to_null():
    """Test that deleting a project sets task project_ids to NULL."""
    project = repository.create_project("Work")
    task = repository.create_task("Task in project", column_id=1, project_id=project.id)

    repository.delete_project(project.id)

    # Task should still exist but with null project_id
    updated_task = repository.get_task(task.id)
    assert updated_task is not None
    assert updated_task.project_id is None


# --- Repository Layer Tests: Columns ---

def test_create_column():
    """Test creating a new column."""
    column = repository.create_column("Backlog", position=0)

    assert column.id is not None
    assert column.name == "Backlog"
    assert column.position == 0


def test_create_column_duplicate_name():
    """Test that duplicate column names raise an error."""
    repository.create_column("Review")

    with pytest.raises(sqlite3.IntegrityError):
        repository.create_column("Review")


def test_list_columns():
    """Test listing all columns."""
    columns = repository.list_columns()

    # Should have default columns from schema (Todo, In Progress, Done)
    assert len(columns) >= 3
    names = [c.name for c in columns]
    assert "Todo" in names
    assert "In Progress" in names
    assert "Done" in names


def test_list_columns_ordered_by_position():
    """Test that columns are returned in position order."""
    columns = repository.list_columns()

    # Verify they're sorted by position
    positions = [c.position for c in columns]
    assert positions == sorted(positions)


def test_get_column():
    """Test fetching a column by ID."""
    # Get one of the default columns
    columns = repository.list_columns()
    first_column = columns[0]

    fetched = repository.get_column(first_column.id)

    assert fetched is not None
    assert fetched.id == first_column.id
    assert fetched.name == first_column.name


def test_get_column_by_name():
    """Test fetching a column by name."""
    column = repository.get_column_by_name("Todo")

    assert column is not None
    assert column.name == "Todo"


def test_get_column_by_name_nonexistent():
    """Test fetching nonexistent column by name returns None."""
    result = repository.get_column_by_name("NonexistentColumn")
    assert result is None


def test_move_task_to_column():
    """Test moving a task to a different column."""
    task = repository.create_task("My task", column_id=1)

    # Move to column 2
    updated_task = repository.move_task(task.id, 2)

    assert updated_task.column_id == 2
    assert updated_task.id == task.id
    assert updated_task.title == "My task"


def test_move_task_nonexistent():
    """Test moving nonexistent task raises error."""
    with pytest.raises(exceptions.TaskNotFoundError):
        repository.move_task(999, 2)


def test_move_task_to_nonexistent_column():
    """Test moving task to nonexistent column raises error."""
    task = repository.create_task("My task", column_id=1)

    with pytest.raises(exceptions.ColumnNotFoundError):
        repository.move_task(task.id, 999)


# --- Service Layer Tests: Projects ---

def test_service_create_project():
    """Test service layer project creation."""
    project = service.create_project("Work")

    assert project.id is not None
    assert project.name == "Work"


def test_service_create_project_empty_name():
    """Test that empty project name raises error."""
    with pytest.raises(exceptions.InvalidInputError):
        service.create_project("")


def test_service_create_project_whitespace_name():
    """Test that whitespace-only project name raises error."""
    with pytest.raises(exceptions.InvalidInputError):
        service.create_project("   ")


def test_service_list_projects():
    """Test service layer project listing."""
    service.create_project("Work")
    service.create_project("Personal")

    projects = service.list_projects()

    assert len(projects) == 2
    names = [p.name for p in projects]
    assert "Work" in names
    assert "Personal" in names


def test_service_delete_project():
    """Test service layer project deletion."""
    project = service.create_project("ToDelete")

    service.delete_project(project.id)

    result = repository.get_project(project.id)
    assert result is None


def test_service_delete_nonexistent_project():
    """Test deleting nonexistent project via service."""
    with pytest.raises(exceptions.ProjectNotFoundError):
        service.delete_project(999)


# --- Service Layer Tests: Columns and Task Movement ---

def test_service_list_columns():
    """Test service layer column listing."""
    columns = service.list_columns()

    assert len(columns) >= 3
    names = [c.name for c in columns]
    assert "Todo" in names


def test_service_move_task():
    """Test moving task via service layer."""
    task = service.create_task("My task", column_id=1)

    updated = service.move_task(task.id, 2)

    assert updated.column_id == 2


def test_service_move_task_nonexistent():
    """Test moving nonexistent task via service."""
    with pytest.raises(exceptions.TaskNotFoundError):
        service.move_task(999, 2)


def test_service_move_task_to_nonexistent_column():
    """Test moving task to nonexistent column via service."""
    task = service.create_task("My task", column_id=1)

    with pytest.raises(exceptions.ColumnNotFoundError):
        service.move_task(task.id, 999)


# --- Service Layer Tests: Task Filtering ---

def test_list_tasks_by_project():
    """Test filtering tasks by project."""
    work_project = service.create_project("Work")
    personal_project = service.create_project("Personal")

    service.create_task("Work task 1", column_id=1, project_id=work_project.id)
    service.create_task("Work task 2", column_id=1, project_id=work_project.id)
    service.create_task("Personal task", column_id=1, project_id=personal_project.id)
    service.create_task("No project task", column_id=1)

    work_tasks = service.list_tasks_by_project(work_project.id)

    assert len(work_tasks) == 2
    for task in work_tasks:
        assert task.project_id == work_project.id


def test_list_tasks_by_column():
    """Test filtering tasks by column."""
    service.create_task("Todo task 1", column_id=1)
    service.create_task("Todo task 2", column_id=1)
    service.create_task("In progress task", column_id=2)

    todo_tasks = service.list_tasks_by_column(1)

    assert len(todo_tasks) == 2
    for task in todo_tasks:
        assert task.column_id == 1


def test_list_tasks_by_nonexistent_project():
    """Test filtering by nonexistent project returns empty list."""
    tasks = service.list_tasks_by_project(999)
    assert tasks == []


def test_list_tasks_by_nonexistent_column():
    """Test filtering by nonexistent column returns empty list."""
    tasks = service.list_tasks_by_column(999)
    assert tasks == []


# --- CLI Tests: Project Commands ---

# Note: CLI tests run against a temporary in-memory approach would be better,
# but for now we test basic functionality. The core repository and service layers
# are thoroughly tested above.

def test_cli_project_add(tmp_path, monkeypatch):
    """Test 'barely project add' command."""
    import uuid
    unique_name = f"TestProject_{uuid.uuid4().hex[:8]}"

    result = run_cli("python", "-m", "barely.cli.main", "project", "add", unique_name)

    assert result.returncode == 0
    assert unique_name in result.stdout


def test_cli_project_add_json_output(tmp_path, monkeypatch):
    """Test 'barely project add --json' command."""
    import uuid
    unique_name = f"TestProject_{uuid.uuid4().hex[:8]}"

    result = run_cli("python", "-m", "barely.cli.main", "project", "add", unique_name, "--json")

    assert result.returncode == 0
    assert f'"name": "{unique_name}"' in result.stdout


def test_cli_project_ls(tmp_path, monkeypatch):
    """Test 'barely project ls' command."""
    result = run_cli("python", "-m", "barely.cli.main", "project", "ls")

    assert result.returncode == 0
    # Should list projects (or show "No projects" if empty)


def test_cli_task_with_project(tmp_path, monkeypatch):
    """Test creating task with project flag."""
    import uuid
    project_name = f"TestProject_{uuid.uuid4().hex[:8]}"

    # Create project first
    run_cli("python", "-m", "barely.cli.main", "project", "add", project_name)

    # Create task with project
    result = run_cli("python", "-m", "barely.cli.main", "add", "Work task", "--project", project_name)

    assert result.returncode == 0


def test_cli_ls_filter_by_project(tmp_path, monkeypatch):
    """Test 'barely ls --project' filtering."""
    import uuid
    project_name = f"TestProject_{uuid.uuid4().hex[:8]}"
    task_title = f"Task_{uuid.uuid4().hex[:8]}"

    # Create project and tasks
    run_cli("python", "-m", "barely.cli.main", "project", "add", project_name)
    run_cli("python", "-m", "barely.cli.main", "add", task_title, "--project", project_name)

    # Filter by project
    result = run_cli("python", "-m", "barely.cli.main", "ls", "--project", project_name)

    assert result.returncode == 0
    assert task_title in result.stdout


def test_cli_mv_task_to_column(tmp_path, monkeypatch):
    """Test 'barely mv' command to move task between columns."""
    # Create task
    add_result = run_cli("python", "-m", "barely.cli.main", "add", "My task", "--json")
    task_data = json_module.loads(add_result.stdout)
    task_id = task_data["id"]

    # Move task to column 2 (In Progress)
    result = run_cli("python", "-m", "barely.cli.main", "mv", str(task_id), "In Progress")

    assert result.returncode == 0
    assert "In Progress" in result.stdout or "Moved" in result.stdout


# --- Integration Tests ---

def test_project_workflow():
    """Test complete project workflow: create project, add tasks, filter, delete."""
    # Create project
    project = service.create_project("Integration Test")

    # Add tasks to project
    task1 = service.create_task("Task 1", column_id=1, project_id=project.id)
    task2 = service.create_task("Task 2", column_id=1, project_id=project.id)
    task3 = service.create_task("Unrelated", column_id=1)

    # Filter by project
    project_tasks = service.list_tasks_by_project(project.id)
    assert len(project_tasks) == 2

    # Move task between columns
    service.move_task(task1.id, 2)
    updated = repository.get_task(task1.id)
    assert updated.column_id == 2

    # Delete project (tasks should remain with null project_id)
    service.delete_project(project.id)

    remaining_task = repository.get_task(task1.id)
    assert remaining_task is not None
    assert remaining_task.project_id is None


def test_column_workflow():
    """Test complete column workflow: list columns, move tasks, filter by column."""
    # Get default columns
    columns = service.list_columns()
    assert len(columns) >= 3

    todo_col = next(c for c in columns if c.name == "Todo")
    progress_col = next(c for c in columns if c.name == "In Progress")

    # Create tasks in different columns
    task1 = service.create_task("Todo task", column_id=todo_col.id)
    task2 = service.create_task("Progress task", column_id=progress_col.id)

    # Filter by column
    todo_tasks = service.list_tasks_by_column(todo_col.id)
    assert len(todo_tasks) == 1
    assert todo_tasks[0].title == "Todo task"

    # Move task
    service.move_task(task1.id, progress_col.id)
    progress_tasks = service.list_tasks_by_column(progress_col.id)
    assert len(progress_tasks) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
