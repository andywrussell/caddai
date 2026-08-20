"""Carry distribution and directional dispersion statistical models.

See docs/player-model.md for the full planned design of this subsystem.
"""

from pydantic import BaseModel, Field


class CarryDistribution(BaseModel):
    """A club's carry distance modelled as a normal distribution, in metres."""

    mean_metres: float = Field(gt=0)
    stddev_metres: float = Field(ge=0)


class DirectionalDispersion(BaseModel):
    """A club's lateral shot spread and systematic bias, in metres.

    Sign convention for ``lateral_bias_metres``: negative is left of the
    intended target line, zero is on-line with the intended target, and
    positive is right of the intended target line — independent of player
    handedness.
    """

    lateral_stddev_metres: float = Field(ge=0)
    lateral_bias_metres: float
