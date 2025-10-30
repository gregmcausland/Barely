"""
FILE: barely/repl/formatting.py
PURPOSE: Date formatting utilities for human-readable relative dates
EXPORTS:
  - format_relative_date(iso_string: str) -> str
DEPENDENCIES:
  - datetime (stdlib)
  - typing (type hints)
NOTES:
  - Converts ISO timestamp strings to relative time ("2 hours ago", "tomorrow")
  - Handles past, present, and future dates
  - Falls back to formatted date for very old dates
"""

from datetime import datetime
from typing import Optional


def format_relative_date(iso_string: Optional[str]) -> str:
    """
    Convert ISO timestamp string to human-readable relative time.

    Args:
        iso_string: ISO format timestamp string (e.g., "2025-01-26T14:30:00")
                    or None for empty/missing dates

    Returns:
        Human-readable relative time string:
        - "just now" (< 1 minute ago)
        - "2 minutes ago" (< 1 hour ago)
        - "3 hours ago" (< 24 hours ago)
        - "today" (same day)
        - "yesterday" (previous day)
        - "2 days ago" (< 1 week ago)
        - "Jan 15" (< 1 year ago, same year)
        - "Jan 15, 2024" (older than 1 year or different year)

    Examples:
        >>> format_relative_date("2025-01-26T14:30:00")
        "2 hours ago"  # assuming current time is 16:30
        >>> format_relative_date("2025-01-27T10:00:00")
        "tomorrow"
        >>> format_relative_date(None)
        "-"
    """
    if not iso_string:
        return "-"

    try:
        # Parse ISO timestamp
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        # If parsing fails, return original string
        return iso_string

    # Get current time
    now = datetime.now()

    # Handle timezone-naive comparisons (assume same timezone)
    if dt.tzinfo is None and now.tzinfo is None:
        delta = now - dt
    elif dt.tzinfo is None:
        # If dt is naive and now is aware, make dt aware using local timezone
        from datetime import timezone
        dt = dt.replace(tzinfo=timezone.utc)
        delta = now - dt
    elif now.tzinfo is None:
        # If now is naive and dt is aware, make now aware
        from datetime import timezone
        now = now.replace(tzinfo=timezone.utc)
        delta = now - dt
    else:
        delta = now - dt

    # Future dates
    if delta.total_seconds() < 0:
        abs_delta = abs(delta)
        hours = abs_delta.total_seconds() / 3600

        if hours < 24:
            if hours < 1:
                minutes = abs_delta.total_seconds() / 60
                if minutes < 1:
                    return "in a moment"
                return f"in {int(minutes)} minute{'s' if int(minutes) != 1 else ''}"
            return f"in {int(hours)} hour{'s' if int(hours) != 1 else ''}"
        elif hours < 48:
            return "tomorrow"
        else:
            days = int(abs_delta.total_seconds() / 86400)
            if days < 7:
                return f"in {days} days"
            else:
                # Format as date
                return dt.strftime("%b %d")

    # Past dates
    seconds = delta.total_seconds()

    # Less than 1 minute
    if seconds < 60:
        return "just now"

    # Less than 1 hour
    if seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"

    # Less than 24 hours
    if seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

    # Same day (more than 24 hours but same calendar day)
    if dt.date() == now.date():
        return "today"

    # Yesterday
    from datetime import timedelta
    yesterday = now.date() - timedelta(days=1)
    if dt.date() == yesterday:
        return "yesterday"

    # Less than 7 days
    days = int(seconds / 86400)
    if days < 7:
        return f"{days} day{'s' if days != 1 else ''} ago"

    # Less than 1 year (same year)
    if dt.year == now.year:
        return dt.strftime("%b %d")

    # Older than 1 year or different year
    return dt.strftime("%b %d, %Y")

