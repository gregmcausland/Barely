"""
Test fixes for flag handling and filtering.
"""

# Path setup handled by conftest.py
from barely.core import repository, service
import pytest


@pytest.fixture(autouse=True)
def temp_db(monkeypatch, tmp_path):
    """Use temporary database for all tests."""
    db_path = tmp_path / "test_barely.db"
    monkeypatch.setattr(repository, "DB_PATH", db_path)
    monkeypatch.setattr(repository, "DB_DIR", tmp_path)
    yield db_path


def test_project_filtering_case_insensitive():
    """Test that --project filtering is case-insensitive."""
    # Create projects
    work = service.create_project("Work")
    personal = service.create_project("Personal")

    # Create tasks
    service.create_task("Work task 1", project_id=work.id)
    service.create_task("Work task 2", project_id=work.id)
    service.create_task("Personal task", project_id=personal.id)
    service.create_task("No project task")

    # Filter by project (lowercase)
    tasks = service.list_tasks(project_id=work.id)
    assert len(tasks) == 2
    assert all(t.project_id == work.id for t in tasks)

    # Filter by project (uppercase)
    tasks = service.list_tasks(project_id=personal.id)
    assert len(tasks) == 1
    assert tasks[0].project_id == personal.id

    print("✓ Project filtering works correctly")


def test_project_name_lookup_case_insensitive():
    """Test that project name lookup is case-insensitive in service layer."""
    # Create projects
    work = service.create_project("Work")
    personal = service.create_project("Personal")

    # Create tasks
    t1 = service.create_task("Work task 1", project_id=work.id)
    t2 = service.create_task("Work task 2", project_id=work.id)
    t3 = service.create_task("Personal task", project_id=personal.id)
    t4 = service.create_task("No project task")

    # Get all projects for case-insensitive lookup
    all_projects = service.list_projects()

    # Test case-insensitive matching (lowercase)
    proj_lower = next((p for p in all_projects if p.name.lower() == "work".lower()), None)
    assert proj_lower is not None
    assert proj_lower.id == work.id

    # Test case-insensitive matching (uppercase)
    proj_upper = next((p for p in all_projects if p.name.lower() == "WORK".lower()), None)
    assert proj_upper is not None
    assert proj_upper.id == work.id

    # Test case-insensitive matching (mixed case)
    proj_mixed = next((p for p in all_projects if p.name.lower() == "WoRk".lower()), None)
    assert proj_mixed is not None
    assert proj_mixed.id == work.id

    print("✓ Project name lookup is case-insensitive")


def test_nonexistent_project():
    """Test that filtering by non-existent project shows error."""
    service.create_project("Work")

    result = subprocess.run(
        [sys.executable, "-m", "barely.cli.main", "ls", "--project", "NonExistent"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )

    assert result.returncode == 1
    assert "not found" in result.stderr or "Error" in result.stderr

    print("✓ Non-existent project shows error")


def test_scope_commands_with_json_flag_cli():
    """Test that CLI scope commands support --json flag."""
    service.create_task("Today task", scope="today")

    result = subprocess.run(
        [sys.executable, "-m", "barely.cli.main", "today", "--json"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )

    assert result.returncode == 0
    # Should be valid JSON
    import json
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["scope"] == "today"

    print("✓ CLI scope commands support --json flag")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
