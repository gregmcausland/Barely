"""Extract REPL workflow handlers from main.py"""
import sys

# Read main.py
with open('barely/repl/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Extract workflow handlers (lines 1268-1544)
workflow_lines = lines[1267:1545]

header = '''"""
FILE: barely/repl/commands/workflow.py
PURPOSE: Workflow command handlers for REPL
"""

from ..main import console, repl_context
from ..parser import ParseResult
from ...core import service
from ...core.exceptions import (
    BarelyError,
    TaskNotFoundError,
    InvalidInputError,
)
from ..style import celebrate_pull, celebrate_bulk
from ..undo import record_pull
from ..main import display_tasks_table
from ..pickers import pick_task

# Helper function
def ask_confirmation(message: str) -> bool:
    """Ask user for confirmation (y/n)."""
    response = input(f"{message} (y/n): ").strip().lower()
    return response in ('y', 'yes')

'''

with open('barely/repl/commands/workflow.py', 'w', encoding='utf-8') as f:
    f.write(header)
    for line in workflow_lines:
        # Skip imports we already have
        if 'from ..core import' in line:
            continue
        if 'from ..parser import' in line:
            continue
        if 'from ..style import' in line:
            continue
        if 'from ..undo import' in line:
            continue
        if 'from ..main import' in line:
            continue
        if 'from ..pickers import' in line or 'from .pickers import' in line:
            continue
        # Fix references
        line = line.replace('undo.', '')
        line = line.replace('style.', '')
        f.write(line)

print("Created workflow.py")

