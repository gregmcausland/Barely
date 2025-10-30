"""
FILE: barely/repl/style.py
PURPOSE: Simple celebration messages for REPL feedback
EXPORTS:
  - celebrate_done() -> str
  - celebrate_pull() -> str
  - celebrate_add() -> str
  - celebrate_delete() -> str
  - celebrate_bulk(count: int, action: str) -> str
  - format_relative(ts_iso: str) -> str
DEPENDENCIES:
  - random (for variety)
NOTES:
  - Simple string-based celebrations
  - Keeps the "barely" philosophy - subtle not overwhelming
"""

import random


# Celebration variants for task completion
DONE_CELEBRATIONS = [
    "✨ *sparkle* ✨",
    "🎉 *pop* 🎉",
    "⭐ *shine* ⭐",
    "💫 *twinkle* 💫",
    "🌟 *flash* 🌟",
]

# Pull animations (moving tasks between scopes)
PULL_ANIMATIONS = [
    "→ *whoosh* →",
    "⇢ *slide* ⇢",
    "↪ *flow* ↪",
    "➜ *shift* ➜",
]

# Add celebrations (new task created)
ADD_CELEBRATIONS = [
    "✓ *noted* ✓",
    "+ *added* +",
    "📝 *captured* 📝",
    "○ *logged* ○",
]

# Delete animations
DELETE_ANIMATIONS = [
    "💨 *poof* 💨",
    "× *removed* ×",
    "⊗ *cleared* ⊗",
    "∅ *gone* ∅",
]

# Bulk operation celebrations
BULK_CELEBRATIONS = [
    "🎯 *efficient* 🎯",
    "⚡ *zippy* ⚡",
    "🚀 *rapid* 🚀",
    "💪 *productive* 💪",
]


def celebrate_done() -> str:
    """
    Return a random celebration for completing a task.

    Returns:
        String with ASCII art celebration

    Example:
        "✨ *sparkle* ✨"
    """
    return random.choice(DONE_CELEBRATIONS)


def celebrate_pull() -> str:
    """
    Return a random animation for pulling tasks between scopes.

    Returns:
        String with ASCII art animation

    Example:
        "→ *whoosh* →"
    """
    return random.choice(PULL_ANIMATIONS)


def celebrate_add() -> str:
    """
    Return a random celebration for adding a task.

    Returns:
        String with ASCII art celebration

    Example:
        "✓ *noted* ✓"
    """
    return random.choice(ADD_CELEBRATIONS)


def celebrate_delete() -> str:
    """
    Return a random animation for deleting a task.

    Returns:
        String with ASCII art animation

    Example:
        "💨 *poof* 💨"
    """
    return random.choice(DELETE_ANIMATIONS)


def celebrate_bulk(count: int, action: str) -> str:
    """
    Return a celebration for bulk operations.

    Args:
        count: Number of items operated on
        action: Action performed (e.g., "completed", "deleted")

    Returns:
        String with ASCII art and message

    Example:
        "🎯 *efficient* 🎯 Completed 5 tasks!"
    """
    celebration = random.choice(BULK_CELEBRATIONS)
    return f"{celebration} {action.capitalize()} {count} tasks!"


def format_relative(ts_iso: str) -> str:
    """
    Format an ISO-8601 timestamp as a relative string.
    
    Uses the improved formatting module for better date handling.
    
    Examples:
        "just now", "2 hours ago", "yesterday", "Jan 15", "tomorrow"
    Fallbacks to the original string if parsing fails.
    """
    # Import here to avoid circular dependency
    from .formatting import format_relative_date
    return format_relative_date(ts_iso)
