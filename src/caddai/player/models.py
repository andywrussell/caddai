"""Player and club domain models.

See docs/player-model.md for the full planned design of this subsystem.
"""

from pydantic import BaseModel, Field, computed_field

from caddai.statistics import CarryDistribution, DirectionalDispersion


class Club(BaseModel):
    """A golf club, its carry distribution, and its directional dispersion."""

    name: str = Field(min_length=1)
    carry_distribution: CarryDistribution
    dispersion: DirectionalDispersion

    @computed_field  # type: ignore[prop-decorator]
    @property
    def expected_carry_metres(self) -> float:
        """The club's expected carry distance, derived from its carry distribution."""
        return self.carry_distribution.mean_metres

    @classmethod
    def with_expected_carry(cls, name: str, expected_carry_metres: float) -> "Club":
        """Build a club from a bare expected-carry scalar.

        Returns a placeholder/degenerate (zero-variance, zero-bias) carry
        distribution and dispersion, not a measured one — use this only
        where no real distribution/dispersion data is available yet.
        """
        return cls(
            name=name,
            carry_distribution=CarryDistribution(
                mean_metres=expected_carry_metres, stddev_metres=0.0
            ),
            dispersion=DirectionalDispersion(lateral_stddev_metres=0.0, lateral_bias_metres=0.0),
        )


class Player(BaseModel):
    """A player identified by name and their bag of clubs."""

    name: str = Field(min_length=1)
    clubs: list[Club] = Field(min_length=1)
