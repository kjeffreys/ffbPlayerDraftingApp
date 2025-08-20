import json
from pathlib import Path

# --- Configuration ---
# This path is confirmed by both the settings.py file and the log output.
CONFIG_PATH = Path(__file__).resolve().parent / "backend" / "league_config.json"


def main():
    """
    Reads the raw text of the config file, prints it for verification,
    and then attempts to parse it to reproduce the error.
    """
    print("--- Running Configuration Load Diagnostic ---")

    if not CONFIG_PATH.exists():
        print(f"ERROR: Configuration file not found at the expected path.")
        print(f"Path: {CONFIG_PATH}")
        return

    print(f"Reading raw text from: {CONFIG_PATH}\n")

    try:
        # 1. Read the raw, unmodified text content of the file
        raw_text = CONFIG_PATH.read_text(encoding="utf-8")

        # 2. Print the raw content as our ground truth
        print("--- START OF RAW FILE CONTENT ---")
        print(raw_text)
        print("--- END OF RAW FILE CONTENT ---\n")

        # 3. Attempt to parse the text
        print("Attempting to parse the content with json.loads()...")
        data = json.loads(raw_text)

        # 4. Report the type of the parsed data
        print(f"Successfully parsed JSON. The data type is: {type(data)}")

        if isinstance(data, dict):
            print(
                "CONCLUSION: The file contains a valid dictionary (mapping). The error must be elsewhere."
            )
        elif isinstance(data, list):
            print(
                "CONCLUSION: CONFIRMED. The file contains a list, which causes the TypeError."
            )

    except json.JSONDecodeError as e:
        print(f"ERROR: The file content is not valid JSON. Parser failed with error:")
        print(e)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    print("\n--- Diagnostic Complete ---")


if __name__ == "__main__":
    main()
