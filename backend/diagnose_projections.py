# diagnose_projections.py (Version 3 - Corrected and Complete)
import pandas as pd
import requests
import logging
import io
import time

# --- Configuration ---
# Corrected and complete list based on league_config.json and standard positions.
POSITIONS = ["QB", "RB", "WR", "TE", "K", "DST"]
SCORING = "HALF"  # Based on your league_config.json

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def diagnose_position_url(position: str, scoring: str):
    """
    Fetches a URL for a given position and diagnoses the tables found.
    """
    # Note: Scoring parameter doesn't affect K or DST, but is harmless to include.
    url = f"https://www.fantasypros.com/nfl/projections/{position.lower()}.php?scoring={scoring.upper()}&week=0"

    logging.info(f"--- Diagnosing Position: {position.upper()} ---")
    logging.info(f"Attempting to fetch URL: {url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        logging.info(f"Successfully fetched {position.upper()}. Status Code: 200")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch URL for {position.upper()}. Error: {e}")
        return  # Stop processing this position on failure

    logging.info(f"Parsing HTML for tables for {position.upper()}...")
    try:
        all_tables = pd.read_html(io.StringIO(response.text))
        logging.info(
            f"SUCCESS: Found {len(all_tables)} tables on the {position.upper()} page."
        )

        print("\n" + "=" * 25)
        print(f"   EVIDENCE REPORT FOR: {position.upper()}")
        print("=" * 25 + "\n")

        for i, table_df in enumerate(all_tables):
            print(f"--- {position.upper()} - Table Index: {i} ---")
            print(f"Columns: {table_df.columns.values.tolist()}")
            print("First 2 rows of data:")
            # Using .to_string() ensures we see all columns without truncation.
            print(table_df.head(2).to_string())
            print("\n" + "-" * 20 + "\n")

    except ValueError:
        logging.error(
            f"CRITICAL ERROR: pandas could not find any tables on the page for {position.upper()}."
        )


if __name__ == "__main__":
    for pos in POSITIONS:
        diagnose_position_url(pos, SCORING)
        # Add a polite delay between requests to avoid being blocked.
        if pos != POSITIONS[-1]:
            logging.info(f"Waiting 1 second before fetching next position...")
            time.sleep(1)
