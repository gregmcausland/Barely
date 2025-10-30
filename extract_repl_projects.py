"""Extract REPL project handlers from main.py"""
import sys

# Read main.py
with open('barely/repl/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Extract project handlers (lines 1546-1805)
project_lines = lines[1545:1806]

header = '''"""
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
from ..main import display_tasks_table

# Helper function
def ask_confirmation(message: str) -> bool:
    """Ask user for confirmation (y/n)."""
    response = input(f"{message} (y/n): ").strip().lower()
    return response in ('y', 'yes')

'''

with open('barely/repl/commands/projects.py', 'w', encoding='utf-8') as f:
    f.write(header)
    for line in project_lines:
        # Skip imports we already have
        if 'from ..core import' in line:
            continue
        if 'from ..parser import' in line:
            continue
        if 'from ..style import' in line:
            continue
        if 'from ..main import' in line:
            continue
        # Fix references
        line = line.replace('style.', '')
        f.write(line)

print("Created projects.py")

