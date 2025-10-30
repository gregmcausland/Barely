"""
FILE: barely/cli/commands/__init__.py
PURPOSE: CLI command modules
"""

# Export all command handlers for easy importing
from .tasks import (
    add,
    ls,
    done,
    rm,
    edit,
    desc,
    show,
    mv,
    assign,
)
from .workflow import (
    today,
    week,
    backlog,
    archive,
    pull,
)
from .projects import (
    project_add,
    project_ls,
    project_rm,
)
from .system import (
    version,
    help,
    repl,
    blitz,
)

__all__ = [
    "add",
    "ls",
    "done",
    "rm",
    "edit",
    "desc",
    "show",
    "mv",
    "assign",
    "today",
    "week",
    "backlog",
    "archive",
    "pull",
    "project_add",
    "project_ls",
    "project_rm",
    "version",
    "help",
    "repl",
    "blitz",
]

