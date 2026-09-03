# Path: ffbPlayerDraftingApp/backend/settings.py (FIXED)

from pathlib import Path
import json
import os

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- FIX: Import the log object ---
from backend.logging_config import log

# ------------------------------------

# --- Define robust directory constants ---
_BASE_DIR = Path(__file__).resolve().parent  # .../backend
ROOT_DIR = _BASE_DIR.parent  # .../ffbPlayerDraftingApp/

_LEAGUE_CONFIG_PATH = Path(
    os.environ.get("LEAGUE_CONFIG_PATH", _BASE_DIR / "league_config.json")
)


class RosterSettings(BaseModel):
    """Defines the number of starters for each position."""

    model_config = ConfigDict(extra="forbid")

    QB: int
    RB: int
    WR: int
    TE: int
    FLEX: int
    SUPERFLEX: int = 0
    K: int
    DEF: int


class LeagueConfig(BaseModel):
    """Defines all league-specific rules and scoring weights."""

    model_config = ConfigDict(extra="forbid")

    league_type: str = "redraft"
    teams: int
    roster: RosterSettings
    draft_targets: dict[str, int] = Field(default_factory=dict)
    scoring: str
    week: int
    games_divisor: int
    boost_small: float
    boost_medium: float
    boost_large: float
    boost_max: float
    top_game_count: int
    weight_projection: float
    weight_last_year: float | None = None
    weight_floor: float | None = None
    weight_superflex_ecr: float = 0.0
    weight_dynasty_ecr: float = 0.0
    superflex_qb_premiums: list[dict[str, float]] = Field(default_factory=list)
    context_overrides_path: str | list[str] | None = None
    market_guardrail_min_market_rank: float | None = None
    market_guardrail_allowed_lead: float = 45.0
    market_guardrail_context_bonus: float = 20.0
    zero_projection_guardrail_min_market_rank: float | None = None
    zero_projection_multiplier: float = 0.05
    min_historical_score: float
    positional_penalties: dict[str, float]

    @model_validator(mode="after")
    def validate_scoring_weights(self) -> "LeagueConfig":
        """Fail fast when a league config cannot drive its scoring model."""
        if self.league_type == "guillotine":
            if self.weight_floor is None:
                raise ValueError("guillotine leagues require weight_floor")
            total = self.weight_projection + self.weight_floor
        else:
            if self.weight_last_year is None:
                raise ValueError("non-guillotine leagues require weight_last_year")
            total = self.weight_projection + self.weight_last_year

        if abs(total - 1.0) > 0.001:
            raise ValueError(
                "scoring weights must sum to 1.0 "
                f"(got {total:.3f} for {self.league_type})"
            )

        market_total = self.weight_superflex_ecr + self.weight_dynasty_ecr
        if market_total < 0 or market_total > 0.5:
            raise ValueError("market ranking weights must be between 0.0 and 0.5 total")

        if self.league_type not in {"redraft", "guillotine", "champions"}:
            raise ValueError(f"unknown league_type: {self.league_type}")

        if self.market_guardrail_min_market_rank is not None and self.market_guardrail_min_market_rank <= 0:
            raise ValueError("market_guardrail_min_market_rank must be positive")
        if self.market_guardrail_allowed_lead <= 0:
            raise ValueError("market_guardrail_allowed_lead must be positive")
        if self.market_guardrail_context_bonus < 0:
            raise ValueError("market_guardrail_context_bonus cannot be negative")
        if (
            self.zero_projection_guardrail_min_market_rank is not None
            and self.zero_projection_guardrail_min_market_rank <= 0
        ):
            raise ValueError("zero_projection_guardrail_min_market_rank must be positive")
        if self.zero_projection_multiplier < 0 or self.zero_projection_multiplier > 1:
            raise ValueError("zero_projection_multiplier must be between 0.0 and 1.0")

        return self


def _load_league_config(path: Path) -> LeagueConfig:
    """Loads and parses the league configuration JSON file."""
    # --- This line will now work correctly ---
    log.info(f"CRITICAL DIAGNOSTIC: Loading league configuration from: {path}")
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
