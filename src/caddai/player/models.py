"""Player and club domain models.

See docs/player-model.md for the full planned design of this subsystem.
"""

from pydantic import BaseModel, Field


class Club(BaseModel):
    """A golf club and its expected carry distance.

    This is a deliberate M1 placeholder standing in for the future carry
    distribution statistical model (M3, see docs/player-model.md): carry is
    represented here as a single scalar `expected_carry_metres`, not a
    distribution.
    """

    name: str = Field(min_length=1)
    expected_carry_metres: float = Field(gt=0)


class Player(BaseModel):
    """A player identified by name and their bag of clubs."""

    name: str = Field(min_length=1)
    clubs: list[Club] = Field(min_length=1)
