"""
FILE: barely/cli/commands/system.py
PURPOSE: System commands (version, help, repl, blitz)
"""

import typer

# Import shared objects from main module
# These will be available after main.py imports this module
from ..main import app, console, error_console, __version__


@app.command()
def version():
    """Show Barely version."""
    console.print(f"Barely v{__version__}")


@app.command()
def help():
    """Show available commands and usage."""
    console.print("\n[bold cyan]Barely[/bold cyan] - Minimalist terminal-native task manager\n")
    console.print(f"[dim]Version {__version__}[/dim]\n")

    console.print("[bold]Usage:[/bold]")
    console.print("  barely [command] [options]")
    console.print("  barely                    [dim]# Launch interactive REPL (default)[/dim]\n")

    console.print("[bold]Commands:[/bold]")

    commands = [
        ("add", "Create a new task", 'barely add "Task title" [--ai]'),
        ("ls", "List tasks", "barely ls [--archived] [--project ID]"),
        ("done", "Mark task as complete", "barely done <task_id>"),
        ("edit", "Update task title", 'barely edit <task_id> "New title"'),
        ("desc", "Edit task description", "barely desc <task_id>"),
        ("show", "View full task details", "barely show <task_id>"),
        ("rm", "Delete task(s)", 'barely rm <task_id> | "*"'),
        ("mv", "Move task to column", 'barely mv <task_id> "Column name"'),
        ("assign", "Assign task to project", 'barely assign <task_id> "Project name"'),
        ("today", "List today's tasks", "barely today"),
        ("week", "List this week's tasks", "barely week"),
        ("backlog", "List backlog tasks", "barely backlog"),
        ("archive", "View archived/completed tasks", "barely archive"),
        ("pull", "Pull tasks into scope", "barely pull <task_id(s)> <scope>"),
        ("project add", "Create a project", 'barely project add "Project name"'),
        ("project ls", "List projects", "barely project ls"),
        ("project rm", "Delete project(s)", 'barely project rm <project_id> | "*"'),
        ("repl", "Launch interactive REPL", "barely repl"),
        ("blitz", "Focused task completion mode", "barely blitz"),
        ("version", "Show version", "barely version"),
        ("help", "Show this help message", "barely help"),
    ]

    for cmd, desc, example in commands:
        console.print(f"  [green]{cmd:8}[/green] {desc}")
        console.print(f"           [dim]{example}[/dim]\n")

    console.print("[bold]Global Options:[/bold]")
    console.print("  [yellow]--json[/yellow]    Output as JSON (for scripting)")
    console.print("  [yellow]--raw[/yellow]     Plain text output (no colors)")
    console.print("  [yellow]--help[/yellow]    Show detailed help for a command\n")

    console.print("[bold]Examples:[/bold]")
    console.print("  barely                         # Launch REPL (default)")
    console.print('  barely add "Write documentation"')
    console.print('  barely add "my messy task" --ai  # Improve title with AI')
    console.print("  barely ls --status todo")
    console.print("  barely done 5")
    console.print("  barely done 3,5,7              # Mark multiple tasks as done")
    console.print('  barely edit 5 "Updated title"')
    console.print("  barely rm 5")
    console.print("  barely rm 3,5,7                # Delete multiple tasks")
    console.print("  barely mv 5 Done")
    console.print('  barely assign 5 "Work"         # Assign task to project')
    console.print("  barely today                   # View today's focus list")
    console.print("  barely week                    # View this week's commitment")
    console.print("  barely pull 3,5,7 today        # Pull tasks into today")
    console.print("  barely pull 10 backlog         # Defer task to backlog")
    console.print("  barely project add Work")
    console.print("  barely project rm 2,3          # Delete multiple projects")
    console.print("  barely ls --json\n")


@app.command()
def repl():
    """
    Launch interactive REPL mode.

    The REPL provides:
    - Command history (up/down arrows)
    - Autocomplete (Tab key)
    - All task management commands
    - Exit with Ctrl+D or type 'exit'

    Example:
        barely repl
    """
    # Import here to avoid loading REPL dependencies for one-shot commands
    from ...repl import main as repl_main

    try:
        repl_main()
    except Exception as e:
        error_console.print(f"[red]Error starting REPL:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def blitz():
    """
    Launch blitz mode for focused task completion.

    Blitz mode provides:
    - One task at a time from today's scope
    - Live audio waveform visualization
    - Keyboard controls (d=done, s=skip, q=quit, ?=details)
    - Progress tracking with strikethrough
    - Celebration on completion

    Example:
        barely blitz
    """
    # Import here to avoid loading dependencies for one-shot commands
    from ...repl.blitz import run_blitz_mode

    try:
        run_blitz_mode()
    except Exception as e:
        error_console.print(f"[red]Error in blitz mode:[/red] {e}")
        raise typer.Exit(1)

