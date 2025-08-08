import pandas as pd
import requests
import io

# --- This script is standalone and needs no special imports ---
print("--- Running Projections Page Diagnostic ---")
URL = "https://www.fantasypros.com/nfl/projections/all.php?scoring=HALF"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

try:
    response = requests.get(URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    print(f"Successfully fetched URL: {URL}")

    tables = pd.read_html(io.StringIO(response.text))

    print(f"\nDiscovered {len(tables)} tables on the page.")

    for i, df in enumerate(tables):
        print(f"\n--- Table {i} ---")
        print(f"  Shape: {df.shape}")
        print(f"  Columns: {df.columns.values.tolist()}")
        print("  First 5 Rows:")
        print(df.head().to_string())

except Exception as e:
    print(f"\nAn error occurred: {e}")

print("\n--- Diagnostic Complete ---")
