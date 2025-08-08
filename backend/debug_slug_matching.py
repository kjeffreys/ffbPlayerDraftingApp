import pandas as pd
from thefuzz import process
import sys

from .data_sources import historical
from .storage.file_store import load_json
from .settings import settings

print("--- Running Slug Matching Diagnostic ---")

# --- Step 1: Find the latest data directory ---
date_str = None
try:
    subdirs = [d for d in settings.DATA_DIR.iterdir() if d.is_dir()]
    if not subdirs:
        raise FileNotFoundError("No data subdirectories found in the data directory.")
    latest_subdir = sorted(subdirs)[-1]
    date_str = latest_subdir.name
    print(f"Found latest data directory: {date_str}")
except (FileNotFoundError, IndexError) as e:
    print(
        f"ERROR: Could not determine the latest data directory. Please run the pipeline first. Details: {e}"
    )
    sys.exit(1)

# --- Step 2: Load the source-of-truth players ---
try:
    # THE FIX IS HERE: Load from the file that contains the 'slug' column
    input_path = settings.DATA_DIR / date_str / "players_enriched.json"
    canonical_players = load_json(input_path)
    canonical_df = pd.DataFrame(canonical_players)

    # This will now work because 'slug' exists in players_enriched.json
    canonical_slugs = canonical_df["slug"].dropna().unique().tolist()
    print(f"Loaded {len(canonical_slugs)} canonical slugs from {input_path.name}.")
except Exception as e:
    print(
        f"ERROR: Could not load or parse {input_path.name}. Did you run the pipeline? Error: {e}"
    )
    sys.exit(1)

# --- Step 3: Fetch the historical data slugs ---
print("\nFetching historical data to get source slugs...")
hist_scores = historical.fetch_last_year_weekly_stats()
historical_slugs = list(hist_scores.keys())
print(f"Fetched {len(historical_slugs)} slugs from the historical data source.")


# --- Step 4: Perform the matching and generate a detailed report ---
print("\n--- Matching Report ---")
successful_matches = {}
unmatched_canonical = []
score_cutoff = 85

matched_historical_slugs = set()

for canon_slug in sorted(canonical_slugs):
    match = process.extractOne(canon_slug, historical_slugs, score_cutoff=score_cutoff)

    if match:
        hist_slug = match[0]
        if hist_slug in successful_matches.values():
            print(
                f"  [WARNING] Duplicate match for '{hist_slug}'! Already matched. Current attempt: '{canon_slug}'."
            )
        else:
            successful_matches[canon_slug] = hist_slug
            matched_historical_slugs.add(hist_slug)
    else:
        unmatched_canonical.append(canon_slug)

# --- Step 5: Print the results ---
print(
    f"\n--- SUCCESSFUL MATCHES ({len(successful_matches)}/{len(canonical_slugs)}) ---"
)
for i, (c_slug, h_slug) in enumerate(successful_matches.items()):
    if i < 20:
        print(f"  Canonical: '{c_slug}'  =>  Historical: '{h_slug}'")
if len(successful_matches) > 20:
    print("  ...")

print(f"\n--- UNMATCHED CANONICAL SLUGS ({len(unmatched_canonical)}) ---")
important_unmatched = [
    s
    for s in unmatched_canonical
    if s in ["jamarr-chase", "josh-allen", "amon-ra-st-brown"]
]
if important_unmatched:
    print("  IMPORTANT FAILURES:")
    for slug in important_unmatched:
        print(f"    - {slug}")

print("\n  Other unmatched canonical slugs (sample):")
for i, slug in enumerate(unmatched_canonical):
    if i < 20:
        print(f"    - {slug}")
if len(unmatched_canonical) > 20:
    print("    ...")

unmatched_historical = [
    slug for slug in historical_slugs if slug not in matched_historical_slugs
]
print(f"\n--- UNMATCHED HISTORICAL SLUGS ({len(unmatched_historical)}) ---")
for i, slug in enumerate(unmatched_historical):
    if i < 20:
        print(f"    - {slug}")
if len(unmatched_historical) > 20:
    print("    ...")

print("\n--- Diagnostic Complete ---")
