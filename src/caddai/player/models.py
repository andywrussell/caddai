"""Player and club domain models.

See docs/player-model.md for the full planned design of this subsystem.
"""

import math
from enum import StrEnum

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

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
    """Where/how a ShotRecord's measurement originated — method/origin only.

    Answers "where/how did this measurement originate?"; trustworthiness is
    ``ShotMeasurementQuality``'s separate job, not this enum's. A distinct
    semantic axis from ``caddai.player.onboarding.CarryProvenance`` (which
    describes trust in a one-off onboarding self-reported cold-start
    number, not a historical shot observation) — see that module's
    docstring. ``LAUNCH_MONITOR`` is used for
    ``observed_carry_measurement.source``; ``GPS_DEVICE``/``MANUAL`` are
    used for ``endpoint_measurement.source``. Metadata only: does not
    affect ``final_downrange_metres``, ``observed_carry_metres``, or
    ``lateral_offset_metres``, and must never be used to derive
    ``PlayerShotDistribution``/``CarryDistribution``/``DirectionalDispersion``
    parameters in this issue (that is for a future personal-learning
    updater to decide).
    """

    LAUNCH_MONITOR = "launch_monitor"
    GPS_DEVICE = "gps_device"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class ShotMeasurementQuality(StrEnum):
    """How trustworthy/useful a ShotRecord's observation is.

    Independent of, and not derived from, ``ShotMeasurementSource`` — two
    ``LAUNCH_MONITOR`` shots can still differ in quality. Metadata only:
    never alters ``final_downrange_metres``, ``observed_carry_metres``, or
    ``lateral_offset_metres``, and must never be used to derive
    distribution parameters in this issue.
    """

    UNKNOWN = "unknown"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ShotMeasurementMetadata(BaseModel):
    """Provenance/quality for one measured quantity on a ``ShotRecord``.

    Composed once as ``endpoint_measurement`` — covering both
    ``final_downrange_metres`` and ``lateral_offset_metres``, since both
    are decompositions of one single final-position observation against
    the target line — and once as ``observed_carry_measurement``, a
    separate, distinct instrument/event (e.g. a launch monitor reading)
    unrelated in time or source to the final-position fix. This submodel
    is composed once per quantity-origin rather than once per record, so
    it never falsely implies every quantity on a record shares one
    source/quality.
    """

    source: ShotMeasurementSource = ShotMeasurementSource.UNKNOWN
    quality: ShotMeasurementQuality = ShotMeasurementQuality.UNKNOWN


class ShotRecord(BaseModel):
    """A single observed shot outcome for a club — evidence only.

    Normal on-course CaddAI use cannot directly observe the ball's first
    landing point (true carry): it can only observe shot start and finish
    position, from which ``final_downrange_metres`` and
    ``lateral_offset_metres`` are derived. True carry is latent and is
    genuinely observed only occasionally, by a suitable direct-measurement
    source (e.g. a launch monitor) — ``observed_carry_metres`` is ``None``
    for the overwhelming majority of on-course shots, and must never be
    auto-populated from an estimate.

    ``ShotRecord`` records evidence/observations only. Estimating latent
    carry from downrange distance (using club, shot regime, rollout,
    surface, wind, elevation, etc.) is a future, separate inference step —
    not implemented here — that will read this evidence, not write it.
    Nothing on this model feeds ``PlayerShotDistribution``/
    ``CarryDistribution``/``DirectionalDispersion`` math.

    ``final_downrange_metres`` is the downrange component of the final
    resting position along the intended target line — i.e. the distance
    from the shot's start position to the perpendicular projection of the
    final position onto that line. Not the straight-line start-to-finish
    displacement, which would be
    ``sqrt(final_downrange_metres**2 + lateral_offset_metres**2)``.
    ``final_downrange_metres`` may be negative — a severe mishit (e.g. a
    thin/top, a deflection off an obstruction, or an extreme contact
    error) can leave the final position behind the shot's start position
    along the intended target line's direction. This is a genuine,
    evidence-preserving outcome, not a data-entry error, so no
    non-negativity constraint is enforced here, unlike
    ``observed_carry_metres`` (a genuine scalar physical carry-distance
    measurement, not a coordinate, and definitionally non-negative).

    The "intended target line" referenced above is the line implied by the
    golfer's own selected/accepted target for this specific shot — not
    automatically the pin, green centre, hole centreline, or a
    CaddAI-recommended target, unless the golfer actually accepted that
    target (in which case selected target == recommended target; if they
    overrode it, selected target != recommended target). Computing
    ``final_downrange_metres``/``lateral_offset_metres`` from raw
    start/target/finish positions, and recording which target was actually
    selected, is the responsibility of upstream round/decision-journal code
    — not implemented here (see ``docs/decision-journal.md``) —
    ``ShotRecord`` stores only the resulting target-line-relative
    coordinates, never the target itself. This distinction matters: a
    golfer's deliberate aim away from a recommended target must never be
    misread as player dispersion/bias by a future learning step.

    Sign convention for ``lateral_offset_metres``: negative is left of the
    intended target line, zero is on-line with the intended target, and
    positive is right of the intended target line — independent of player
    handedness (same convention as ``DirectionalDispersion.lateral_bias_metres``).

    ``endpoint_measurement`` describes the source/quality of the single
    final-position observation that both ``final_downrange_metres`` and
    ``lateral_offset_metres`` are derived from — not two independent
    measurements — and is always present (a quantity that is always
    required has metadata by default). ``observed_carry_measurement`` is
    ``None`` exactly when ``observed_carry_metres`` is ``None`` — a
    metadata object describing the provenance of a value that doesn't
    exist would be meaningless, so the two are enforced to be null-paired.

    No constraint is enforced between ``observed_carry_metres`` and
    ``final_downrange_metres`` (e.g. carry <= downrange) — they may come
    from independent instruments that can legitimately disagree, and this
    model records evidence, not physics consistency.
    """

    club_name: str = Field(min_length=1)
    final_downrange_metres: float
    lateral_offset_metres: float
    endpoint_measurement: ShotMeasurementMetadata = Field(default_factory=ShotMeasurementMetadata)
    observed_carry_metres: float | None = Field(default=None, ge=0)
    observed_carry_measurement: ShotMeasurementMetadata | None = None
    notes: str | None = None

    @field_validator("final_downrange_metres", "lateral_offset_metres")
    @classmethod
    def _validate_finite(cls, value: float) -> float:
        return _require_finite(value)

    @field_validator("observed_carry_metres")
    @classmethod
    def _validate_observed_carry_finite(cls, value: float | None) -> float | None:
        if value is None:
            return value
        return _require_finite(value)

    @model_validator(mode="after")
    def _validate_observed_carry_metadata_pairing(self) -> "ShotRecord":
        if (self.observed_carry_metres is None) != (self.observed_carry_measurement is None):
            raise ValueError(
                "observed_carry_metres and observed_carry_measurement must both be "
                "present or both be None"
            )
        return self


class Player(BaseModel):
    """A player identified by name, their bag of clubs, and shot history."""

    name: str = Field(min_length=1)
    clubs: list[Club] = Field(min_length=1)
    shot_history: list[ShotRecord] = Field(default_factory=list)
