"""Quick test of completer functionality."""

# Path setup handled by conftest.py
from barely.repl.completer import create_completer
from prompt_toolkit.document import Document


def test_command_completion():
    """Test that all commands are available for completion."""
    completer = create_completer()

    # Test completing "pr" should suggest "project"
    doc = Document("pr", cursor_position=2)
    completions = list(completer.get_completions(doc, None))

    assert any(c.text == "project" for c in completions), "Should suggest 'project'"
    print("✓ 'project' command completion works")

    # Test completing "m" should suggest "mv"
    doc = Document("m", cursor_position=1)
    completions = list(completer.get_completions(doc, None))

    assert any(c.text == "mv" for c in completions), "Should suggest 'mv'"
    print("✓ 'mv' command completion works")


def test_project_subcommand_completion():
    """Test that project subcommands are suggested."""
    completer = create_completer()

    # After "project " should suggest subcommands
    doc = Document("project ", cursor_position=8)
    completions = list(completer.get_completions(doc, None))

    completion_texts = [c.text for c in completions]
    assert "add" in completion_texts, "Should suggest 'add' subcommand"
    assert "ls" in completion_texts, "Should suggest 'ls' subcommand"
    assert "rm" in completion_texts, "Should suggest 'rm' subcommand"
    print("✓ Project subcommand completion works")

    # Typing "project a" should suggest "add"
    doc = Document("project a", cursor_position=9)
    completions = list(completer.get_completions(doc, None))

    assert any(c.text == "add" for c in completions), "Should suggest 'add'"
    print("✓ Partial project subcommand completion works")


def test_flag_completion():
    """Test that --project flag is available."""
    completer = create_completer()

    # After "ls " should suggest flags including --project
    doc = Document("ls --", cursor_position=5)
    completions = list(completer.get_completions(doc, None))

    completion_texts = [c.text for c in completions]
    assert "--project" in completion_texts, "Should suggest '--project' flag"
    assert "--status" in completion_texts, "Should suggest '--status' flag"
    print("✓ Flag completion works for ls command")


if __name__ == "__main__":
    test_command_completion()
    test_project_subcommand_completion()
    test_flag_completion()
    print("\n✓ All completer tests passed!")
