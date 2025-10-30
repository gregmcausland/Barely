"""
Test that running 'barely' without arguments launches the REPL.
"""

import subprocess
import sys

def test_default_launches_repl():
    """Test that running CLI without arguments launches REPL."""
    # Send "exit" to the REPL to quit immediately
    result = subprocess.run(
        [sys.executable, "-m", "barely.cli.main"],
        input="exit\n",
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )

    # Check that REPL welcome message appears
    assert "Barely REPL" in result.stdout, f"Expected REPL welcome message, got: {result.stdout}"
    assert "Goodbye!" in result.stdout, f"Expected goodbye message, got: {result.stdout}"
    assert result.returncode == 0, f"Expected exit code 0, got: {result.returncode}"

    print("✓ Default command launches REPL successfully")


def test_commands_still_work():
    """Test that regular commands still work."""
    result = subprocess.run(
        [sys.executable, "-m", "barely.cli.main", "version"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )

    assert "Barely v" in result.stdout, f"Expected version output, got: {result.stdout}"
    assert result.returncode == 0, f"Expected exit code 0, got: {result.returncode}"

    print("✓ Regular commands still work")


if __name__ == "__main__":
    test_default_launches_repl()
    test_commands_still_work()
    print("\n✓ All tests passed!")
