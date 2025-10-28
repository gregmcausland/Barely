"""
FILE: barely/repl/__init__.py
PURPOSE: REPL package for interactive task management
EXPORTS:
  - main() (from repl.main)
DEPENDENCIES:
  - prompt_toolkit (REPL interface)
  - rich (formatted output)
  - barely.core.service (business logic)
NOTES:
  - Entry point for interactive mode
  - Provides autocomplete and command history
"""

from .main import main

__all__ = ["main"]
