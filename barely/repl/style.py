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
from datetime import datetime, timezone


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


def _parse_iso(ts_iso: str) -> datetime | None:
    """Parse ISO-8601 timestamp to timezone-aware datetime (UTC)."""
    if not ts_iso:
        return None
    try:
        # Handle naive or aware inputs
        dt = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def format_relative(ts_iso: str) -> str:
    """
    Format an ISO-8601 timestamp as a relative string.

    Examples:
        "2 minutes ago", "3 hours ago", "yesterday", "in 5 minutes"
    Fallbacks to the original string if parsing fails.
    """
    dt = _parse_iso(ts_iso)
    if not dt:
        return ts_iso or ""

    now = datetime.now(timezone.utc)
    delta = dt - now
    seconds = int(delta.total_seconds())
    past = seconds < 0
    seconds = abs(seconds)

    def unit(n, name):
        return f"{n} {name}{'' if n == 1 else 's'}"

    if seconds < 60:
        text = unit(seconds, "second")
    elif seconds < 3600:
        text = unit(seconds // 60, "minute")
    elif seconds < 86400:
        text = unit(seconds // 3600, "hour")
    elif seconds < 172800:
        text = "yesterday" if past else "tomorrow"
        return text
    else:
        text = unit(seconds // 86400, "day")

    return f"{text} ago" if past else f"in {text}"
