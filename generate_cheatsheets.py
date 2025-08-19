import pandas as pd
from pathlib import Path

# --- Configuration ---
# The name of your final, ranked JSON file.
INPUT_JSON_FILE = Path("public/champions.json")

# The threshold for creating a new tier. A larger number means fewer, bigger tiers.
# This value represents a drop-off in VOR points. A good starting point is 1.5-2.0.
VOR_TIER_DROP_THRESHOLD = 1.75

# The positions you want to generate tiered sheets for.
POSITIONS_TO_TIER = ["QB", "RB", "WR", "TE"]

# The directory where the cheat sheets will be saved.
OUTPUT_DIR = Path("cheatsheets")


def generate_cheatsheets():
    """
    Reads the final player rankings and generates printable CSV cheat sheets,
    including an overall big board and positional tiers.
    """
    print(f"--- Fantasy Football Cheat Sheet Generator ---")

    # 1. Load the Data
    if not INPUT_JSON_FILE.exists():
        print(
            f"ERROR: Input file not found! Make sure '{INPUT_JSON_FILE}' is in this directory."
        )
        return

    print(f"Loading data from '{INPUT_JSON_FILE}'...")
    df = pd.read_json(INPUT_JSON_FILE)

    # Ensure the output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"Output will be saved in the '{OUTPUT_DIR}/' directory.")

    # Define the columns we want in our cheat sheets for readability
    columns_to_keep = ["id", "name", "position", "team", "vor", "adp", "bye", "ppg"]

    # 2. Generate the Overall Big Board
    print("Generating Overall Big Board...")
    overall_df = df[columns_to_keep]
    overall_output_path = OUTPUT_DIR / "cheatsheet_overall.csv"
    overall_df.to_csv(overall_output_path, index=False)
    print(f" -> Saved to '{overall_output_path}'")

    # 3. Generate Positional Tier Sheets
    print("\nGenerating Positional Tiers...")
    for pos in POSITIONS_TO_TIER:
        print(f"  -> Processing {pos}s...")

        # Filter for the current position and sort by VOR
        pos_df = df[df["position"] == pos].sort_values(by="vor", ascending=False).copy()

        if pos_df.empty:
            print(f"     No players found for position {pos}. Skipping.")
            continue

        # Calculate the drop-off in VOR from the player above
        pos_df["vor_drop"] = pos_df["vor"].diff().abs()

        # A new tier starts where the drop-off exceeds our threshold
        # We use cumsum() to create incrementing tier numbers
        pos_df["Tier"] = (pos_df["vor_drop"] > VOR_TIER_DROP_THRESHOLD).cumsum() + 1

        # Select and reorder columns for the final sheet
        final_pos_df = pos_df[["Tier"] + columns_to_keep]

        # Save the tiered sheet to its own CSV file
        pos_output_path = OUTPUT_DIR / f"cheatsheet_{pos}.csv"
        final_pos_df.to_csv(pos_output_path, index=False)
        print(f"     Saved to '{pos_output_path}'")

    print("\n--- Generation Complete! ---")
    print(
        "You can now open the CSV files in the 'cheatsheets' directory with any spreadsheet program."
    )


if __name__ == "__main__":
    generate_cheatsheets()
