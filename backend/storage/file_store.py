# backend/backend/storage/file_store.py
"""Utilities for saving and loading data artifacts from the filesystem."""

import json
from pathlib import Path
from typing import Any

from backend.logging_config import setup_logging

log = setup_logging(__name__)

# ... (save_json function from before remains unchanged) ...


def save_json(file_path: Path, data: Any):
    """
    Saves data to a JSON file, creating parent directories if they don't exist.

    Args:
        file_path (Path): The full path to the output file.
        data (Any): The JSON-serializable data to save.
    """
    try:
        log.info("Attempting to save JSON artifact.", extra={"path": str(file_path)})
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        log.info("Successfully saved JSON artifact.", extra={"path": str(file_path)})
    except (OSError, TypeError) as e:
        log.exception(
            "Failed to save JSON file.", extra={"path": str(file_path), "error": str(e)}
        )
        raise


# --- NEW FUNCTION ---
def load_json(file_path: Path) -> Any:
    """
    Loads data from a JSON file.

    Args:
        file_path (Path): The full path to the input file.

    Returns:
        The deserialized data from the JSON file.
    """
    log.info("Attempting to load JSON artifact.", extra={"path": str(file_path)})
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        log.info("Successfully loaded JSON artifact.", extra={"path": str(file_path)})
        return data
    except (OSError, json.JSONDecodeError) as e:
        log.exception(
            "Failed to load JSON file.", extra={"path": str(file_path), "error": str(e)}
        )
        raise
