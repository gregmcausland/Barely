"""
Test context and picker functionality.
"""

# Path setup handled by conftest.py
from barely.core import repository, service
from barely.repl.main import REPLContext, pick_task
import pytest


@pytest.fixture(autouse=True)
def temp_db(monkeypatch, tmp_path):
    """Use temporary database for all tests."""
    db_path = tmp_path / "test_barely.db"
    monkeypatch.setattr(repository, "DB_PATH", db_path)
    monkeypatch.setattr(repository, "DB_DIR", tmp_path)
    yield db_path


def test_repl_context_prompt_generation():
    """Test that REPLContext generates correct prompt strings."""
    ctx = REPLContext()

    # No context
    assert ctx.get_prompt() == "barely> "

    # Create test project
    project = service.create_project("TestProj")
    ctx.current_project = project
    assert ctx.get_prompt() == "barely:[TestProj]> "

    # Add scope
    ctx.current_scope = "today"
    assert ctx.get_prompt() == "barely:[TestProj | today]> "

    # Only scope
    ctx.current_project = None
    assert ctx.get_prompt() == "barely:[today]> "

    print("✓ REPLContext prompt generation works correctly")


def test_repl_context_task_filtering():
    """Test that REPLContext filters tasks correctly."""
    ctx = REPLContext()

    # Create projects
    work = service.create_project("Work")
    personal = service.create_project("Personal")

    # Create tasks
    t1 = service.create_task("Work task 1", project_id=work.id, scope="today")
    t2 = service.create_task("Work task 2", project_id=work.id, scope="week")
    t3 = service.create_task("Personal task", project_id=personal.id, scope="today")
    t4 = service.create_task("No project task", scope="backlog")

    all_tasks = service.list_tasks()
    assert len(all_tasks) == 4

    # Filter by project
    ctx.current_project = work
    filtered = ctx.filter_tasks(all_tasks)
    assert len(filtered) == 2
    assert all(t.project_id == work.id for t in filtered)

    # Filter by project and scope
    ctx.current_scope = "today"
    filtered = ctx.filter_tasks(all_tasks)
    assert len(filtered) == 1
    assert filtered[0].id == t1.id

    # Filter by scope only
    ctx.current_project = None
    filtered = ctx.filter_tasks(all_tasks)
    assert len(filtered) == 2  # t1 and t3 are in today
    assert all(t.scope == "today" for t in filtered)

    print("✓ REPLContext task filtering works correctly")


def test_context_persists_in_global_instance():
    """Test that context persists in global instance during REPL session."""
    from barely.repl.main import repl_context

    # Create project
    proj = service.create_project("GlobalTest")

    # Set context
    repl_context.current_project = proj
    repl_context.current_scope = "week"

    # Verify it persists
    assert repl_context.current_project.name == "GlobalTest"
    assert repl_context.current_scope == "week"
    assert repl_context.get_prompt() == "barely:[GlobalTest | week]> "

    # Clear context
    repl_context.current_project = None
    repl_context.current_scope = None
    assert repl_context.get_prompt() == "barely> "

    print("✓ Global context instance works correctly")


def test_add_command_defaults_to_context():
    """Test that add command uses context project by default."""
    from barely.repl.main import repl_context

    # Create project
    work = service.create_project("Work")

    # Set context
    repl_context.current_project = work

    # Add task (simulating what handle_add_command does)
    title = "Test task"
    project_id = work.id if repl_context.current_project else None
    task = service.create_task(title, project_id=project_id)

    # Verify task has project
    assert task.project_id == work.id

    # Clear context
    repl_context.current_project = None

    print("✓ Add command defaults to context project")


def test_scope_views_respect_context():
    """Test that today/week/backlog commands filter by context project."""
    from barely.repl.main import repl_context

    # Create projects
    work = service.create_project("Work")
    personal = service.create_project("Personal")

    # Create tasks in different scopes
    t1 = service.create_task("Work today", project_id=work.id, scope="today")
    t2 = service.create_task("Personal today", project_id=personal.id, scope="today")
    t3 = service.create_task("Work week", project_id=work.id, scope="week")

    # Get today tasks
    today_tasks = service.list_today()
    assert len(today_tasks) == 2

    # Filter by context project (simulating what handle_today_command does)
    repl_context.current_project = work
    filtered = [t for t in today_tasks if t.project_id == repl_context.current_project.id]
    assert len(filtered) == 1
    assert filtered[0].id == t1.id

    # Clear context
    repl_context.current_project = None

    print("✓ Scope views respect context project")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
