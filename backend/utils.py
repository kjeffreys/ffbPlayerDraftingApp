# Path: ffbPlayerDraftingApp/backend/utils.py

"""General utility functions."""

import re
import json
from typing import TypeVar
from thefuzz import process

# These imports need to be relative for the script to be used as a module
from .settings import settings
from .logging_config import log

# Generic TypeVar for dictionary values, allowing this function to work with
# different types of data (e.g., dict[str, tuple] or dict[str, list[float]])
V = TypeVar("V")


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


def create_hybrid_slug_map(
    source_data: dict[str, V],
    canonical_slugs: list[str],
    score_cutoff: int = 85,
) -> dict[str, V]:
    """
    Creates a mapping from canonical slugs to data from a source dictionary.

    This is a hybrid approach that prioritizes a manual alias map for known
    problematic slugs and falls back to fuzzy matching for the rest.

    Args:
        source_data: The dictionary with potentially "dirty" slugs as keys.
        canonical_slugs: A list of the "clean" slugs that are our target.
        score_cutoff: The confidence score required for a fuzzy match.

    Returns:
        A dictionary mapping clean, canonical slugs to their corresponding
        values from the source_data.
    """
    # Load the manual alias map
    alias_map_path = settings.BASE_DIR / "player_alias_map.json"
    try:
        with open(alias_map_path, "r") as f:
            alias_map = json.load(f)
        log.info(f"Loaded {len(alias_map)} aliases from {alias_map_path.name}")
    except (FileNotFoundError, json.JSONDecodeError):
        log.warning(
            "player_alias_map.json not found or is invalid. Proceeding without aliases."
        )
        alias_map = {}

    final_map: dict[str, V] = {}
    source_slugs_to_match = list(source_data.keys())
    canonical_set = set(canonical_slugs)

    # --- Step 1: Direct and Alias Matching ---
    mapped_source_slugs = set()

    for source_slug, value in source_data.items():
        # A) Perfect match: The source slug is one of our canonical slugs
        if source_slug in canonical_set:
            final_map[source_slug] = value
            mapped_source_slugs.add(source_slug)
            continue
        # B) Alias match: The source slug is in our manual alias file
        if source_slug in alias_map:
            canonical_slug = alias_map[source_slug]
            if canonical_slug in canonical_set:
                final_map[canonical_slug] = value
                mapped_source_slugs.add(source_slug)

    log.info(f"Mapped {len(final_map)} players using direct matches and aliases.")

    # --- Step 2: Fuzzy Matching for the Remainder ---
    unmatched_canonical = [slug for slug in canonical_slugs if slug not in final_map]
    remaining_source_slugs = [
        slug for slug in source_slugs_to_match if slug not in mapped_source_slugs
    ]

    if not unmatched_canonical or not remaining_source_slugs:
        log.info("No remaining players to fuzzy match.")
        return final_map

    log.info(
        f"Attempting to fuzzy match {len(unmatched_canonical)} remaining canonical slugs against {len(remaining_source_slugs)} source slugs."
    )

    for canon_slug in unmatched_canonical:
        # Prevent trying to match a slug that's already been successfully mapped
        if canon_slug in final_map:
            continue

        match = process.extractOne(
            canon_slug, remaining_source_slugs, score_cutoff=score_cutoff
        )
        if match:
            matched_source_slug = match[0]
            final_map[canon_slug] = source_data[matched_source_slug]
            # Important: Remove the matched source slug so it can't be used again
            remaining_source_slugs.remove(matched_source_slug)

    log.info(f"Total players mapped after fuzzy matching: {len(final_map)}")
    return final_map
