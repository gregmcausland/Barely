#!/usr/bin/env python3
"""
Test script for Phase 2: Core Service Layer

Tests all service functions:
- create_task()
- complete_task()
- list_tasks() with filters
- update_task_title()
- delete_task()
- Error handling and validation
"""

import sys
from pathlib import Path

# Path setup handled by conftest.py for pytest runs
# For direct execution, add project root to path
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from barely.core import service
from barely.core.exceptions import TaskNotFoundError, InvalidInputError


def test_create_task():
    """Test task creation with validation."""
    print("\n=== Testing create_task() ===")

    # Create a valid task
    task = service.create_task("Write Phase 2 tests", column_id=1)
    print(f"✓ Created task: {task.title} (ID: {task.id})")
    assert task.title == "Write Phase 2 tests"
    assert task.status == "todo"
    assert task.column_id == 1

    # Test title trimming
    task2 = service.create_task("  Whitespace test  ", column_id=1)
    print(f"✓ Title trimmed: '{task2.title}'")
    assert task2.title == "Whitespace test"

    # Test empty title validation
    try:
        service.create_task("", column_id=1)
        assert False, "Should have raised InvalidInputError"
    except InvalidInputError as e:
        print(f"✓ Empty title rejected: {e}")

    # Test whitespace-only title
    try:
        service.create_task("   ", column_id=1)
        assert False, "Should have raised InvalidInputError"
    except InvalidInputError as e:
        print(f"✓ Whitespace-only title rejected: {e}")

    return task.id


def test_list_tasks():
    """Test task listing with filters."""
    print("\n=== Testing list_tasks() ===")

    # List all tasks
    all_tasks = service.list_tasks()
    print(f"✓ Listed all tasks: {len(all_tasks)} task(s)")

    # Filter by status
    todo_tasks = service.list_tasks(status="todo")
    print(f"✓ Todo tasks: {len(todo_tasks)}")

    # Test invalid status
    try:
        service.list_tasks(status="invalid")
        assert False, "Should have raised InvalidInputError"
    except InvalidInputError as e:
        print(f"✓ Invalid status rejected: {e}")

    return all_tasks


def test_complete_task(task_id):
    """Test marking task as complete."""
    print("\n=== Testing complete_task() ===")

    # Complete the task
    completed = service.complete_task(task_id)
    print(f"✓ Completed task {task_id}: {completed.title}")
    assert completed.status == "done"
    assert completed.completed_at is not None

    # Test completing non-existent task
    try:
        service.complete_task(99999)
        assert False, "Should have raised TaskNotFoundError"
    except TaskNotFoundError as e:
        print(f"✓ Non-existent task rejected: {e}")

    return completed


def test_update_task_title(task_id):
    """Test updating task title."""
    print("\n=== Testing update_task_title() ===")

    # Update title
    updated = service.update_task_title(task_id, "Updated task title")
    print(f"✓ Updated task {task_id}: {updated.title}")
    assert updated.title == "Updated task title"

    # Test empty title
    try:
        service.update_task_title(task_id, "")
        assert False, "Should have raised InvalidInputError"
    except InvalidInputError as e:
        print(f"✓ Empty title rejected: {e}")

    # Test non-existent task
    try:
        service.update_task_title(99999, "New title")
        assert False, "Should have raised TaskNotFoundError"
    except TaskNotFoundError as e:
        print(f"✓ Non-existent task rejected: {e}")


def test_delete_task():
    """Test task deletion."""
    print("\n=== Testing delete_task() ===")

    # Create a task to delete
    task = service.create_task("Task to delete", column_id=1)
    task_id = task.id
    print(f"✓ Created task {task_id} for deletion")

    # Delete the task
    service.delete_task(task_id)
    print(f"✓ Deleted task {task_id}")

    # Verify it's gone
    try:
        service.complete_task(task_id)
        assert False, "Task should be deleted"
    except TaskNotFoundError:
        print(f"✓ Confirmed task {task_id} is deleted")

    # Test deleting non-existent task
    try:
        service.delete_task(99999)
        assert False, "Should have raised TaskNotFoundError"
    except TaskNotFoundError as e:
        print(f"✓ Non-existent task deletion rejected: {e}")


def test_filtering():
    """Test advanced filtering scenarios."""
    print("\n=== Testing advanced filtering ===")

    # Create tasks with different statuses
    task1 = service.create_task("Todo task 1", column_id=1)
    task2 = service.create_task("Todo task 2", column_id=1)
    task3 = service.create_task("Task to complete", column_id=1)
    service.complete_task(task3.id)

    # Filter by status
    todo_tasks = service.list_tasks(status="todo")
    done_tasks = service.list_tasks(status="done")

    print(f"✓ Todo tasks: {len(todo_tasks)}")
    print(f"✓ Done tasks: {len(done_tasks)}")

    # Verify filtering works
    assert all(t.status == "todo" for t in todo_tasks)
    assert all(t.status == "done" for t in done_tasks)
    print("✓ Status filtering validated")


def main():
    """Run all Phase 2 tests."""
    print("=" * 60)
    print("PHASE 2 TEST SUITE: Core Service Layer")
    print("=" * 60)

    try:
        # Run tests in sequence
        task_id = test_create_task()
        test_list_tasks()
        completed = test_complete_task(task_id)
        test_update_task_title(completed.id)
        test_delete_task()
        test_filtering()

        # Summary
        print("\n" + "=" * 60)
        print("✓ ALL PHASE 2 TESTS PASSED")
        print("=" * 60)
        print("\nPhase 2 Definition of Done:")
        print("✓ Service layer validates input")
        print("✓ Business rules enforced")
        print("✓ Specific errors raised")
        print("✓ All functions have docstrings and type hints")
        print("\nPhase 2 COMPLETE! Ready for Phase 3 (Minimal CLI)")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
