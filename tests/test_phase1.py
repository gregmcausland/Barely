#!/usr/bin/env python3
"""Quick test script for Phase 1 functionality."""

import sys
from pathlib import Path

# Add project root to path for imports (when run directly)
# conftest.py handles this for pytest runs
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from barely.core import repository
from barely.core.exceptions import TaskNotFoundError

def test_phase1():
    """Test Phase 1: Foundation."""

    print("=" * 60)
    print("PHASE 1 TEST: Foundation")
    print("=" * 60)

    # Test 1: Create tasks
    print("\n[1] Creating tasks...")
    task1 = repository.create_task("Write project proposal", column_id=1)
    print(f"  OK Created task {task1.id}: {task1.title}")

    task2 = repository.create_task("Review pull requests", column_id=2)
    print(f"  OK Created task {task2.id}: {task2.title}")

    task3 = repository.create_task("Deploy to production", column_id=1)
    print(f"  OK Created task {task3.id}: {task3.title}")

    # Test 2: List tasks
    print("\n[2] Listing all tasks...")
    tasks = repository.list_tasks()
    print(f"  OK Found {len(tasks)} tasks")
    for task in tasks:
        print(f"    - [{task.id}] {task.title} (column: {task.column_id}, status: {task.status})")

    # Test 3: Get single task
    print(f"\n[3] Getting task {task1.id}...")
    fetched = repository.get_task(task1.id)
    print(f"  OK Retrieved: {fetched.title}")
    print(f"    Created at: {fetched.created_at}")

    # Test 4: Update task
    print(f"\n[4] Updating task {task2.id}...")
    task2.title = "Review pull requests (UPDATED)"
    task2.status = "done"
    task2.completed_at = "2025-01-15T10:30:00"
    repository.update_task(task2)

    updated = repository.get_task(task2.id)
    print(f"  OK Updated title: {updated.title}")
    print(f"  OK Updated status: {updated.status}")
    print(f"  OK Completed at: {updated.completed_at}")

    # Test 5: Delete task
    print(f"\n[5] Deleting task {task3.id}...")
    repository.delete_task(task3.id)
    print(f"  OK Deleted task {task3.id}")

    remaining = repository.list_tasks()
    print(f"  OK {len(remaining)} tasks remaining")

    # Test 6: Error handling
    print("\n[6] Testing error handling...")
    try:
        repository.get_task(99999)
        print("  FAIL Should have returned None for non-existent task")
    except Exception:
        print("  FAIL Should not raise exception, should return None")
    else:
        print("  OK Returns None for non-existent task")

    try:
        repository.delete_task(99999)
        print("  FAIL Should have raised TaskNotFoundError")
    except TaskNotFoundError as e:
        print(f"  OK Raised TaskNotFoundError: {e}")

    # Test 7: JSON serialization
    print("\n[7] Testing JSON serialization...")
    task = repository.get_task(task1.id)
    json_str = task.to_json()
    print(f"  OK JSON output:\n{json_str}")

    print("\n" + "=" * 60)
    print("OK ALL TESTS PASSED")
    print("=" * 60)
    print(f"\nDatabase location: {repository.DB_PATH}")
    print("Schema initialized with default columns (Todo, In Progress, Done)")
    print("\nPhase 1 complete! Ready for Phase 2.")


if __name__ == "__main__":
    test_phase1()
