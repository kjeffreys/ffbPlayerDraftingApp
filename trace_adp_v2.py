import sys
from pathlib import Path

# Add the project's backend directory to the Python path
# This allows us to import the fantasypros module directly
project_root = Path(__file__).resolve().parent
backend_path = project_root / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

try:
    # Now we can import the pipeline's own data source module
    from data_sources.fantasypros import fetch_adp, slugify
except ImportError as e:
    print(f"FATAL: Could not import the fantasypros module.")
    print(f"Please ensure this script is in the project root and the backend exists.")
    print(f"Error: {e}")
    sys.exit(1)


# --- Configuration ---
ANOMALOUS_ADP_VALUE = 63.5
PLAYER_OF_INTEREST_SLUG = "tim-jones"


def main():
    """Main diagnostic function to trace ADP data using the pipeline's own logic."""
    print("--- Running ADP Anomaly Diagnostic (v2) for BUG-002 ---")

    # Use the EXACT same function the pipeline uses to get the data
    adp_map = fetch_adp()

    if not adp_map:
        print("Could not proceed. The fetch_adp function returned no data.")
        return

    print("\n--- Analysis of Parsed ADP Data ---")

    # Find what the pipeline mapped for Tim Jones
    tim_jones_data = adp_map.get(PLAYER_OF_INTEREST_SLUG)

    # Find which player slug is associated with the anomalous ADP
    slug_with_anomalous_adp = None
    for slug, (adp, _) in adp_map.items():
        if abs(adp - ANOMALOUS_ADP_VALUE) < 0.01:
            slug_with_anomalous_adp = slug
            break

    print("\n--- DIAGNOSTIC REPORT ---")
    print(
        f"Searching for player '{PLAYER_OF_INTEREST_SLUG}' and ADP value '{ANOMALOUS_ADP_VALUE}'..."
    )
    print("-" * 20)

    # Report on Tim Jones
    if tim_jones_data:
        adp_val, bye_val = tim_jones_data
        print(f"EVIDENCE FOR '{PLAYER_OF_INTEREST_SLUG}':")
        print(
            f"  - The pipeline correctly parsed an ADP of {adp_val} and Bye of {bye_val}."
        )
    else:
        print(f"EVIDENCE FOR '{PLAYER_OF_INTEREST_SLUG}':")
        print(f"  - No ADP data was found for this slug in the parsed map.")

    print("-" * 20)

    # Report on the anomalous ADP
    if slug_with_anomalous_adp:
        adp_val, bye_val = adp_map[slug_with_anomalous_adp]
        print(f"EVIDENCE FOR ADP VALUE '{ANOMALOUS_ADP_VALUE}':")
        print(
            f"  - This ADP value is associated with the slug: '{slug_with_anomalous_adp}'."
        )
    else:
        print(f"EVIDENCE FOR ADP VALUE '{ANOMALOUS_ADP_VALUE}':")
        print(f"  - No player was found with this exact ADP value in the parsed map.")

    print("\nCONCLUSION:")
    if (
        tim_jones_data
        and slug_with_anomalous_adp
        and tim_jones_data[0] == ANOMALOUS_ADP_VALUE
    ):
        print(
            "  The data appears correct. Tim Jones' ADP is listed as 63.5 at the source."
        )
    elif slug_with_anomalous_adp and slug_with_anomalous_adp != PLAYER_OF_INTEREST_SLUG:
        print(
            f"  MISMATCH CONFIRMED. The ADP of {ANOMALOUS_ADP_VALUE} belongs to '{slug_with_anomalous_adp}',"
        )
        print(
            f"  but it was somehow mapped to '{PLAYER_OF_INTEREST_SLUG}' during the enrichment phase."
        )
        print(
            "  This points to a flaw in the `create_hybrid_slug_map` fuzzy matching logic."
        )
    else:
        print(
            "  The results are inconclusive. One of the search criteria was not found."
        )

    print("\n--- End of Report ---")


if __name__ == "__main__":
    main()
