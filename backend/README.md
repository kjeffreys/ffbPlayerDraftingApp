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
*   `"weight_projection"` & `"weight_last_year"`: Determines the blend between a player's projected performance and their historical performance. Should sum to `1.0`.
*   `"boost_small"`, `"boost_medium"`, `"boost_large"`: Sets the percentage increase for players in your boost list (e.g., `0.15` is a 15% boost).
*   `"positional_penalties"`: A dictionary to de-value certain positions. A value of `0.6` means the player's final PPG score will be multiplied by 0.6 (a 40% reduction). This is used to make Kicker and Defense rankings more realistic.

#### `player_boost.json`
This file allows you to apply a tiered boost to specific players you are high on.

*   `"large_boost_slugs"`: A list of player slugs to receive the `boost_large` percentage.
*   `"medium_boost_slugs"`: A list of player slugs to receive the `boost_medium` percentage.
*   `"small_boost_slugs"`: A list of player slugs to receive the `boost_small` percentage.

#### `player_alias_map.json`
This file is for data cleaning. It handles cases where a player's name from an external data source (like a historical stats website) doesn't perfectly match their official name from the Sleeper API.

*   **Format:** `"slug-from-external-source": "canonical-slug-from-sleeper"`
*   *Example:* `"patrick-mahomes": "patrick-mahomes-ii-kc"`

### 3. Running the Pipeline

The pipeline is controlled via the command-line interface in `cli.py`.

*   **To run the entire pipeline from start to finish:**
    ```bash
    python -m backend.cli all
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