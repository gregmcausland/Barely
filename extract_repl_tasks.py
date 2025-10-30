"""Extract REPL task handlers from main.py"""
import sys

# Read main.py
with open('barely/repl/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Extract task handlers (lines 422-1262)
task_lines = lines[421:1262]

header = '''"""
FILE: barely/repl/commands/tasks.py
PURPOSE: Task command handlers for REPL
"""

from typing import Optional, List

from ..main import console, repl_context
from ..parser import ParseResult
from ...core import service, repository
from ...core.exceptions import (
    BarelyError,
    TaskNotFoundError,
    ProjectNotFoundError,
    ColumnNotFoundError,
    InvalidInputError,
)
from ...utils import improve_title_with_ai
from ..style import celebrate_add, celebrate_done, celebrate_delete, celebrate_bulk
from ..undo import record_create, record_complete, record_delete, record_update_title
from ..pickers import pick_task
from ..formatting import display_task, display_tasks_table

# Helper function
def ask_confirmation(message: str) -> bool:
    """Ask user for confirmation (y/n)."""
    response = input(f"{message} (y/n): ").strip().lower()
    return response in ('y', 'yes')

'''

with open('barely/repl/commands/tasks.py', 'w', encoding='utf-8') as f:
    f.write(header)
    # Fix imports
    for line in task_lines:
        # Remove the function definition if it's ask_confirmation (we'll add it to header)
        if line.strip().startswith('def ask_confirmation'):
            # Skip the function definition and its docstring
            continue
        # Fix imports
        if 'from ..core import' in line:
            continue  # Already in header
        if 'from ..parser import' in line:
            continue  # Already in header
        if 'from ..style import' in line:
            continue  # Already in header
        if 'from ..undo import' in line:
            continue  # Already in header
        if 'from ..pickers import' in line or 'from .pickers import' in line:
            continue  # Already in header
        if 'from ..formatting import' in line or 'from .formatting import' in line:
            continue  # Already in header
        f.write(line)

print("Created tasks.py")

