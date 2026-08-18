"""Strategy request/result domain models.

See docs/strategy-engine.md and
docs/plans/m1-core-domain-vertical-slice.plan.md (Task 2) for context.
"""

from enum import StrEnum

from pydantic import BaseModel, Field

from caddai.player import Club, Player


class WindDirection(StrEnum):
    """Wind direction relative to the shot line."""

    HEADWIND = "headwind"
    TAILWIND = "tailwind"
    CROSSWIND = "crosswind"


class Wind(BaseModel):
    """Wind affecting a shot.

    M1 simplification: wind is treated as a scalar along-shot component
    only — a headwind lengthens playing distance, a tailwind shortens it,
    and a crosswind has no effect on playing distance in this model. There
    is no bearing/vector wind model until `gps`/`course` exist.
    """

    speed_mps: float = Field(ge=0)
    direction: WindDirection


class LieType(StrEnum):
    """Where the ball is lying before the shot."""

    TEE = "tee"
    FAIRWAY = "fairway"
    ROUGH = "rough"
    BUNKER = "bunker"
    RECOVERY = "recovery"


class RecommendationRequest(BaseModel):
    """A request for a club recommendation for a single shot."""

    player: Player
    target_distance_metres: float = Field(gt=0)
    wind: Wind
    lie: LieType


class RecommendationResult(BaseModel):
    """A deterministic club recommendation for a single shot."""

    selected_club: Club
    playing_distance_metres: float
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str] = Field(min_length=1)
