# Path: ffbPlayerDraftingApp/backend/utils.py

import re
import json
from typing import TypeVar
from thefuzz import process

from .settings import settings
from .logging_config import log

V = TypeVar("V")


def slugify(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text


def create_hybrid_slug_map(
    source_data: dict[str, V],
    canonical_slugs: list[str],
    score_cutoff: int = 85,
) -> dict[str, V]:
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
        if source_slug in canonical_set:
            final_map[source_slug] = value
            mapped_source_slugs.add(source_slug)
            continue
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

    # --- FIX: ADDED ENHANCED LOGGING FOR FUZZY MATCHES ---
    fuzzy_match_count = 0
    for canon_slug in unmatched_canonical:
        if canon_slug in final_map:
            continue

        match = process.extractOne(
            canon_slug, remaining_source_slugs, score_cutoff=score_cutoff
        )
        if match:
            matched_source_slug, match_score = match[0], match[1]

            # Log the specific match and its confidence score
            log.info(
                "Fuzzy match found.",
                extra={
                    "canonical_slug": canon_slug,
                    "matched_source_slug": matched_source_slug,
                    "score": match_score,
                },
            )

            final_map[canon_slug] = source_data[matched_source_slug]
            remaining_source_slugs.remove(matched_source_slug)
            fuzzy_match_count += 1

    log.info(f"Found {fuzzy_match_count} fuzzy matches.")
    # --- END OF FIX ---

    log.info(f"Total players mapped after fuzzy matching: {len(final_map)}")
    return final_map
