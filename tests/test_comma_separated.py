"""Test comma-separated ID functionality for bulk operations."""

import subprocess
import sys


def run_cli(*args):
    """Run CLI command with proper encoding."""
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )


def test_comma_separated_done():
    """Test marking multiple tasks as done with comma-separated IDs."""
    print("Testing: barely done with comma-separated IDs")

    # Create three tasks
    result1 = run_cli("python", "-m", "barely.cli.main", "add", "Task 1", "--json")
    result2 = run_cli("python", "-m", "barely.cli.main", "add", "Task 2", "--json")
    result3 = run_cli("python", "-m", "barely.cli.main", "add", "Task 3", "--json")

    import json
    task1_id = json.loads(result1.stdout)["id"]
    task2_id = json.loads(result2.stdout)["id"]
    task3_id = json.loads(result3.stdout)["id"]

    # Mark all three as done using comma-separated IDs
    ids = f"{task1_id},{task2_id},{task3_id}"
    result = run_cli("python", "-m", "barely.cli.main", "done", ids)

    assert result.returncode == 0
    assert "Completed" in result.stdout
    print(f"  ✓ Successfully completed tasks {ids}")
    print(f"  Output: {result.stdout.strip()}")


def test_comma_separated_rm():
    """Test deleting multiple tasks with comma-separated IDs."""
    print("\nTesting: barely rm with comma-separated IDs")

    # Create three tasks
    result1 = run_cli("python", "-m", "barely.cli.main", "add", "Delete 1", "--json")
    result2 = run_cli("python", "-m", "barely.cli.main", "add", "Delete 2", "--json")
    result3 = run_cli("python", "-m", "barely.cli.main", "add", "Delete 3", "--json")

    import json
    task1_id = json.loads(result1.stdout)["id"]
    task2_id = json.loads(result2.stdout)["id"]
    task3_id = json.loads(result3.stdout)["id"]

    # Delete all three using comma-separated IDs
    ids = f"{task1_id},{task2_id},{task3_id}"
    result = run_cli("python", "-m", "barely.cli.main", "rm", ids)

    assert result.returncode == 0
    assert "Deleted" in result.stdout
    print(f"  ✓ Successfully deleted tasks {ids}")
    print(f"  Output: {result.stdout.strip()}")


def test_comma_separated_project_rm():
    """Test deleting multiple projects with comma-separated IDs."""
    print("\nTesting: barely project rm with comma-separated IDs")

    # Create three projects
    import uuid
    name1 = f"Proj_{uuid.uuid4().hex[:6]}"
    name2 = f"Proj_{uuid.uuid4().hex[:6]}"
    name3 = f"Proj_{uuid.uuid4().hex[:6]}"

    result1 = run_cli("python", "-m", "barely.cli.main", "project", "add", name1, "--json")
    result2 = run_cli("python", "-m", "barely.cli.main", "project", "add", name2, "--json")
    result3 = run_cli("python", "-m", "barely.cli.main", "project", "add", name3, "--json")

    import json
    proj1_id = json.loads(result1.stdout)["id"]
    proj2_id = json.loads(result2.stdout)["id"]
    proj3_id = json.loads(result3.stdout)["id"]

    # Delete all three using comma-separated IDs
    ids = f"{proj1_id},{proj2_id},{proj3_id}"
    result = run_cli("python", "-m", "barely.cli.main", "project", "rm", ids)

    assert result.returncode == 0
    assert "Deleted" in result.stdout
    print(f"  ✓ Successfully deleted projects {ids}")
    print(f"  Output: {result.stdout.strip()}")


def test_comma_separated_with_spaces():
    """Test that spaces around commas are handled correctly."""
    print("\nTesting: comma-separated IDs with spaces")

    # Create two tasks
    result1 = run_cli("python", "-m", "barely.cli.main", "add", "Space test 1", "--json")
    result2 = run_cli("python", "-m", "barely.cli.main", "add", "Space test 2", "--json")

    import json
    task1_id = json.loads(result1.stdout)["id"]
    task2_id = json.loads(result2.stdout)["id"]

    # Delete with spaces around commas
    ids = f"{task1_id} , {task2_id}"
    result = run_cli("python", "-m", "barely.cli.main", "rm", ids)

    assert result.returncode == 0
    assert "Deleted" in result.stdout
    print(f"  ✓ Successfully handled IDs with spaces: '{ids}'")


def test_comma_separated_partial_failure():
    """Test that valid IDs are processed even when some are invalid."""
    print("\nTesting: comma-separated with some invalid IDs")

    # Create one valid task
    result = run_cli("python", "-m", "barely.cli.main", "add", "Valid task", "--json")

    import json
    valid_id = json.loads(result.stdout)["id"]

    # Try to delete with mix of valid and invalid IDs
    ids = f"{valid_id},99999"
    result = run_cli("python", "-m", "barely.cli.main", "rm", ids)

    # Should succeed for valid ID but show error for invalid
    assert "Deleted" in result.stdout
    assert "not found" in result.stderr or "Error" in result.stderr
    print(f"  ✓ Processed valid ID and reported error for invalid ID")
    print(f"  Stdout: {result.stdout.strip()}")
    print(f"  Stderr: {result.stderr.strip()}")


if __name__ == "__main__":
    try:
        test_comma_separated_done()
        test_comma_separated_rm()
        test_comma_separated_project_rm()
        test_comma_separated_with_spaces()
        test_comma_separated_partial_failure()

        print("\n" + "="*60)
        print("✓ All comma-separated tests passed!")
        print("="*60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
