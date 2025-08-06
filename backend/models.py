# Path: ffbPlayerDraftingApp/backend/models.py

"""Pydantic models for typed data structures throughout the pipeline."""

from pydantic import BaseModel, ConfigDict, Field


class PlayerRaw(BaseModel):
    """
    Represents the raw player data structure from the Sleeper API.
    Only includes fields relevant for the initial cleaning and enrichment phases.
    """

    player_id: str
    first_name: str
    last_name: str
    position: str | None = None
    team: str | None = None
    # The 'alias' allows Pydantic to read from a different key name in the source JSON.
    bye_week: int | None = Field(default=None, alias="fantasy_data_tms_bye_week")

    # This config tells Pydantic to respect the 'alias' when populating the model.
    model_config = ConfigDict(populate_by_name=True)


class PlayerEnriched(PlayerRaw):
    """
    Represents a player after being enriched with external data like ADP
    and fantasy point projections. Inherits all fields from PlayerRaw.
    """

    adp: float | None = None
    projected_points: float | None = None


class PlayerWithPPG(PlayerEnriched):
    """
    Represents a player after the composite 'expected_ppg' score has been calculated.
    This model is primarily for data moving from the stats to the VOR phase.
    """

    expected_ppg: float


class PlayerFinal(PlayerWithPPG):
    """
    The final player model, including Value over Replacement (VOR) and
    the final overall rank. This is the model for the final JSON export.
    """

    vor: float
    rank: int
