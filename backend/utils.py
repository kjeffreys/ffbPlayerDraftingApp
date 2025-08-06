# Path: ffbPlayerDraftingApp/backend/utils.py

"""General utility functions."""

import re


def slugify(text: str) -> str:
    """
    Convert a string to a URL-friendly "slug".
    This is used to create consistent keys for players from different data sources.

    Example: "Patrick Mahomes II" -> "patrick-mahomes-ii"

    Args:
        text: The input string (e.g., a player's full name).

    Returns:
        A slugified version of the string.
    """
    if not isinstance(text, str):
        return ""
    # 1. Convert to lowercase
    text = text.lower()
    # 2. Remove any characters that aren't letters, numbers, spaces, or hyphens
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    # 3. Replace sequences of spaces or hyphens with a single hyphen
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text
