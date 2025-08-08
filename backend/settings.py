# Path: ffbPlayerDraftingApp/backend/settings.py (FINAL)

import json
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Define robust directory constants ---
_BASE_DIR = Path(__file__).resolve().parent  # .../backend
ROOT_DIR = _BASE_DIR.parent  # .../ffbPlayerDraftingApp/

_LEAGUE_CONFIG_PATH = _BASE_DIR / "league_config.json"  # Correct Path


class RosterSettings(BaseModel):
    """Defines the number of starters for each position."""

    QB: int
    RB: int
    WR: int
    TE: int
    FLEX: int
    K: int
    DEF: int


class LeagueConfig(BaseModel):
    """Defines all league-specific rules and scoring weights."""

    teams: int
    roster: RosterSettings
    scoring: str
    week: int
    games_divisor: int
    player_boost: float
    top_game_count: int
    weight_projection: float
    weight_last_year: float


def _load_league_config(path: Path) -> LeagueConfig:
    """Loads and parses the league configuration JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    return LeagueConfig(**config_data)


class Settings(BaseSettings):
    """Manages all configuration for the application."""

    # Provide robust, accessible directory constants
    ROOT_DIR: Path = ROOT_DIR
    BASE_DIR: Path = _BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"

    league_config: LeagueConfig = Field(
        default_factory=lambda: _load_league_config(_LEAGUE_CONFIG_PATH)
    )

    # API URLs
    SLEEPER_API_URL: str = "https://api.sleeper.app/v1/players/nfl"
    # This URL is now superseded by the dynamic URL in fantasypros.py, but can remain as a fallback/example.
    FANTASYPROS_ADP_URL: str = "https://www.fantasypros.com/nfl/adp/ppr-overall.php"

    # Secrets loaded from the environment
    YAHOO_CLIENT_ID: str = "your_yahoo_client_id"
    YAHOO_CLIENT_SECRET: str = "your_yahoo_client_secret"

    # Pydantic settings configuration
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env", env_file_encoding="utf-8", case_sensitive=False
    )


# Singleton instance to be used by the rest of the application
settings = Settings()
