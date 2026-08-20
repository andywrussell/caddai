"""Carry distribution statistical models.

See docs/player-model.md for the full planned design of this subsystem.
"""

from pydantic import BaseModel, Field


class CarryDistribution(BaseModel):
    """A club's carry distance modelled as a normal distribution, in metres."""

    mean_metres: float = Field(gt=0)
    stddev_metres: float = Field(ge=0)
