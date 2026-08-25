# Path: ffbPlayerDraftingApp/backend/utils.py

import json
import re
from typing import Any, TypeVar

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


def _load_alias_map() -> dict[str, str]:
    alias_map_path = settings.BASE_DIR / "player_alias_map.json"
    try:
        with open(alias_map_path, "r", encoding="utf-8") as f:
            alias_map = json.load(f)
        log.info(f"Loaded {len(alias_map)} aliases from {alias_map_path.name}")
        return alias_map
    except (FileNotFoundError, json.JSONDecodeError):
        log.warning(
            "player_alias_map.json not found or is invalid. Proceeding without aliases."
        )
        return {}


def _audit_row(
    *,
    canonical_slug: str,
    matched_source_slug: str = "",
    match_type: str,
    score: int | None = None,
    needs_review: bool = False,
    review_reason: str = "",
    alternatives: list[tuple[str, int]] | None = None,
) -> dict[str, Any]:
    return {
        "canonical_slug": canonical_slug,
        "matched_source_slug": matched_source_slug,
        "match_type": match_type,
        "score": score,
        "needs_review": needs_review,
        "review_reason": review_reason,
        "alternatives": [
            {"source_slug": source_slug, "score": alt_score}
            for source_slug, alt_score in (alternatives or [])
        ],
    }


def create_hybrid_slug_map(
    source_data: dict[str, V],
    canonical_slugs: list[str],
    score_cutoff: int = 85,
) -> dict[str, V]:
    final_map, _audit_rows = create_hybrid_slug_map_with_audit(
        source_data=source_data,
        canonical_slugs=canonical_slugs,
        score_cutoff=score_cutoff,
    )
    return final_map


def create_hybrid_slug_map_with_audit(
    source_data: dict[str, V],
    canonical_slugs: list[str],
    score_cutoff: int = 85,
    review_score_cutoff: int = 95,
) -> tuple[dict[str, V], list[dict[str, Any]]]:
    alias_map = _load_alias_map()
    final_map: dict[str, V] = {}
    audit_rows: list[dict[str, Any]] = []
    source_slugs_to_match = list(source_data.keys())
    canonical_set = set(canonical_slugs)

    mapped_source_slugs = set()
    for source_slug, value in source_data.items():
        if source_slug in canonical_set:
            final_map[source_slug] = value
            mapped_source_slugs.add(source_slug)
            audit_rows.append(
                _audit_row(
                    canonical_slug=source_slug,
                    matched_source_slug=source_slug,
                    match_type="direct",
                    score=100,
                )
            )
            continue
        if source_slug in alias_map:
            canonical_slug = alias_map[source_slug]
            if canonical_slug in canonical_set:
                final_map[canonical_slug] = value
                mapped_source_slugs.add(source_slug)
                audit_rows.append(
                    _audit_row(
                        canonical_slug=canonical_slug,
                        matched_source_slug=source_slug,
                        match_type="alias",
                        score=100,
                    )
                )

    log.info(f"Mapped {len(final_map)} players using direct matches and aliases.")

    unmatched_canonical = [slug for slug in canonical_slugs if slug not in final_map]
    remaining_source_slugs = [
        slug for slug in source_slugs_to_match if slug not in mapped_source_slugs
    ]

    if unmatched_canonical and remaining_source_slugs:
        log.info(
            f"Attempting to fuzzy match {len(unmatched_canonical)} remaining canonical slugs against {len(remaining_source_slugs)} source slugs."
        )

    fuzzy_match_count = 0
    for canon_slug in unmatched_canonical:
        if canon_slug in final_map:
            continue

        alternatives = process.extract(canon_slug, remaining_source_slugs, limit=3)
        match = alternatives[0] if alternatives and alternatives[0][1] >= score_cutoff else None
        if match:
            matched_source_slug, match_score = match[0], match[1]
            needs_review = match_score < review_score_cutoff
            audit_rows.append(
                _audit_row(
                    canonical_slug=canon_slug,
                    matched_source_slug=matched_source_slug,
                    match_type="fuzzy",
                    score=match_score,
                    needs_review=needs_review,
                    review_reason=(
                        f"Fuzzy score {match_score} is below review cutoff {review_score_cutoff}."
                        if needs_review
                        else ""
                    ),
                    alternatives=alternatives,
                )
            )

            log.info(
                "Fuzzy match found.",
                extra={
                    "canonical_slug": canon_slug,
                    "matched_source_slug": matched_source_slug,
                    "score": match_score,
                    "needs_review": needs_review,
                },
            )

            final_map[canon_slug] = source_data[matched_source_slug]
            remaining_source_slugs.remove(matched_source_slug)
            fuzzy_match_count += 1
        else:
            audit_rows.append(
                _audit_row(
                    canonical_slug=canon_slug,
                    match_type="unmatched_canonical",
                    needs_review=False,
                    review_reason="No source slug met the fuzzy score cutoff.",
                    alternatives=alternatives,
                )
            )

    for source_slug in remaining_source_slugs:
        audit_rows.append(
            _audit_row(
                canonical_slug="",
                matched_source_slug=source_slug,
                match_type="unmatched_source",
                needs_review=False,
                review_reason="Source slug was not mapped to any canonical player.",
            )
        )

    log.info(f"Found {fuzzy_match_count} fuzzy matches.")
    log.info(f"Total players mapped after fuzzy matching: {len(final_map)}")
    return final_map, audit_rows