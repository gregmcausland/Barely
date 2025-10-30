"""Extract REPL system handlers from main.py"""
import sys

# Read main.py
with open('barely/repl/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Extract system handlers (lines 1808-1984)
system_lines = lines[1807:1985]

header = '''"""
FILE: barely/repl/commands/system.py
PURPOSE: System command handlers for REPL
"""

from rich.panel import Panel

from ..main import console, repl_context
from ..parser import ParseResult
from .. import blitz
from .. import undo
from ...core import service

'''

with open('barely/repl/commands/system.py', 'w', encoding='utf-8') as f:
    f.write(header)
    for line in system_lines:
        # Skip imports we already have
        if 'from rich.panel import' in line:
            continue
        if 'from ..main import' in line:
            continue
        if 'from ..parser import' in line:
            continue
        if 'from .. import blitz' in line:
            continue
        if 'from .. import undo' in line:
            continue
        if 'from ...core import' in line:
            continue
        f.write(line)

print("Created system.py")

