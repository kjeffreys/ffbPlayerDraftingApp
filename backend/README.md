# Fantasy Football Backend

## Overview

This backend is an end-to-end data pipeline written in Python. Its primary goal is to produce a single, draft-ready JSON file (`players_final.json`) that ranks fantasy football players based on a composite score of historical performance and future projections. The final ranking is determined by a "Value over Replacement" (VOR) model, which is highly configurable to suit different league strategies.

The system is built on a strict, evidence-based methodology to ensure data integrity and logical correctness at every step.

---

## How to Use (User Guide)

This guide is for running the pipeline to generate a new draft list.

### 1. Prerequisites
*   Python 3.10+
*   An active Python virtual environment (e.g., `venv`).
*   Required packages installed via `pip install -r requirements.txt`.

### 2. Configuration (The Three Key Files)

All strategic decisions are controlled by three JSON files located in the `backend/` directory. **You should only need to edit these files.**

#### `league_config.json`
This is the master control file for the entire model.

*   `"roster"`: **Crucially important for VOR.** Set the number of starters for each position. To model FLEX spots realistically, set `"FLEX": 0` and add those spots to the `RB` and `WR` counts (see "Design Decisions" below for why).
*   `"weight_projection"` & `"weight_last_year"`: Determines the blend between a player's projected performance and their historical performance. Should sum to `1.0`. **Note:** This blend only applies to veteran players. Rookies (players with no historical data) will have their score based 100% on their projection, which is a deliberate design choice.
*   `"boost_small"`, `"boost_medium"`, `"boost_large"`: Sets the percentage increase for players in your boost list (e.g., `0.15` is a 15% boost).
*   `"boost_max"`: A special boost tier intended for significant strategic elevation of a single player (e.g., making them the definitive #1 pick). A value of `1.39` represents a 139% boost.
*   `"positional_penalties"`: A dictionary to de-value certain positions. A value of `0.6` means the player's final PPG score will be multiplied by 0.6 (a 40% reduction). This is used to make Kicker and Defense rankings more realistic.

#### `player_boost.json`
This file allows you to apply a tiered boost to specific players you are high on. Find a player's slug by looking at a previous run's `players_final.json` or `players_with_ppg.json` files.

*   `"large_boost_slugs"`: A list of player slugs to receive the `boost_large` percentage.
*   `"medium_boost_slugs"`: A list of player slugs to receive the `boost_medium` percentage.
*   `"small_boost_slugs"`: A list of player slugs to receive the `boost_small` percentage.

#### `player_alias_map.json`
This file is for data cleaning. It handles cases where a player's name from an external data source doesn't perfectly match their official name from the Sleeper API. This is the **primary tool for fixing data mapping issues.**

*   **Format:** `"slug-from-external-source": "canonical-slug-from-sleeper"`
*   **Why it's important:** Different websites use different name formats (e.g., with or without 'Jr.', 'Sr.', 'II', or team abbreviations). This file creates a definitive link.
*   **Example:** Aaron Jones is a player with multiple source slugs. To ensure all his data maps to the canonical `aaron-jones` slug, we need an entry for each variation found in the wild:
    ```json
    "aaron-jones-sr": "aaron-jones",
    "aaron-jones-sr-min": "aaron-jones"
    ```

### 3. Running the Pipeline

The pipeline is controlled via the command-line interface in `cli.py`.

*   **To run the entire pipeline from start to finish:**
    ```bash
    python -m backend.cli all > report.log 2>&1
    ```
*   **To run a single phase for debugging:**
    ```bash
    python -m backend.cli stats
    ```

### 4. Finding the Output

The final, draft-ready file will be located at: `backend/data/YYYY-MM-DD/players_final.json`. This file is designed to be consumed by a web frontend.

---

## Architectural Overview & Methodology (Developer Guide)

This guide is for understanding the system's design and making changes.

### Core Methodology

This project was built (and repaired) using a strict, evidence-based methodology. **Any future changes must adhere to this process.**

1.  **Diagnose Before Fixing:** When a component is suspected to be broken, the first step is always to write a small, separate diagnostic script. This script's only job is to fetch and log the "ground truth" (e.g., raw HTML, the state of a DataFrame).
2.  **Demand Evidence:** Run the diagnostic script and capture its complete, unmodified output.
3.  **Analyze Evidence:** Propose a targeted fix based *only* on the ground truth from the diagnostic output. Do not make assumptions.
4.  **Log Everything:** Any proposed fix must include comprehensive, granular logging to verify its behavior in a real run.

### End-to-End Data Flow

The pipeline is designed with five distinct phases. Each phase produces a JSON artifact for step-by-step debugging.

### Key Design Decisions & Lessons Learned

During recent tuning and verification, several key aspects of the system's design were clarified and improved:

1.  **Player Slug Mapping is the Most Common Point of Failure:** The most significant bugs arose from external data sources using slightly different player slugs than our internal canonical format.
    *   **The Alias Map is the Solution:** The `player_alias_map.json` is the definitive, first-line tool for resolving these discrepancies. It is more reliable than fuzzy matching.
    *   **Fuzzy Matching is a Fallback, Not a Primary Tool:** The pipeline uses the `thefuzz` library to catch minor variations not covered by the alias map (e.g., `patrick-mahomes` vs. `patrick-mahomes-ii-kc`). However, it can be overly aggressive and create false positives (e.g., incorrectly mapping ADP from `aaron-jones-sr` to `tim-jones`). An explicit alias is always preferred.
    *   **Enhanced Logging for Fuzzy Matches:** The `utils.py` module now logs every fuzzy match it makes, including the confidence score. If a mapping seems incorrect, the `report.log` is the first place to look for evidence. A typical entry looks like this:
        ```json
        {"asctime": "...", "message": "Fuzzy match found.", "canonical_slug": "patrick-mahomes", "matched_source_slug": "patrick-mahomes-ii", "score": 95}
        ```

2.  **Rookie vs. Veteran Scoring:** The pre-boost score calculation in `stats.py` intentionally treats rookies differently from veterans. A veteran's score is a blend of their historical and projection data. A rookie's score is based **100% on their scaled projection**. This is to avoid penalizing them for having no historical data and provides a more accurate initial score.

3.  **FLEX Spot VOR Calculation:** The VOR model is most accurate when it can calculate replacement levels for discrete positions. The recommended approach is to set `"FLEX": 0` in the roster config and add the flex count to the `RB` and `WR` totals (e.g., a 2 RB, 2 WR, 1 FLEX league should be configured as 3 RB, 3 WR). This provides a more accurate pool of players from which to calculate replacement value.