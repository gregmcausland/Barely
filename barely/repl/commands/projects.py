"""
FILE: barely/repl/commands/projects.py
PURPOSE: Project command handlers for REPL
"""

from ..main import console, repl_context
from ..parser import ParseResult
from ...core import service
from ...core.exceptions import (
    BarelyError,
    ProjectNotFoundError,
    InvalidInputError,
)
from ..style import celebrate_bulk, format_relative
from rich.table import Table

# Helper function
def ask_confirmation(message: str) -> bool:
    """Ask user for confirmation (y/n)."""
    response = input(f"{message} (y/n): ").strip().lower()
    return response in ('y', 'yes')

def handle_project_add_command(result: ParseResult) -> None:
    """
    Handle 'project add' command - create new project.

    Args:
        result: Parsed command with args and flags

    Usage:
        project add Work
        project add "My Project"
    """
    if not result.args:
        console.print("[red]Error:[/red] Project name required")
        console.print("[dim]Usage: project add <name>[/dim]")
        return

    # Join all args as the name
    name = " ".join(result.args)

    try:
        project = service.create_project(name)
        console.print(f"[green]✓ Created project:[/green] [cyan]{project.id}[/cyan]: {project.name}")
    except InvalidInputError as e:
        console.print(f"[red]Error:[/red] {e}")
    except BarelyError as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def handle_project_ls_command(result: ParseResult) -> None:
    """
    Handle 'project ls' command - list projects.

    Args:
        result: Parsed command with args and flags

    Usage:
        project ls
    """
    try:
        projects = service.list_projects()

        if not projects:
            console.print("[dim]No projects found[/dim]")
            return

        # Create table with columns
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("ID", style="cyan", width=6)
        table.add_column("Name", style="white")
        table.add_column("Created", style="dim")

        # Add rows for each project
        for project in projects:
            # Show relative created time if available
            created_display = format_relative(project.created_at) if project.created_at else ""

            table.add_row(
                str(project.id),
                project.name,
                created_display,
            )

        console.print(table)
    except BarelyError as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def handle_project_rm_command(result: ParseResult) -> None:
    """
    Handle 'project rm' command - delete project(s).

    Supports:
    - project rm 42          - delete single project
    - project rm 1,2,3       - delete multiple projects
    - project rm *           - delete all projects

    Always confirms before deleting multiple projects.

    Args:
        result: Parsed command with args and flags

    Usage:
        project rm 42
        project rm 1,2,3
        project rm *
    """
    if not result.args:
        console.print("[red]Error:[/red] Project ID(s) required")
        console.print("[dim]Usage: project rm <project_id>[,<project_id>...] or project rm '*'[/dim]")
        return

    try:
        arg = result.args[0].strip()

        # Handle wildcard: delete all projects
        if arg == "*":
            all_projects = service.list_projects()

            if not all_projects:
                console.print("[yellow]No projects to delete[/yellow]")
                return

            # Confirm deletion
            if not ask_confirmation(f"Delete {len(all_projects)} projects?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

            # Delete all in batch
            deleted_count = 0
            for project in all_projects:
                try:
                    service.delete_project(project.id)
                    deleted_count += 1
                except (ProjectNotFoundError, BarelyError) as e:
                    console.print(f"[red]Error deleting project {project.id}:[/red] {e}")

            if deleted_count > 0:
                console.print("[dim]Tasks in these projects now have no project assigned[/dim]")
            bulk_msg = celebrate_bulk(deleted_count, "deleted")
            console.print(f"[green]{bulk_msg}[/green]")
            return

        # Parse comma-separated IDs
        ids = [id.strip() for id in arg.split(",")]

        # Collect valid project IDs
        all_projects = service.list_projects()
        project_dict = {p.id: p for p in all_projects}

        projects_to_delete = []
        invalid_ids = []

        for id_str in ids:
            try:
                project_id = int(id_str)

                # Check if project exists
                if project_id not in project_dict:
                    invalid_ids.append((id_str, "not found"))
                else:
                    projects_to_delete.append(project_id)
            except ValueError:
                invalid_ids.append((id_str, "invalid ID"))

        # Report invalid IDs
        for id_str, reason in invalid_ids:
            console.print(f"[yellow]Warning:[/yellow] Project {id_str} - {reason}")

        if not projects_to_delete:
            console.print("[yellow]No valid projects to delete[/yellow]")
            return

        # Confirm deletion for multiple projects
        if len(projects_to_delete) > 1:
            if not ask_confirmation(f"Delete {len(projects_to_delete)} projects?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        # Delete projects
        deleted_count = 0
        for project_id in projects_to_delete:
            try:
                service.delete_project(project_id)
                console.print(f"[green]✓ Deleted project {project_id}[/green]")
                deleted_count += 1
            except (ProjectNotFoundError, BarelyError) as e:
                console.print(f"[red]Error:[/red] {e}")

        if deleted_count > 0:
            console.print("[dim]Tasks in these projects now have no project assigned[/dim]")
        if deleted_count > 1:
            bulk_msg = celebrate_bulk(deleted_count, "deleted")
            console.print(f"[green]{bulk_msg}[/green]")

    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def handle_project_command(result: ParseResult) -> None:
    """
    Handle 'project' command - dispatch to subcommand.

    Args:
        result: Parsed command with args and flags

    Usage:
        project add <name>
        project ls
        project rm <id>
    """
    if not result.args:
        console.print("[red]Error:[/red] Project subcommand required")
        console.print("[dim]Usage: project <add|ls|rm> ...[/dim]")
        return

    subcommand = result.args[0].lower()
    # Create new ParseResult with subcommand as command and rest as args
    sub_result = ParseResult(subcommand, result.args[1:], result.flags)

    handlers = {
        "add": handle_project_add_command,
        "ls": handle_project_ls_command,
        "rm": handle_project_rm_command,
    }

    handler = handlers.get(subcommand)
    if handler:
        handler(sub_result)
    else:
        console.print(f"[red]Unknown project command:[/red] {subcommand}")
        console.print("[dim]Available: add, ls, rm[/dim]")


# --- Context Management Commands ---


def handle_use_command(result: ParseResult) -> None:
    """
    Handle 'use' command - set current working project.

    Args:
        result: Parsed command with args and flags

    Usage:
        use                 # Show current project
        use work            # Set to Work project
        use none            # Clear project context
    """
    if not result.args:
        # Show current context
        if repl_context.current_project:
            console.print(f"Current project: [cyan]{repl_context.current_project.name}[/cyan]")
        else:
            console.print("[dim]No project context set (showing all projects)[/dim]")
        return

    project_name = result.args[0]

    # Clear context
    if project_name.lower() in ("none", "clear", "."):
        repl_context.current_project = None
        console.print("✓ Cleared project context")
        return

    # Set project
    try:
        project = service.find_project_by_name(project_name)
        if not project:
            console.print(f"[red]Error:[/red] Project '{project_name}' not found")
            console.print("\n[dim]Available projects:[/dim]")
            projects = service.list_projects()
            for p in projects:
                console.print(f"  - {p.name}")
            return

        repl_context.current_project = project
        console.print(f"✓ Now working in project: [cyan]{project.name}[/cyan]")

    except BarelyError as e:
        console.print(f"[red]Unexpected error:[/red] {e}")

