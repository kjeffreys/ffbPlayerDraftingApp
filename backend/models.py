# backend/backend/models.py
"""Pydantic models for typed data structures."""

from pydantic import BaseModel, Field


class PlayerRaw(BaseModel):
    """
    Represents the raw player data structure from the Sleeper API.
    Includes fields relevant for the initial cleaning and enrichment phases.
    """

    player_id: str
    first_name: str
    last_name: str
    position: str | None = None
    team: str | None = None
    bye_week: int | None = Field(default=None, alias="fantasy_data_tms_bye_week")

    # This allows Pydantic to populate 'bye_week' from the 'fantasy_data_tms_bye_week' key in the source JSON
    class Config:
        populate_by_name = True

    def model_dump(self, **kwargs) -> dict:
        # We ensure the alias is used for dumping if needed, though for our use case it's less critical.
        return super().model_dump(by_alias=True, **kwargs)


class PlayerEnriched(PlayerRaw):
    """
    Represents a player after being enriched with external data like ADP
    and fantasy point projections. Inherits all fields from PlayerRaw.
    """

    adp: float | None = None
    projected_points: float | None = None


class PlayerWithPPG(PlayerEnriched):
    """
    Represents a player after the 'expected_ppg' score has been calculated.
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
