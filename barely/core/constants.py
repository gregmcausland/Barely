"""
FILE: barely/core/constants.py
PURPOSE: Constants used throughout the application
EXPORTS:
  - VALID_SCOPES: All valid scope values
  - ACTIVE_SCOPES: Scopes for active (non-archived) tasks
  - DEFAULT_SCOPE: Default scope for new tasks
  - DEFAULT_COLUMN_ID: Default column ID for new tasks
DEPENDENCIES:
  - None (stdlib only)
NOTES:
  - Centralized constants to avoid magic strings
  - Single source of truth for scope values
"""

# Task scope constants
VALID_SCOPES = ("backlog", "week", "today", "archived")
ACTIVE_SCOPES = ("backlog", "week", "today")
DEFAULT_SCOPE = "backlog"
SCOPE_BACKLOG = "backlog"
SCOPE_WEEK = "week"
SCOPE_TODAY = "today"
SCOPE_ARCHIVED = "archived"

# Default values
DEFAULT_COLUMN_ID = 1

# Task status constants
STATUS_TODO = "todo"
STATUS_DONE = "done"

