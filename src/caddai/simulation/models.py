"""Environment/physics transform domain models.

See docs/plans/m4.7-environment-physics-transform.plan.md for the design
this module implements (GitHub issue #55).

These models deliberately do **not** import ``caddai.strategy.models.Wind``/
``LieType`` or anything from ``caddai.player``. Importing ``caddai.strategy``
would create a reverse dependency (``simulation`` is meant to be depended on
by ``strategy``, never the other way around — see AGENTS.md's dependency
direction rules). Importing ``caddai.player`` would conflate two different
kinds of model: ``caddai.player.ShotRecord`` is an *observation/evidence*
model of a shot that actually happened (used to update a player's shot
distribution), whereas ``ShotOutcome`` here is a *forward-modelled* outcome
produced by applying a deterministic physics transform to a hypothetical or
simulated shot. They are not interchangeable and this module keeps no
coupling between them.
"""

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _require_finite(value: float) -> float:
    """Reject NaN/+inf/-inf, which otherwise satisfy ``ge``/``le`` constraints."""
    if not math.isfinite(value):
        raise ValueError("must be finite")
    return value


class WindComponents(BaseModel):
    """Wind decomposed into a shot-relative longitudinal and lateral component, in m/s.

    ``longitudinal_mps`` is signed relative to the shot's intended line of
    play: positive is a tailwind (blowing from behind the golfer toward the
    target), negative is a headwind (blowing from the target toward the
    golfer).

    ``lateral_mps`` uses the same sign convention as
    ``caddai.statistics.DirectionalDispersion.lateral_bias_metres`` and
    ``caddai.player.ShotRecord.lateral_offset_metres``: positive is a wind
    effect toward the golfer's right, negative is toward the golfer's left.

    This model is structurally immutable (``frozen=True``).
    """

    model_config = ConfigDict(frozen=True)

    longitudinal_mps: float = Field(default=0.0, ge=-60.0, le=60.0)
    lateral_mps: float = Field(default=0.0, ge=-60.0, le=60.0)

    @field_validator("longitudinal_mps", "lateral_mps")
    @classmethod
    def _validate_finite(cls, value: float) -> float:
        return _require_finite(value)


class EnvironmentInput(BaseModel):
    """The environmental conditions to apply to a forward-modelled shot outcome.

    ``elevation_delta_metres`` is signed relative to the shot's origin:
    positive means the landing target is above the shot origin (uphill),
    negative means it is below (downhill).

    ``air_density_kg_per_m3`` is optional: ``None`` means "use the reference
    air density / apply no air-density correction" — it is not a sentinel
    for zero density, which would be physically meaningless.

    This model is structurally immutable (``frozen=True``).
    """

    model_config = ConfigDict(frozen=True)

    wind: WindComponents = Field(default_factory=WindComponents)
    elevation_delta_metres: float = Field(default=0.0, ge=-200.0, le=200.0)
    air_density_kg_per_m3: float | None = Field(default=None, ge=0.4, le=1.5)

    @field_validator("elevation_delta_metres", "air_density_kg_per_m3")
    @classmethod
    def _validate_finite(cls, value: float | None) -> float | None:
        if value is None:
            return value
        return _require_finite(value)


class ShotOutcome(BaseModel):
    """A shot's downrange/lateral landing position, in metres, relative to its origin.

    This single type is used for **both** intrinsic outcomes (before any
    environment transform is applied) and transformed outcomes (after
    ``apply_environment_transform`` — see ``environment.py`` — has been
    applied). There is no ``is_transformed`` flag: callers are responsible
    for tracking which stage of the pipeline a given ``ShotOutcome`` value
    represents.

    Both fields are signed and neither is clamped: ``downrange_metres`` may
    be negative (e.g. a badly topped or thinned shot, or after a strong
    headwind correction), and ``lateral_metres`` may be negative (left,
    matching ``WindComponents.lateral_mps``'s sign convention) or positive
    (right).

    This model is structurally immutable (``frozen=True``).
    """

    model_config = ConfigDict(frozen=True)

    downrange_metres: float
    lateral_metres: float

    @field_validator("downrange_metres", "lateral_metres")
    @classmethod
    def _validate_finite(cls, value: float) -> float:
        return _require_finite(value)
