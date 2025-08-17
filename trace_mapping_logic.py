import re
import json
from pathlib import Path
import sys
from thefuzz import process

# --- Setup: Add backend to path to import modules ---
project_root = Path(__file__).resolve().parent
backend_path = project_root / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

try:
    from data_sources.fantasypros import fetch_adp
    from settings import settings
except ImportError as e:
    print("FATAL: Could not import necessary project modules.")
    sys.exit(1)

# --- Configuration for this specific diagnostic ---
PLAYERS_TO_TRACE = ["patrick-mahomes", "aaron-jones", "tim-jones"]


def diagnostic_slug_map_tracer(source_data: dict, canonical_slugs: list[str]) -> None:
    """
    A modified version of create_hybrid_slug_map with extensive print statements
    to trace the exact logic flow for our players of interest.
    """
    print("\n--- Starting Diagnostic Trace of Mapping Logic ---")

    alias_map_path = settings.BASE_DIR / "player_alias_map.json"
    try:
        with open(alias_map_path, "r") as f:
            alias_map = json.load(f)
        print(f"\n[TRACE] Loaded {len(alias_map)} aliases.")
    except (FileNotFoundError, json.JSONDecodeError):
        alias_map = {}
        print("\n[TRACE] No alias map found or it is invalid.")

    final_map = {}
    source_slugs_to_match = list(source_data.keys())
    canonical_set = set(canonical_slugs)

    print("\n--- Step 1: Direct and Alias Matching ---")
    for source_slug, value in source_data.items():
        # Only print details for the players we are tracing
        is_relevant = any(p in source_slug for p in PLAYERS_TO_TRACE)

        # A) Perfect match check
        if source_slug in canonical_set:
            if is_relevant:
                print(f"[TRACE] Found DIRECT match for '{source_slug}'. Mapping it.")
            final_map[source_slug] = value
            continue

        # B) Alias match check
        if source_slug in alias_map:
            canonical_target = alias_map[source_slug]
            if is_relevant:
                print(
                    f"[TRACE] Source slug '{source_slug}' is a KEY in alias_map. It maps to '{canonical_target}'."
                )
            if canonical_target in canonical_set:
                final_map[canonical_target] = value
                if is_relevant:
                    print(
                        f"  └── SUCCESS: Mapped source '{source_slug}' to canonical '{canonical_target}'."
                    )
            continue

        # C) REVERSE ALIAS CHECK - This might be the missing logic
        if source_slug in alias_map.values():
            # Find which canonical key maps to this source value
            for canon_key, source_val in alias_map.items():
                if source_val == source_slug and canon_key in PLAYERS_TO_TRACE:
                    print(
                        f"[TRACE] Source slug '{source_slug}' is a VALUE in alias_map for key '{canon_key}'."
                    )
                    if canon_key in canonical_set:
                        final_map[canon_key] = value
                        print(
                            f"  └── SUCCESS: Mapped source '{source_slug}' via REVERSE lookup to canonical '{canon_key}'."
                        )

    print(f"\n[INFO] After direct/alias matching, mapped {len(final_map)} players.")
    for slug in PLAYERS_TO_TRACE:
        if slug in final_map:
            print(f"  - '{slug}' was successfully mapped at this stage.")
        else:
            print(
                f"  - '{slug}' was NOT mapped at this stage. Will proceed to fuzzy matching."
            )

    # The fuzzy matching part is omitted as the error almost certainly lies in the logic above.


def main():
    print("--- Running Mapping Logic Diagnostic ---")
    print(f"This script will trace the mapping for: {', '.join(PLAYERS_TO_TRACE)}")

    # 1. Get the real source data
    source_adp_data = fetch_adp()
    if not source_adp_data:
        print("Could not fetch source ADP data. Aborting.")
        return

    # 2. Define our canonical player list
    # We will use a small list including our targets
    canonical_player_slugs = [
        "patrick-mahomes",
        "aaron-jones",
        "tim-jones",
        "bijan-robinson",
        "justin-jefferson",
    ]

    # 3. Run the tracer function
    diagnostic_slug_map_tracer(source_adp_data, canonical_player_slugs)

    print("\n--- Diagnostic Complete ---")


if __name__ == "__main__":
    main()
