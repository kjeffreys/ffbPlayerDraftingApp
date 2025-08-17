import json
import re
from pathlib import Path
import ast  # To safely evaluate list strings from the log
from collections import defaultdict

# --- Configuration: File Paths ---
# These paths assume the script is run from the project root directory.
PLAYER_BOOST_FILE = Path("backend/player_boost.json")
LOG_FILE = Path("report.log")


def get_intended_boosts(filepath: Path) -> dict[str, str]:
    """
    Loads the player_boost.json file and returns a dictionary mapping
    each player slug to its intended boost tier name (e.g., 'max', 'large').
    """
    if not filepath.exists():
        print(f"ERROR: Intended boosts file not found at '{filepath}'")
        return {}

    with open(filepath, "r") as f:
        data = json.load(f)

    intended_map = {}
    for boost_tier, slugs in data.items():
        # e.g., 'max_boost_slugs' -> 'max'
        tier_name = boost_tier.replace("_boost_slugs", "")
        for slug in slugs:
            intended_map[slug] = tier_name

    return intended_map


def get_actual_boosts_from_log(filepath: Path) -> dict[str, str]:
    """
    Parses the report.log file using the corrected log format,
    returning a dictionary mapping the player slug to the applied boost tier.
    """
    if not filepath.exists():
        print(f"ERROR: Log file not found at '{filepath}'")
        return {}

    # Regex for the actual log format: "'<tier>' boosted players: ['<slug1>', ...]"
    boost_pattern = re.compile(r"'(\w+)' boosted players: (\[.*\])")

    actual_map = {}
    with open(filepath, "r") as f:
        for line in f:
            match = boost_pattern.search(line)
            if match:
                boost_type, slugs_str = match.groups()
                try:
                    # Safely evaluate the string representation of the list
                    slugs_list = ast.literal_eval(slugs_str)
                    if isinstance(slugs_list, list):
                        for slug in slugs_list:
                            actual_map[slug] = boost_type
                except (ValueError, SyntaxError) as e:
                    print(
                        f"WARNING: Could not parse slug list from log line: {line.strip()}"
                    )
                    print(f"         Error: {e}")

    return actual_map


def main():
    """Main diagnostic function."""
    print("--- Running Player Boost Verification Diagnostic (v2) ---")

    intended = get_intended_boosts(PLAYER_BOOST_FILE)
    actual = get_actual_boosts_from_log(LOG_FILE)

    if not intended:
        print(
            "Could not proceed: No intended boosts were loaded from player_boost.json."
        )
        return
    if not actual:
        print(
            "Could not proceed: No actual boosts were found in the log with the expected format."
        )
        return

    intended_slugs = set(intended.keys())
    actual_slugs = set(actual.keys())

    # --- Analysis ---
    successfully_applied = intended_slugs.intersection(actual_slugs)
    missed_in_log = intended_slugs.difference(actual_slugs)
    unexpected_in_log = actual_slugs.difference(intended_slugs)

    mismatched_levels = []
    for slug in successfully_applied:
        if intended[slug] != actual[slug]:
            mismatched_levels.append(
                f"  - {slug}: INTENDED '{intended[slug]}', but LOGGED '{actual[slug]}'"
            )

    # --- Reporting ---
    print("\n--- DIAGNOSTIC REPORT ---")
    print(f"\n[SUMMARY]")
    print(f"  - Intended Boosts (from JSON): {len(intended_slugs)}")
    print(f"  - Actual Boosts (found in log): {len(actual_slugs)}")
    print(f"  - Successfully Matched: {len(successfully_applied)}")
    print(f"  - Mismatched Boost Levels: {len(mismatched_levels)}")
    print(f"  - Missed (in JSON, not in log): {len(missed_in_log)}")
    print(f"  - Unexpected (in log, not in JSON): {len(unexpected_in_log)}")

    print("\n[DETAILS: MISMATCHED BOOST LEVELS]")
    if mismatched_levels:
        for item in mismatched_levels:
            print(item)
    else:
        print("  None. All applied boosts had the correct level.")

    print("\n[DETAILS: MISSED BOOSTS (Configured in JSON but not found in log)]")
    if missed_in_log:
        for slug in sorted(list(missed_in_log)):
            print(f"  - {slug} (Was configured for '{intended[slug]}' boost)")
    else:
        print("  None. All players in player_boost.json were found in the log.")

    print("\n[DETAILS: UNEXPECTED BOOSTS (Found in log but not configured in JSON)]")
    if unexpected_in_log:
        for slug in sorted(list(unexpected_in_log)):
            print(f"  - {slug} (Log reports a '{actual[slug]}' boost)")
    else:
        print("  None. No unexpected player boosts were found in the log.")

    print("\n--- End of Report ---")


if __name__ == "__main__":
    main()
