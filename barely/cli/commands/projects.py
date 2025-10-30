"""
FILE: barely/cli/commands/projects.py
PURPOSE: Project management commands (project_add, project_ls, project_rm)
"""

import json
from typing import Optional

import typer
from rich.table import Table

from ..main import app, console, error_console, project_app
from ...core import service
from ...core.exceptions import (
    BarelyError,
    ProjectNotFoundError,
    InvalidInputError,
)

@project_app.command("add")
def project_add(
    name: str = typer.Argument(..., help="Project name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    Create a new project.

    Example:
        barely project add "Work"
        barely project add "Personal" --json
    """
    try:
        project = service.create_project(name)

        if json_output:
            console.print(project.to_json())
        elif raw:
            console.print(f"{project.id}: {project.name}")
        else:
            console.print(f"[green]✓[/green] Created project {project.id}: {project.name}")

    except InvalidInputError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@project_app.command("ls")
def project_ls(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
):
    """
    List all projects.

    Example:
        barely project ls
        barely project ls --json
    """
    try:
        projects = service.list_projects()

        if json_output:
            # Output as JSON array
            projects_data = [
                {
                    "id": p.id,
                    "name": p.name,
                    "created_at": p.created_at,
                }
                for p in projects
            ]
            console.print(json.dumps(projects_data, indent=2))

        elif raw:
            # Plain text, one per line
            for project in projects:
                console.print(f"{project.id}: {project.name}")

        else:
            # Rich table output
            if not projects:
                console.print("[dim]No projects found[/dim]")
                return

            table = Table(title="Projects")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="white")
            table.add_column("Created", style="dim")

            for project in projects:
                # Format created_at as just the date if available
                created_display = project.created_at.split("T")[0] if project.created_at else ""

                table.add_row(
                    str(project.id),
                    project.name,
                    created_display,
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(projects)} project(s)[/dim]")

    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@project_app.command("rm")
def project_rm(
    project_ids: str = typer.Argument(..., help="Project ID(s) to delete (comma-separated or '*' for all)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    raw: bool = typer.Option(False, "--raw", help="Plain text output (no colors)"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt"),
):
    """
    Delete one or more projects permanently.

    Supports:
    - barely project rm 2           - delete single project
    - barely project rm 2,3,5       - delete multiple projects
    - barely project rm '*'         - delete all projects

    Tasks associated with deleted projects will have their project_id set to NULL.

    Confirms before deleting multiple projects (use -y to skip).

    Example:
        barely project rm 2
        barely project rm 2,3,5
        barely project rm '*'
        barely project rm 2,3,5 --yes
    """
    try:
        # Handle wildcard: delete all projects
        if project_ids.strip() == "*":
            all_projects = service.list_projects()

            if not all_projects:
                console.print("[yellow]No projects to delete[/yellow]")
                raise typer.Exit(0)

            # Confirm deletion unless --yes
            if not yes and len(all_projects) > 0:
                console.print(f"[yellow]About to delete {len(all_projects)} project(s)[/yellow]")
                response = typer.confirm("Continue?", default=False)
                if not response:
                    console.print("[yellow]Cancelled[/yellow]")
                    raise typer.Exit(0)

            # Delete all projects
            deleted_projects = []
            errors = []

            for project in all_projects:
                try:
                    service.delete_project(project.id)
                    deleted_projects.append({"id": project.id, "name": project.name})
                except (ProjectNotFoundError, BarelyError) as e:
                    errors.append(f"Project {project.id}: {e}")

            # Display results
            if json_output:
                console.print(json.dumps(deleted_projects, indent=2))
            elif raw:
                for project in deleted_projects:
                    console.print(f"Deleted project {project['id']}: {project['name']}")
            else:
                console.print(f"[green]✓ Deleted {len(deleted_projects)} project(s)[/green]")
                if deleted_projects:
                    console.print("[dim]Tasks in these projects now have no project assigned[/dim]")
                if errors:
                    for error in errors:
                        error_console.print(f"[red]Error:[/red] {error}")

            raise typer.Exit(0 if not errors else 1)

        # Parse comma-separated IDs
        ids = [id.strip() for id in project_ids.split(",")]
        deleted_projects = []
        errors = []

        # Get all projects once for efficiency
        all_projects = service.list_projects()
        all_projects_dict = {p.id: p for p in all_projects}

        # Validate IDs first
        valid_ids = []
        for id_str in ids:
            try:
                project_id = int(id_str)
                if project_id not in all_projects_dict:
                    errors.append(f"Project {id_str} not found")
                else:
                    valid_ids.append(project_id)
            except ValueError:
                errors.append(f"Invalid project ID: {id_str}")

        if not valid_ids:
            for error in errors:
                error_console.print(f"[red]Error:[/red] {error}")
            raise typer.Exit(1)

        # Confirm deletion for multiple projects unless --yes
        if not yes and len(valid_ids) > 1:
            console.print(f"[yellow]About to delete {len(valid_ids)} project(s)[/yellow]")
            response = typer.confirm("Continue?", default=False)
            if not response:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        # Delete projects
        for project_id in valid_ids:
            try:
                project_to_delete = all_projects_dict[project_id]
                service.delete_project(project_id)
                deleted_projects.append({"id": project_id, "name": project_to_delete.name})
            except (ProjectNotFoundError, BarelyError) as e:
                errors.append(f"Error deleting project {project_id}: {e}")

        # Display results
        if json_output:
            console.print(json.dumps(deleted_projects, indent=2))
        elif raw:
            for project in deleted_projects:
                console.print(f"Deleted project {project['id']}: {project['name']}")
        else:
            for project in deleted_projects:
                console.print(f"[red]✗[/red] Deleted project {project['id']}: {project['name']}")
            if deleted_projects:
                console.print("[dim]Tasks in these projects now have no project assigned[/dim]")

        # Show errors if any
        if errors:
            for error in errors:
                error_console.print(f"[red]Error:[/red] {error}")
            if not deleted_projects:
                raise typer.Exit(1)

    except BarelyError as e:
        error_console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)

