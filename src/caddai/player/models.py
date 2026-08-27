"""Player and club domain models.

See docs/player-model.md for the full planned design of this subsystem.
"""

import math
from enum import StrEnum

from pydantic import BaseModel, Field, computed_field, field_validator

from caddai.statistics import CarryDistribution, DirectionalDispersion
from caddai.statistics import ClubCategory as ClubCategory  # explicit re-export (mypy strict)


def _require_finite(value: float) -> float:
    """Reject NaN/+inf/-inf, which otherwise satisfy ``gt=0``/``ge=0`` constraints."""
    if not math.isfinite(value):
        raise ValueError("must be finite")
    return value


class Club(BaseModel):
    """A golf club, its carry distribution, and its directional dispersion."""

    name: str = Field(min_length=1)
    carry_distribution: CarryDistribution
    dispersion: DirectionalDispersion
    category: ClubCategory

    @computed_field  # type: ignore[prop-decorator]
    @property
    def expected_carry_metres(self) -> float:
        """The club's expected carry distance, derived from its carry distribution."""
        return self.carry_distribution.mean_metres

    @classmethod
    def with_expected_carry(
        cls,
        name: str,
        expected_carry_metres: float,
        category: ClubCategory = ClubCategory.OTHER,
    ) -> "Club":
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
            category=category,
        )


class ShotMeasurementSource(StrEnum):
    """Where a ShotRecord's measurement came from.

    A distinct semantic axis from ``caddai.player.onboarding.CarryProvenance``
    (which describes trust in a one-off onboarding self-reported cold-start
    number, not a historical shot observation) — see that module's
    docstring. Metadata only: does not affect ``achieved_carry_metres`` or
    ``lateral_offset_metres``, and must never be used to derive
    ``PlayerShotDistribution``/``CarryDistribution``/``DirectionalDispersion``
    parameters in this issue (that is for a future personal-learning
    updater to decide).
    """

    MEASURED = "measured"
    GPS_ESTIMATE = "gps_estimate"
    MANUAL_ESTIMATE = "manual_estimate"
    UNKNOWN = "unknown"


class ShotMeasurementQuality(StrEnum):
    """How trustworthy/useful a ShotRecord's observation is.

    Independent of, and not derived from, ``ShotMeasurementSource`` — two
    ``MEASURED`` shots can still differ in quality. Metadata only: never
    alters ``achieved_carry_metres``/``lateral_offset_metres``, and must
    never be used to derive distribution parameters in this issue.
    """

    UNKNOWN = "unknown"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ShotRecord(BaseModel):
    """A single manually entered, observed shot outcome for a club.

    Sign convention for ``lateral_offset_metres``: negative is left of the
    intended target line, zero is on-line with the intended target, and
    positive is right of the intended target line — independent of player
    handedness (same convention as ``DirectionalDispersion.lateral_bias_metres``).

    ``measurement_source`` and ``measurement_quality`` let future personal
    shot-distribution learning (M4.5, not implemented here) distinguish
    genuinely observed shots from estimated, low-quality, or
    unknown-provenance ones. Both are metadata only in this issue: they do
    not affect ``achieved_carry_metres``/``lateral_offset_metres`` and are
    not consumed by any statistics/distribution math here.
    """

    club_name: str = Field(min_length=1)
    achieved_carry_metres: float = Field(ge=0)
    lateral_offset_metres: float
    notes: str | None = None
    measurement_source: ShotMeasurementSource = ShotMeasurementSource.UNKNOWN
    measurement_quality: ShotMeasurementQuality = ShotMeasurementQuality.UNKNOWN

    @field_validator("achieved_carry_metres", "lateral_offset_metres")
    @classmethod
    def _validate_finite(cls, value: float) -> float:
        return _require_finite(value)


class Player(BaseModel):
    """A player identified by name, their bag of clubs, and shot history."""

    name: str = Field(min_length=1)
    clubs: list[Club] = Field(min_length=1)
    shot_history: list[ShotRecord] = Field(default_factory=list)
