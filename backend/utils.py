# backend/backend/utils.py
"""General utility functions."""

import re


def slugify(text: str) -> str:
    """
    Convert a string to a URL-friendly "slug".
    Example: "Patrick Mahomes II" -> "patrick-mahomes-ii"
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)  # Remove non-alphanumeric chars
    text = re.sub(r"[\s-]+", "-", text).strip(
        "-"
    )  # Replace space/hyphen with single hyphen
    return text
