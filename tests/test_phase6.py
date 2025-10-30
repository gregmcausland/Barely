"""
Test suite for Phase 6: Pull-Based Workflow

Tests repository, service, CLI, and REPL integration for:
- Scope management (backlog, week, today)
- Pull operations (moving tasks between scopes)
- Scope-specific views
- Default scope behavior
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


# --- Repository Layer Tests: Scope Operations ---

def test_create_task_with_default_scope():
    """Test that new tasks default to backlog scope."""
    task = repository.create_task("Test task", column_id=1)

    assert task.scope == "backlog"


def test_create_task_with_explicit_scope():
    """Test creating task with explicit scope."""
    task = repository.create_task("Test task", column_id=1, scope="today")

    assert task.scope == "today"


def test_list_tasks_by_scope_backlog():
    """Test listing tasks in backlog scope."""
    # Create tasks in different scopes
    repository.create_task("Backlog task 1", column_id=1, scope="backlog")
    repository.create_task("Week task", column_id=1, scope="week")
    repository.create_task("Backlog task 2", column_id=1, scope="backlog")
    repository.create_task("Today task", column_id=1, scope="today")

    backlog_tasks = repository.list_tasks_by_scope("backlog")

    assert len(backlog_tasks) == 2
    for task in backlog_tasks:
        assert task.scope == "backlog"


def test_list_tasks_by_scope_week():
    """Test listing tasks in week scope."""
    repository.create_task("Week task 1", column_id=1, scope="week")
    repository.create_task("Week task 2", column_id=1, scope="week")
    repository.create_task("Backlog task", column_id=1, scope="backlog")

    week_tasks = repository.list_tasks_by_scope("week")

    assert len(week_tasks) == 2
    for task in week_tasks:
        assert task.scope == "week"


def test_list_tasks_by_scope_today():
    """Test listing tasks in today scope."""
    repository.create_task("Today task", column_id=1, scope="today")
    repository.create_task("Week task", column_id=1, scope="week")

    today_tasks = repository.list_tasks_by_scope("today")

    assert len(today_tasks) == 1
    assert today_tasks[0].scope == "today"


def test_list_tasks_by_scope_empty():
    """Test listing scope with no tasks."""
    repository.create_task("Backlog task", column_id=1, scope="backlog")

    today_tasks = repository.list_tasks_by_scope("today")

    assert today_tasks == []


def test_update_task_scope():
    """Test updating a task's scope."""
    task = repository.create_task("Test task", column_id=1, scope="backlog")
    original_id = task.id

    updated = repository.update_task_scope(task.id, "today")

    assert updated.id == original_id
    assert updated.scope == "today"

    # Verify it persisted
    fetched = repository.get_task(task.id)
    assert fetched.scope == "today"


def test_update_task_scope_nonexistent():
    """Test updating scope of nonexistent task raises error."""
    with pytest.raises(exceptions.TaskNotFoundError):
        repository.update_task_scope(999, "today")


# --- Service Layer Tests: Scope Operations ---

def test_service_create_task_default_scope():
    """Test service layer creates task with default backlog scope."""
    task = service.create_task("Test task")

    assert task.scope == "backlog"


def test_service_create_task_with_scope():
    """Test service layer creates task with explicit scope."""
    task = service.create_task("Test task", scope="week")

    assert task.scope == "week"


def test_service_create_task_invalid_scope():
    """Test service layer rejects invalid scope."""
    with pytest.raises(exceptions.InvalidInputError) as exc_info:
        service.create_task("Test task", scope="invalid")

    assert "Invalid scope" in str(exc_info.value)


def test_service_list_backlog():
    """Test service layer lists backlog tasks."""
    service.create_task("Backlog 1", scope="backlog")
    service.create_task("Week task", scope="week")
    service.create_task("Backlog 2", scope="backlog")

    backlog = service.list_backlog()

    assert len(backlog) == 2
    for task in backlog:
        assert task.scope == "backlog"


def test_service_list_week():
    """Test service layer lists week tasks."""
    service.create_task("Week 1", scope="week")
    service.create_task("Week 2", scope="week")
    service.create_task("Backlog task", scope="backlog")

    week = service.list_week()

    assert len(week) == 2
    for task in week:
        assert task.scope == "week"


def test_service_list_today():
    """Test service layer lists today tasks."""
    service.create_task("Today 1", scope="today")
    service.create_task("Week task", scope="week")
    service.create_task("Today 2", scope="today")

    today = service.list_today()

    assert len(today) == 2
    for task in today:
        assert task.scope == "today"


def test_service_pull_task():
    """Test pulling a task from backlog to week."""
    task = service.create_task("Test task", scope="backlog")

    pulled = service.pull_task(task.id, "week")

    assert pulled.id == task.id
    assert pulled.scope == "week"

    # Verify it moved
    backlog = service.list_backlog()
    week = service.list_week()
    assert len(backlog) == 0
    assert len(week) == 1


def test_service_pull_task_to_today():
    """Test pulling a task from week to today."""
    task = service.create_task("Test task", scope="week")

    pulled = service.pull_task(task.id, "today")

    assert pulled.scope == "today"


def test_service_pull_task_back_to_backlog():
    """Test pulling a task back to backlog (defer)."""
    task = service.create_task("Test task", scope="today")

    pulled = service.pull_task(task.id, "backlog")

    assert pulled.scope == "backlog"


def test_service_pull_task_invalid_scope():
    """Test pulling task with invalid scope."""
    task = service.create_task("Test task")

    with pytest.raises(exceptions.InvalidInputError) as exc_info:
        service.pull_task(task.id, "invalid")

    assert "Invalid scope" in str(exc_info.value)


def test_service_pull_task_nonexistent():
    """Test pulling nonexistent task."""
    with pytest.raises(exceptions.TaskNotFoundError):
        service.pull_task(999, "today")


def test_service_pull_tasks_multiple():
    """Test pulling multiple tasks at once."""
    task1 = service.create_task("Task 1", scope="backlog")
    task2 = service.create_task("Task 2", scope="backlog")
    task3 = service.create_task("Task 3", scope="backlog")

    pulled = service.pull_tasks([task1.id, task2.id, task3.id], "week")

    assert len(pulled) == 3
    for task in pulled:
        assert task.scope == "week"

    # Verify they all moved
    backlog = service.list_backlog()
    week = service.list_week()
    assert len(backlog) == 0
    assert len(week) == 3


def test_service_pull_tasks_invalid_scope():
    """Test pull_tasks rejects invalid scope."""
    task = service.create_task("Test task")

    with pytest.raises(exceptions.InvalidInputError):
        service.pull_tasks([task.id], "invalid")


# --- CLI Tests: Scope Commands ---

def test_cli_today_empty():
    """Test CLI today command with no tasks."""
    result = run_cli("python", "-m", "barely.cli.main", "today")

    assert result.returncode == 0
    assert "No tasks for today" in result.stdout or "today" in result.stdout.lower()


def test_cli_today_with_tasks():
    """Test CLI today command shows today's tasks."""
    task1 = service.create_task("Today task 1", scope="today")
    task2 = service.create_task("Today task 2", scope="today")
    service.create_task("Week task", scope="week")

    result = run_cli("python", "-m", "barely.cli.main", "today")

    assert result.returncode == 0
    assert "Today task 1" in result.stdout
    assert "Today task 2" in result.stdout
    assert "Week task" not in result.stdout


def test_cli_week_with_tasks():
    """Test CLI week command shows this week's tasks."""
    service.create_task("Week task 1", scope="week")
    service.create_task("Week task 2", scope="week")
    service.create_task("Backlog task", scope="backlog")

    result = run_cli("python", "-m", "barely.cli.main", "week")

    assert result.returncode == 0
    assert "Week task 1" in result.stdout
    assert "Week task 2" in result.stdout
    assert "Backlog task" not in result.stdout


def test_cli_backlog_with_tasks():
    """Test CLI backlog command shows backlog tasks."""
    service.create_task("Backlog task 1", scope="backlog")
    service.create_task("Backlog task 2", scope="backlog")
    service.create_task("Today task", scope="today")

    result = run_cli("python", "-m", "barely.cli.main", "backlog")

    assert result.returncode == 0
    assert "Backlog task 1" in result.stdout
    assert "Backlog task 2" in result.stdout
    assert "Today task" not in result.stdout


def test_cli_pull_single_task():
    """Test CLI pull command for single task."""
    task = service.create_task("Test task", scope="backlog")

    result = run_cli("python", "-m", "barely.cli.main", "pull", str(task.id), "today")

    assert result.returncode == 0
    assert "Pulled task" in result.stdout or "today" in result.stdout

    # Verify task moved
    today = service.list_today()
    assert len(today) == 1
    assert today[0].id == task.id


def test_cli_pull_multiple_tasks():
    """Test CLI pull command for multiple tasks."""
    task1 = service.create_task("Task 1", scope="backlog")
    task2 = service.create_task("Task 2", scope="backlog")
    task3 = service.create_task("Task 3", scope="backlog")

    result = run_cli("python", "-m", "barely.cli.main", "pull", f"{task1.id},{task2.id},{task3.id}", "week")

    assert result.returncode == 0

    # Verify all tasks moved
    week = service.list_week()
    assert len(week) == 3
    week_ids = [t.id for t in week]
    assert task1.id in week_ids
    assert task2.id in week_ids
    assert task3.id in week_ids


def test_cli_pull_invalid_scope():
    """Test CLI pull command with invalid scope."""
    task = service.create_task("Test task", scope="backlog")

    result = run_cli("python", "-m", "barely.cli.main", "pull", str(task.id), "invalid")

    assert result.returncode == 1
    assert "Invalid scope" in result.stderr or "Error" in result.stderr


def test_cli_pull_nonexistent_task():
    """Test CLI pull command with nonexistent task."""
    result = run_cli("python", "-m", "barely.cli.main", "pull", "999", "today")

    assert result.returncode == 1
    assert "not found" in result.stderr.lower() or "error" in result.stderr.lower()


def test_cli_today_json_output():
    """Test CLI today command with JSON output."""
    service.create_task("Today task", scope="today")

    result = run_cli("python", "-m", "barely.cli.main", "today", "--json")

    assert result.returncode == 0
    tasks = json_module.loads(result.stdout)
    assert len(tasks) == 1
    assert tasks[0]["scope"] == "today"


def test_cli_ls_shows_scope():
    """Test that ls command shows scope column."""
    service.create_task("Backlog task", scope="backlog")
    service.create_task("Week task", scope="week")
    service.create_task("Today task", scope="today")

    result = run_cli("python", "-m", "barely.cli.main", "ls")

    assert result.returncode == 0
    # Check that scope values appear in output
    assert "backlog" in result.stdout
    assert "week" in result.stdout
    assert "today" in result.stdout


# --- End-to-End Workflow Tests ---

def test_workflow_monday_planning():
    """Test typical Monday workflow: pull from backlog to week."""
    # Create backlog
    task1 = service.create_task("Write docs", scope="backlog")
    task2 = service.create_task("Fix bug", scope="backlog")
    task3 = service.create_task("Review PR", scope="backlog")
    service.create_task("Future task", scope="backlog")

    # Monday planning: pull 3 tasks into week
    service.pull_tasks([task1.id, task2.id, task3.id], "week")

    # Verify state
    backlog = service.list_backlog()
    week = service.list_week()
    assert len(backlog) == 1
    assert len(week) == 3


def test_workflow_daily_planning():
    """Test typical daily workflow: pull from week to today."""
    # Setup week
    task1 = service.create_task("Task 1", scope="week")
    task2 = service.create_task("Task 2", scope="week")
    task3 = service.create_task("Task 3", scope="week")

    # Daily planning: pull 2 tasks into today
    service.pull_tasks([task1.id, task2.id], "today")

    # Verify state
    week = service.list_week()
    today = service.list_today()
    assert len(week) == 1
    assert len(today) == 2


def test_workflow_deferring_task():
    """Test deferring a task back to backlog."""
    # Task in today that we can't finish
    task = service.create_task("Blocked task", scope="today")

    # Defer it back to backlog
    service.pull_task(task.id, "backlog")

    # Verify state
    today = service.list_today()
    backlog = service.list_backlog()
    assert len(today) == 0
    assert len(backlog) == 1


def test_workflow_complete_sequence():
    """Test complete workflow: backlog -> week -> today -> done."""
    # Start with task in backlog
    task = service.create_task("Important task", scope="backlog")
    assert service.list_backlog()[0].id == task.id

    # Pull to week
    service.pull_task(task.id, "week")
    assert service.list_week()[0].id == task.id
    assert len(service.list_backlog()) == 0

    # Pull to today
    service.pull_task(task.id, "today")
    assert service.list_today()[0].id == task.id
    assert len(service.list_week()) == 0

    # Complete it
    service.complete_task(task.id)
    completed = service.get_task(task.id)
    assert completed.status == "done"
    assert completed.scope == "today"  # Scope doesn't change on completion


def test_workflow_direct_backlog_to_today():
    """Test pulling directly from backlog to today (skip week)."""
    task = service.create_task("Urgent task", scope="backlog")

    # Pull directly to today
    service.pull_task(task.id, "today")

    assert len(service.list_today()) == 1
    assert len(service.list_backlog()) == 0


# --- Edge Cases ---

def test_task_retains_other_fields_when_pulled():
    """Test that pulling a task only changes scope, not other fields."""
    task = service.create_task("Test task", scope="backlog")
    original_title = task.title
    original_status = task.status
    original_column = task.column_id

    pulled = service.pull_task(task.id, "today")

    assert pulled.title == original_title
    assert pulled.status == original_status
    assert pulled.column_id == original_column
    assert pulled.scope == "today"


def test_completed_tasks_stay_in_scope():
    """Test that completed tasks remain in their scope."""
    task = service.create_task("Test task", scope="today")

    completed = service.complete_task(task.id)

    assert completed.scope == "today"
    assert completed.status == "done"

    # Still appears in today list
    today = service.list_today()
    assert len(today) == 1
    assert today[0].id == task.id


def test_default_task_creation_uses_backlog():
    """Test that tasks created via add command default to backlog."""
    result = run_cli("python", "-m", "barely.cli.main", "add", "New task")

    assert result.returncode == 0

    # Verify it's in backlog
    backlog = service.list_backlog()
    assert len(backlog) == 1
    assert backlog[0].title == "New task"


# Get the service.get_task function
def test_get_task_helper():
    """Helper function to get task by ID from service layer."""
    # This is already tested via service.pull_task which calls repository.get_task
    # Just verify the API exists
    task = service.create_task("Test")
    fetched = repository.get_task(task.id)
    assert fetched.id == task.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
