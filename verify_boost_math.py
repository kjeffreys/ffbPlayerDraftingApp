import json
from pathlib import Path
import sys

# --- Configuration ---
LEAGUE_CONFIG_FILE = Path("backend/league_config.json")
PLAYER_BOOST_FILE = Path("backend/player_boost.json")
PLAYERS_WITH_PPG_FILE = Path("backend/data/2025-08-16/players_with_ppg.json")

# Slugs for players we want to specifically audit
TEST_SLUGS = [
    "christian-mccaffrey",  # max boost
    "jamarr-chase",  # large boost
    "ceedee-lamb",  # medium boost
    "ashton-jeanty",  # small boost
    "saquon-barkley",  # no boost (control)
]


def load_json_artifact(filepath: Path) -> dict | list:
    """Helper to load a JSON file with error handling."""
    if not filepath.exists():
        print(f"FATAL: Required file not found at '{filepath}'", file=sys.stderr)
        sys.exit(1)
    with open(filepath, "r") as f:
        return json.load(f)


def get_player_data_by_slug(players: list[dict], slug: str) -> dict | None:
    """Finds a player's data dictionary from the list by their slug."""
    for player in players:
        if player.get("slug") == slug:
            return player
    return None


def main():
    print("--- Running Boost Calculation Verification Diagnostic ---")

    # --- Load all necessary data ---
    league_config = load_json_artifact(LEAGUE_CONFIG_FILE)
    player_boosts = load_json_artifact(PLAYER_BOOST_FILE)
    players_data = load_json_artifact(PLAYERS_WITH_PPG_FILE)

    # --- Prepare data for easy lookup ---
    # Map slugs to boost tier names
    intended_boosts = {}
    for tier_key, slugs in player_boosts.items():
        tier_name = tier_key.replace("_boost_slugs", "")
        for slug in slugs:
            intended_boosts[slug] = tier_name

    # Get weights and boost percentages from config
    w_hist = league_config.get("weight_last_year", 0.5)
    w_proj = league_config.get("weight_projection", 0.5)
    boost_values = {
        "small": league_config.get("boost_small", 0),
        "medium": league_config.get("boost_medium", 0),
        "large": league_config.get("boost_large", 0),
        "max": league_config.get("boost_max", 0),
    }

    print("\n--- Auditing Player Calculations ---\n")

    all_tests_passed = True
    for slug in TEST_SLUGS:
        print(f"--- Verifying '{slug}' ---")
        player = get_player_data_by_slug(players_data, slug)
        if not player:
            print(
                f"  ERROR: Could not find player data for '{slug}' in players_with_ppg.json"
            )
            all_tests_passed = False
            continue

        # --- Get player's base scores and final score ---
        scaled_hist = (
            player.get("scaled_hist") or 0.0
        )  # Handle NaN/nulls by treating as 0
        scaled_proj = player.get("scaled_proj") or 0.0
        actual_final_ppg = player.get("expected_ppg")

        # --- Calculate pre-boost score ---
        pre_boost_score = (scaled_hist * w_hist) + (scaled_proj * w_proj)

        # --- Determine and apply boost ---
        boost_tier = intended_boosts.get(slug, "none")
        boost_percent = boost_values.get(boost_tier, 0)

        expected_final_ppg = pre_boost_score * (1 + boost_percent)

        # --- Compare and report ---
        print(f"  Boost Tier (from JSON): '{boost_tier.upper()}'")
        print(f"  Boost Percentage (from config): {boost_percent:.2%}")
        print(f"  Pre-Boost Blended Score: {pre_boost_score:.4f}")
        print(f"  EXPECTED Final PPG (calculated): {expected_final_ppg:.4f}")
        print(f"  ACTUAL Final PPG (from file):   {actual_final_ppg:.4f}")

        if abs(expected_final_ppg - actual_final_ppg) < 0.001:
            print("  STATUS: MATCH ✔️\n")
        else:
            print("  STATUS: MISMATCH ❌\n")
            all_tests_passed = False

    print("--- End of Audit ---")
    if all_tests_passed:
        print(
            "\nCONCLUSION: All tested calculations are correct. The boost logic is working as expected."
        )
    else:
        print(
            "\nCONCLUSION: One or more boost calculations are incorrect. See mismatches above."
        )


if __name__ == "__main__":
    main()
