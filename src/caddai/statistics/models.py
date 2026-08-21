"""Carry distribution and directional dispersion statistical models.

See docs/player-model.md for the full planned design of this subsystem.
"""

import math

from pydantic import BaseModel, Field, field_validator


def _require_finite(value: float) -> float:
    """Reject NaN/+inf/-inf, which otherwise satisfy ``gt=0``/``ge=0`` constraints."""
    if not math.isfinite(value):
        raise ValueError("must be finite")
    return value


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
