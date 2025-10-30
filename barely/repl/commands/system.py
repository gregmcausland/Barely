"""
FILE: barely/repl/commands/system.py
PURPOSE: System command handlers for REPL
"""

from rich.panel import Panel

from ..main import console, repl_context
from ..parser import ParseResult
from .. import blitz
from .. import undo
from ...core import service

def handle_scope_command(result: ParseResult) -> None:
    """
    Handle 'scope' command - set current scope filter.

    Args:
        result: Parsed command with args and flags

    Usage:
        scope               # Show current scope
        scope today         # Filter to today
        scope week          # Filter to week
        scope backlog       # Filter to backlog
        scope archived      # Filter to archived/completed tasks
        scope all           # Clear scope filter
    """
    if not result.args:
        # Show current scope
        if repl_context.current_scope:
            console.print(f"Current scope: [cyan]{repl_context.current_scope}[/cyan]")
        else:
            console.print("[dim]No scope filter (showing all scopes)[/dim]")
        return

    scope_name = result.args[0].lower()

    # Clear scope filter
    if scope_name in ("all", "none", "clear"):
        repl_context.current_scope = None
        console.print("✓ Cleared scope filter")
        return

    # Validate scope
    valid_scopes = ("today", "week", "backlog", "archived")
    if scope_name not in valid_scopes:
        console.print(f"[red]Error:[/red] Invalid scope '{scope_name}'")
        console.print(f"[dim]Valid scopes: {', '.join(valid_scopes)}, all[/dim]")
        return

    repl_context.current_scope = scope_name
    console.print(f"✓ Filtering to [cyan]{scope_name}[/cyan] tasks")


def handle_undo_command(result: ParseResult) -> None:
    """
    Handle 'undo' command - undo last operation.
    
    Args:
        result: Parsed command (unused)
    
    Usage:
        undo
    """
    success, message = undo.undo_last_operation()
    
    if success:
        console.print(f"[green]✓ {message}[/green]")
    else:
        console.print(f"[yellow]{message}[/yellow]")


def handle_help_command(result: ParseResult) -> None:
    """
    Handle 'help' command - show available commands.

    Args:
        result: Parsed command (unused)
    """
    help_text = """
[bold cyan]Available Commands:[/bold cyan]

  [cyan]add <title> [--ai][/cyan]        Create a new task (--ai improves title with Claude)
  [cyan]ls [--archived] [--project <name>][/cyan]   List tasks
  [cyan]done [<id>[,<id>...]][/cyan]    Mark task(s) as complete (picker if no ID)
  [cyan]rm [<id>[,<id>...]][/cyan]      Delete task(s) (picker if no ID)
  [cyan]edit [<id>] <title>[/cyan]      Update task title (picker if no ID)
  [cyan]desc [<id>][/cyan]              Edit task description in $EDITOR (picker if no ID)
  [cyan]show [<id>][/cyan]              View full task details (picker if no ID)
  [cyan]mv [<id>] <column>[/cyan]       Move task to column (picker if no ID)
  [cyan]assign [<id>] <project>[/cyan]  Assign task to project (picker if no ID)
  [cyan]today[/cyan]                    List today's tasks
  [cyan]week[/cyan]                     List this week's tasks
  [cyan]backlog[/cyan]                  List backlog tasks
  [cyan]archive[/cyan]                  View archived/completed tasks
  [cyan]pull [<id>[,<id>...]] [scope][/cyan] Pull tasks into scope (defaults to today)
  [cyan]blitz[/cyan]                    Enter focused completion mode (with audio viz!)
  [cyan]use <project>[/cyan]           Set current working project
  [cyan]scope <scope>[/cyan]           Set current scope filter
  [cyan]project add <name>[/cyan]       Create a project
  [cyan]project ls[/cyan]               List projects
  [cyan]project rm <id>[,<id>...][/cyan] Delete project(s)
  [cyan]help[/cyan]                     Show this help
  [cyan]clear[/cyan]                    Clear the screen
  [cyan]exit[/cyan] or [cyan]quit[/cyan]            Exit REPL

[bold cyan]Flags:[/bold cyan]

  [cyan]--project <name>[/cyan]         Filter by project name
  [cyan]--archived[/cyan]                Include archived/completed tasks in ls output
  [cyan]--ai[/cyan]                      Improve task title using AI (Claude CLI) for add command

[bold cyan]Examples:[/bold cyan]

  [dim]add Buy groceries
  add "Task with spaces in title"
  add "my messy task braindump" --ai  # Improve title with AI
  ls
  ls --project Work
  ls --project Work
  done 42
  done                        # Shows picker for todo tasks
  done 1,2,3                  # Mark multiple tasks as done
  edit 42 Updated title
  edit Updated title          # Shows picker to select task
  rm 5,6,7                    # Delete multiple tasks
  mv Done                     # Shows picker to select task
  mv 42 "In Progress"
  assign 42 Work              # Assign task 42 to Work project
  assign Work                 # Shows picker to select task
  today                       # View today's focus list
  week                        # View this week's commitment
  backlog                     # View all backlog tasks
  archive                     # View archived/completed tasks
  pull 3,5,7                  # Pull tasks into today (default)
  pull                        # Shows picker for today scope
  pull 42 week                # Pull specific task into week
  pull week                   # Shows picker for week scope
  pull 10 backlog             # Defer task to backlog
  blitz                       # Enter focused mode with audio viz
  use Work                    # Set current project to Work
  scope today                 # Filter to today's tasks
  use none                    # Clear project context
  scope all                   # Clear scope filter
  project add Work
  project ls
  project rm 2
  project rm 2,3,4            # Delete multiple projects[/dim]

[bold yellow]💡 Smart Pickers:[/bold yellow]
  [dim]Commands that need task IDs can show a numbered picker when you
  omit the ID. Pickers are filtered by your current context (project/scope),
  making it easy to find tasks. Enter a number to select, or use commas
  for bulk operations (e.g., "1,3,5" to select multiple).[/dim]
"""
    console.print(Panel(help_text, title="Barely REPL Help", border_style="cyan"))


def handle_clear_command(result: ParseResult) -> None:
    """
    Clear the screen.

    Args:
        result: Parsed command (no arguments used)
    """
    console.clear()
    console.print("[dim]Screen cleared[/dim]")


def handle_blitz_command(result: ParseResult) -> None:
    """
    Handle 'blitz' command - enter focused task completion mode.

    Args:
        result: Parsed command (no arguments used)

    Notes:
        - Displays tasks from current scope (or 'today' by default)
        - Respects current project filter if set
        - Shows live audio waveform visualization
        - Keyboard controls: d=done, s=skip, q=quit, ?=details
        - Returns to normal REPL when complete
    """
    # Pass REPL context to blitz mode
    project_id = repl_context.current_project.id if repl_context.current_project else None
    scope = repl_context.current_scope  # Could be None, will default to 'today'

    blitz.run_blitz_mode(project_id=project_id, scope=scope)


