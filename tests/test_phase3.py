#!/usr/bin/env python3
"""
Test script for Phase 3: Minimal CLI

Tests all CLI commands:
- barely version
- barely add <title>
- barely ls [--status] [--project]
- barely done <id>
- barely edit <id> <new_title>
- barely rm <id>
- Output formats: --json, --raw
- Error handling and exit codes
"""

import sys
import subprocess
import json
from pathlib import Path

# Path setup handled by conftest.py for pytest runs
# For direct execution, add project root and fix Windows encoding
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def run_command(cmd, expect_error=False):
    """
    Run a barely CLI command and return result.

    Args:
        cmd: Command as list or string (e.g., ["barely", "add", "Test task"])
        expect_error: If True, don't fail on non-zero exit code

    Returns:
        tuple: (exit_code, stdout, stderr)
    """
    # Convert string to list if needed
    if isinstance(cmd, str):
        # For simple commands without arguments
        parts = cmd.split()
    else:
        parts = cmd

    # Run command using Python module directly (works before install)
    if parts[0] == "barely":
        parts = ["python", "-m", "barely.cli.main"] + parts[1:]

    result = subprocess.run(
        parts,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if not expect_error and result.returncode != 0:
        print(f"Command failed: {' '.join(parts)}")
        print(f"Exit code: {result.returncode}")
        print(f"Stderr: {result.stderr}")
        raise Exception(f"Command failed: {' '.join(parts)}")

    return result.returncode, result.stdout, result.stderr


def test_version():
    """Test version command."""
    print("\n=== Testing 'barely version' ===")

    code, stdout, stderr = run_command("barely version")
    assert code == 0
    assert "Barely v" in stdout
    print(f"✓ Version command works: {stdout.strip()}")


def test_help():
    """Test help command."""
    print("\n=== Testing 'barely help' ===")

    code, stdout, stderr = run_command("barely help")
    assert code == 0
    assert "Commands:" in stdout
    assert "add" in stdout
    assert "ls" in stdout
    assert "done" in stdout
    assert "Examples:" in stdout
    print(f"✓ Help command works and shows all commands")


def test_add_command():
    """Test adding tasks."""
    print("\n=== Testing 'barely add' ===")

    # Add a basic task
    code, stdout, stderr = run_command(["barely", "add", "Test task from CLI"])
    assert code == 0
    assert "Created task" in stdout or "✓" in stdout
    print(f"✓ Basic add: {stdout.strip()}")

    # Add with --json
    code, stdout, stderr = run_command(["barely", "add", "JSON test", "--json"])
    assert code == 0
    data = json.loads(stdout)
    assert data["title"] == "JSON test"
    print(f"✓ Add with --json: task {data['id']} created")

    # Add with --raw
    code, stdout, stderr = run_command(["barely", "add", "Raw test", "--raw"])
    assert code == 0
    assert "Raw test" in stdout
    print(f"✓ Add with --raw: {stdout.strip()}")

    # Test empty title (should fail)
    code, stdout, stderr = run_command(["barely", "add", ""], expect_error=True)
    assert code != 0
    assert "Error" in stderr
    print(f"✓ Empty title rejected")

    return data["id"]  # Return task ID for later tests


def test_ls_command():
    """Test listing tasks."""
    print("\n=== Testing 'barely ls' ===")

    # Basic list
    code, stdout, stderr = run_command("barely ls")
    assert code == 0
    print(f"✓ Basic list works")

    # List with --json
    code, stdout, stderr = run_command("barely ls --json")
    assert code == 0
    data = json.loads(stdout)
    assert isinstance(data, list)
    print(f"✓ List with --json: {len(data)} tasks")

    # List with --raw
    code, stdout, stderr = run_command("barely ls --raw")
    assert code == 0
    print(f"✓ List with --raw works")

    # Filter by status
    code, stdout, stderr = run_command("barely ls --status todo")
    assert code == 0
    print(f"✓ Filter by status works")

    # Invalid status (should fail)
    code, stdout, stderr = run_command("barely ls --status invalid", expect_error=True)
    assert code != 0
    assert "Error" in stderr
    print(f"✓ Invalid status rejected")

    return data


def test_done_command(task_id):
    """Test completing tasks."""
    print("\n=== Testing 'barely done' ===")

    # Complete task
    code, stdout, stderr = run_command(["barely", "done", str(task_id)])
    assert code == 0
    assert "Completed" in stdout or "✓" in stdout
    print(f"✓ Completed task {task_id}")

    # Complete with --json (returns list)
    code, stdout, stderr = run_command(["barely", "done", str(task_id), "--json"])
    assert code == 0
    data = json.loads(stdout)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["status"] == "done"
    print(f"✓ Done with --json: status = {data[0]['status']}")

    # Complete non-existent task (should fail)
    code, stdout, stderr = run_command(["barely", "done", "99999"], expect_error=True)
    assert code != 0
    assert "not found" in stderr.lower()
    print(f"✓ Non-existent task rejected")


def test_edit_command():
    """Test editing task titles."""
    print("\n=== Testing 'barely edit' ===")

    # Create a task to edit
    code, stdout, stderr = run_command(["barely", "add", "Task to edit", "--json"])
    data = json.loads(stdout)
    task_id = data["id"]

    # Edit the task
    code, stdout, stderr = run_command(["barely", "edit", str(task_id), "Edited title"])
    assert code == 0
    assert "Updated" in stdout or "✎" in stdout
    print(f"✓ Edited task {task_id}")

    # Edit with --json
    code, stdout, stderr = run_command(["barely", "edit", str(task_id), "JSON edit", "--json"])
    assert code == 0
    data = json.loads(stdout)
    assert data["title"] == "JSON edit"
    print(f"✓ Edit with --json: {data['title']}")

    # Edit non-existent task (should fail)
    code, stdout, stderr = run_command(["barely", "edit", "99999", "New title"], expect_error=True)
    assert code != 0
    assert "not found" in stderr.lower()
    print(f"✓ Non-existent task rejected")

    # Edit with empty title (should fail)
    code, stdout, stderr = run_command(["barely", "edit", str(task_id), ""], expect_error=True)
    assert code != 0
    assert "Error" in stderr
    print(f"✓ Empty title rejected")


def test_rm_command():
    """Test deleting tasks."""
    print("\n=== Testing 'barely rm' ===")

    # Create a task to delete
    code, stdout, stderr = run_command(["barely", "add", "Task to delete", "--json"])
    data = json.loads(stdout)
    task_id = data["id"]
    print(f"✓ Created task {task_id} for deletion")

    # Delete the task
    code, stdout, stderr = run_command(["barely", "rm", str(task_id)])
    assert code == 0
    assert "Deleted" in stdout or "✗" in stdout
    print(f"✓ Deleted task {task_id}")

    # Delete with --json
    code, stdout, stderr = run_command(["barely", "add", "Delete with JSON", "--json"])
    data = json.loads(stdout)
    task_id = data["id"]

    code, stdout, stderr = run_command(["barely", "rm", str(task_id), "--json"])
    assert code == 0
    data = json.loads(stdout)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == task_id
    print(f"✓ Delete with --json: task {task_id} deleted")

    # Delete non-existent task (should fail)
    code, stdout, stderr = run_command(["barely", "rm", "99999"], expect_error=True)
    assert code != 0
    assert "not found" in stderr.lower()
    print(f"✓ Non-existent task rejected")


def test_workflow():
    """Test a complete workflow."""
    print("\n=== Testing complete workflow ===")

    # Add multiple tasks
    tasks = []
    for i in range(3):
        code, stdout, stderr = run_command(["barely", "add", f"Workflow task {i+1}", "--json"])
        data = json.loads(stdout)
        tasks.append(data["id"])
    print(f"✓ Created 3 tasks: {tasks}")

    # List and verify
    code, stdout, stderr = run_command(["barely", "ls", "--json"])
    data = json.loads(stdout)
    task_ids = [t["id"] for t in data]
    assert all(tid in task_ids for tid in tasks)
    print(f"✓ All tasks visible in list")

    # Complete one task
    code, stdout, stderr = run_command(["barely", "done", str(tasks[0])])
    assert code == 0
    print(f"✓ Completed task {tasks[0]}")

    # Verify status filter works
    code, stdout, stderr = run_command(["barely", "ls", "--status", "done", "--json"])
    done_tasks = json.loads(stdout)
    assert any(t["id"] == tasks[0] for t in done_tasks)
    print(f"✓ Status filter shows completed task")

    # Edit one task
    code, stdout, stderr = run_command(["barely", "edit", str(tasks[1]), "Updated workflow task"])
    assert code == 0
    print(f"✓ Edited task {tasks[1]}")

    # Delete one task
    code, stdout, stderr = run_command(["barely", "rm", str(tasks[2])])
    assert code == 0
    print(f"✓ Deleted task {tasks[2]}")

    # Verify deleted task is gone
    code, stdout, stderr = run_command(["barely", "done", str(tasks[2])], expect_error=True)
    assert code != 0
    print(f"✓ Deleted task no longer accessible")


def main():
    """Run all Phase 3 tests."""
    print("=" * 60)
    print("PHASE 3 TEST SUITE: Minimal CLI")
    print("=" * 60)

    try:
        test_version()
        test_help()
        task_id = test_add_command()
        tasks = test_ls_command()
        test_done_command(task_id)
        test_edit_command()
        test_rm_command()
        test_workflow()

        # Summary
        print("\n" + "=" * 60)
        print("✓ ALL PHASE 3 TESTS PASSED")
        print("=" * 60)
        print("\nPhase 3 Definition of Done:")
        print("✓ Can manage tasks entirely from command line")
        print("✓ All commands work with proper error handling")
        print("✓ Support for --json and --raw output")
        print("✓ Proper exit codes (0=success, 1=error)")
        print("\nPhase 3 COMPLETE! Ready for Phase 4 (Basic REPL)")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
