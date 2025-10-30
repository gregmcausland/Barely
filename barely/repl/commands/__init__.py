"""
FILE: barely/repl/commands/__init__.py
PURPOSE: REPL command handler modules
"""

# Export all command handlers for easy importing
from .tasks import (
    handle_add_command,
    handle_ls_command,
    handle_done_command,
    handle_rm_command,
    handle_edit_command,
    handle_desc_command,
    handle_show_command,
    handle_mv_command,
    handle_assign_command,
)
from .workflow import (
    handle_today_command,
    handle_week_command,
    handle_backlog_command,
    handle_archive_command,
    handle_pull_command,
)
from .projects import (
    handle_use_command,
    handle_project_add_command,
    handle_project_ls_command,
    handle_project_rm_command,
    handle_project_command,
)
from .system import (
    handle_help_command,
    handle_clear_command,
    handle_blitz_command,
    handle_undo_command,
    handle_scope_command,
)

__all__ = [
    "handle_add_command",
    "handle_ls_command",
    "handle_done_command",
    "handle_rm_command",
    "handle_edit_command",
    "handle_desc_command",
    "handle_show_command",
    "handle_mv_command",
    "handle_assign_command",
    "handle_today_command",
    "handle_week_command",
    "handle_backlog_command",
    "handle_archive_command",
    "handle_pull_command",
    "handle_use_command",
    "handle_project_add_command",
    "handle_project_ls_command",
    "handle_project_rm_command",
    "handle_project_command",
    "handle_help_command",
    "handle_clear_command",
    "handle_blitz_command",
    "handle_undo_command",
    "handle_scope_command",
]

