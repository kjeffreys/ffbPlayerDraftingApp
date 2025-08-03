# /home/kyle/repos/ffbPlayerDraftingApp/backend/settings.py

import json
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ... (LeagueConfig, RosterSettings models are unchanged) ...
class RosterSettings(BaseModel):
    QB: int
    RB: int
    WR: int
    TE: int
    FLEX: int
    K: int
    DEF: int


class LeagueConfig(BaseModel):
    teams: int
    roster: RosterSettings
    scoring: str
    week: int
    games_divisor: int
    rookie_bonus: float
    top_game_count: int
    weight_projection: float
    weight_last_year: float


def _load_league_config(path: Path) -> LeagueConfig:
    with open(path) as f:
        config_data = json.load(f)
    return LeagueConfig(**config_data)


class Settings(BaseSettings):
    """Core application settings."""

    # CRITICAL FIX: BASE_DIR is now the parent of this file, which is 'backend/'.
    BASE_DIR: Path = Path(__file__).resolve().parent

    # This now correctly points to backend/data
    DATA_DIR: Path = BASE_DIR / "data"

    # This now correctly points to backend/league_config.json
    LEAGUE_CONFIG_PATH: Path = BASE_DIR / "league_config.json"
    league_config: LeagueConfig = Field(
        default_factory=lambda: _load_league_config(Settings().LEAGUE_CONFIG_PATH)
    )

    # API URLs
    SLEEPER_API_URL: str = "https://api.sleeper.app/v1/players/nfl"
    FANTASYPROS_ADP_URL: str = "https://www.fantasypros.com/nfl/adp/ppr-overall.php"

    YAHOO_CLIENT_ID: str = Field(..., env="YAHOO_CLIENT_ID")
    YAHOO_CLIENT_SECRET: str = Field(..., env="YAHOO_CLIENT_SECRET")

    # This now correctly looks for '.env' in the 'backend/' directory.
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", case_sensitive=False
    )


settings = Settings()
