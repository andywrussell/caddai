"""Carry distribution and directional dispersion statistical models.

See docs/player-model.md for the full planned design of this subsystem.
"""

import math
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from caddai.statistics.shot_distribution import ShotDistributionFamily


def _require_finite(value: float) -> float:
    """Reject NaN/+inf/-inf, which otherwise satisfy ``gt=0``/``ge=0`` constraints."""
    if not math.isfinite(value):
        raise ValueError("must be finite")
    return value


class ClubCategory(StrEnum):
    """The broad category a club belongs to.

    Metadata only — no strategy behaviour keys off this yet.
    """

    DRIVER = "driver"
    FAIRWAY_WOOD = "fairway_wood"
    HYBRID = "hybrid"
    IRON = "iron"
    WEDGE = "wedge"
    PUTTER = "putter"
    OTHER = "other"


class CarryDistribution(BaseModel):
    """A club's carry distance modelled as a normal distribution, in metres."""

    mean_metres: float = Field(gt=0)
    stddev_metres: float = Field(ge=0)

    @field_validator("mean_metres", "stddev_metres")
    @classmethod
    def _validate_finite(cls, value: float) -> float:
        return _require_finite(value)


class DirectionalDispersion(BaseModel):
    """A club's lateral shot spread and systematic bias, in metres.

    Sign convention for ``lateral_bias_metres``: negative is left of the
    intended target line, zero is on-line with the intended target, and
    positive is right of the intended target line — independent of player
    handedness.
    """

    lateral_stddev_metres: float = Field(ge=0)
    lateral_bias_metres: float

    @field_validator("lateral_stddev_metres", "lateral_bias_metres")
    @classmethod
    def _validate_finite(cls, value: float) -> float:
        return _require_finite(value)


class HandicapBand(StrEnum):
    """A coarse WHS Handicap Index band used for population-prior lookup.

    Half-open range containment, no interpolation between bands — see
    ``population_prior.resolve_population_prior``.
    """

    PLUS = "plus"
    LOW = "low"
    MID = "mid"
    HIGH = "high"


class PopulationPriorParameters(BaseModel):
    """The scale/correlation/tail parameters a population prior can supply.

    Deliberately excludes ``carry_location_metres``/``lateral_bias_metres``
    — see ``population_prior``'s module docstring. Field bounds mirror
    ``PlayerShotDistribution`` (``shot_distribution.py``) exactly, so a
    resolved instance is always compatible with that type's constructor.
    """

    family: ShotDistributionFamily = ShotDistributionFamily.BIVARIATE_STUDENT_T
    carry_scale_metres: float = Field(gt=0)
    lateral_scale_metres: float = Field(gt=0)
    correlation: float = Field(gt=-1.0, lt=1.0)
    degrees_of_freedom: float = Field(gt=2.0)

    @field_validator(
        "carry_scale_metres", "lateral_scale_metres", "correlation", "degrees_of_freedom"
    )
    @classmethod
    def _validate_finite(cls, value: float) -> float:
        return _require_finite(value)
