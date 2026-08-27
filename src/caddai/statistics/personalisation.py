"""Pure partial-pooling (empirical-Bayes-style shrinkage) shot-distribution updates.

See GitHub issue #53 ("M4.5 — Personal partial-pooling player-model
updater") and
docs/plans/m4.5-personal-partial-pooling-updater.plan.md for the full
Architect-approved design this module implements. This module holds only
the pure shrinkage math over a ``PlayerShotDistribution`` (ADR 0006) and
generic weighted-observation arrays — it does not import ``caddai.player``
and knows nothing about ``ShotRecord``. Turning a player's shot history
into the ``WeightedObservations``/``WeightedJointObservations`` inputs this
module consumes is ``caddai.player.personalisation``'s job.

**Shrinkage approach (per parameter, all closed-form, deterministic, no
RNG/Monte Carlo):**

- ``carry_location_metres``/``lateral_bias_metres`` (location): a
  pseudo-count-weighted convex combination of the prior value and the
  weighted sample mean of the evidence,
  ``posterior = (location_prior_pseudo_count * prior + n * sample_mean) /
  (location_prior_pseudo_count + n)``, where ``n = sum(weights)``. No
  evidence (``n == 0``) leaves the value unchanged
  (``DimensionUpdateOutcome.NO_EVIDENCE``); any positive evidence updates
  it (``DimensionUpdateOutcome.UPDATED``) — there is no minimum-evidence
  gate for location.
- ``carry_scale_metres``/``lateral_scale_metres`` (dispersion): converted
  to variance via the same ``nu / (nu - 2)`` factor
  ``PlayerShotDistribution.implied_covariance_metres_sq`` uses (Student-t
  scale is *not* standard deviation), pooled as variances using
  ``dispersion_prior_pseudo_count``, then converted back to a scale. Gated
  by ``dispersion_min_effective_observations``: ``n == 0`` ->
  ``NO_EVIDENCE``; ``0 < n < threshold`` -> ``INSUFFICIENT_EVIDENCE``
  (value held exactly at the prior); ``n >= threshold`` -> ``UPDATED``.
- ``correlation``: a weighted-Pearson-correlation sample statistic pooled
  with the prior correlation using ``correlation_prior_pseudo_count``, hard
  gated by ``correlation_min_effective_observations`` the same way scale
  is gated. Near-degenerate evidence (either leg's weighted variance
  effectively zero) is treated as ``INSUFFICIENT_EVIDENCE`` rather than
  dividing by ~zero. The sample correlation is clipped to a safe open
  sub-interval before pooling so the posterior can never reach exactly
  +/-1 (which would violate ``PlayerShotDistribution``'s own invariant).
- ``degrees_of_freedom``: always retained unchanged in V1 — never
  estimated from evidence — outcome is always
  ``DimensionUpdateOutcome.HELD_FIXED_BY_POLICY``.

The resulting ``PlayerShotDistribution`` is built through its normal
constructor (not ``model_construct``), so Pydantic validation runs as
defense-in-depth against any invariant this module's own math might
otherwise violate.
"""

import math
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator

from caddai.statistics.shot_distribution import PlayerShotDistribution, ShotDistributionFamily


def _require_finite(value: float) -> float:
    """Reject NaN/+inf/-inf, which otherwise satisfy ``gt``/``ge`` constraints."""
    if not math.isfinite(value):
        raise ValueError("must be finite")
    return value


# Sample variance below this is treated as degenerate (avoids dividing by
# ~zero when computing a weighted Pearson correlation) — not a calibrated
# value, just small enough to only catch genuinely near-constant evidence.
_NEAR_ZERO_VARIANCE = 1e-9

# Sample correlation is clipped to this open sub-interval before pooling,
# so the posterior can never land on the +/-1 boundary
# ``PlayerShotDistribution.correlation`` forbids.
_CORRELATION_CLIP_BOUND = 0.999999


class PersonalisationConfig(BaseModel):
    """Pseudo-counts/thresholds controlling partial-pooling shrinkage strength.

    All numeric fields are provisional/illustrative pending calibration
    data — see ``DEFAULT_PERSONALISATION_CONFIG``.
    """

    config_version: str = Field(min_length=1)
    location_prior_pseudo_count: float = Field(gt=0)
    dispersion_prior_pseudo_count: float = Field(gt=0)
    dispersion_min_effective_observations: float = Field(gt=0)
    correlation_prior_pseudo_count: float = Field(gt=0)
    correlation_min_effective_observations: float = Field(gt=0)

    @field_validator(
        "location_prior_pseudo_count",
        "dispersion_prior_pseudo_count",
        "dispersion_min_effective_observations",
        "correlation_prior_pseudo_count",
        "correlation_min_effective_observations",
    )
    @classmethod
    def _validate_finite(cls, value: float) -> float:
        return _require_finite(value)


class WeightedObservations(BaseModel):
    """A single-dimension array of evidence values paired with per-value weights."""

    values: tuple[float, ...]
    weights: tuple[float, ...]

    @field_validator("values")
    @classmethod
    def _validate_values_finite(cls, values: tuple[float, ...]) -> tuple[float, ...]:
        for value in values:
            _require_finite(value)
        return values

    @field_validator("weights")
    @classmethod
    def _validate_weights(cls, weights: tuple[float, ...]) -> tuple[float, ...]:
        for weight in weights:
            _require_finite(weight)
            if weight < 0.0:
                raise ValueError("weights must be >= 0")
        return weights

    @model_validator(mode="after")
    def _validate_matching_lengths(self) -> "WeightedObservations":
        if len(self.values) != len(self.weights):
            raise ValueError("values and weights must have equal length")
        return self


class WeightedJointObservations(BaseModel):
    """A paired (carry, lateral) array of evidence values, for correlation evidence."""

    carry_values: tuple[float, ...]
    lateral_values: tuple[float, ...]
    weights: tuple[float, ...]

    @field_validator("carry_values", "lateral_values")
    @classmethod
    def _validate_values_finite(cls, values: tuple[float, ...]) -> tuple[float, ...]:
        for value in values:
            _require_finite(value)
        return values

    @field_validator("weights")
    @classmethod
    def _validate_weights(cls, weights: tuple[float, ...]) -> tuple[float, ...]:
        for weight in weights:
            _require_finite(weight)
            if weight < 0.0:
                raise ValueError("weights must be >= 0")
        return weights

    @model_validator(mode="after")
    def _validate_matching_lengths(self) -> "WeightedJointObservations":
        if len(self.carry_values) != len(self.lateral_values) or len(self.carry_values) != len(
            self.weights
        ):
            raise ValueError("carry_values, lateral_values, and weights must have equal length")
        return self


class DimensionUpdateOutcome(StrEnum):
    """What happened to a single ``PlayerShotDistribution`` dimension during shrinkage."""

    UPDATED = "updated"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NO_EVIDENCE = "no_evidence"
    HELD_FIXED_BY_POLICY = "held_fixed_by_policy"


class ShotDistributionUpdateResult(BaseModel):
    """A ``shrink_shot_distribution`` outcome: the posterior distribution plus per-dimension
    bookkeeping (how much evidence was available, and what happened as a result)."""

    shot_distribution: PlayerShotDistribution
    config_version: str
    carry_location_effective_n: float
    carry_location_outcome: DimensionUpdateOutcome
    lateral_bias_effective_n: float
    lateral_bias_outcome: DimensionUpdateOutcome
    carry_scale_effective_n: float
    carry_scale_outcome: DimensionUpdateOutcome
    lateral_scale_effective_n: float
    lateral_scale_outcome: DimensionUpdateOutcome
    correlation_effective_n: float
    correlation_outcome: DimensionUpdateOutcome
    degrees_of_freedom_outcome: DimensionUpdateOutcome


STATISTICS_PERSONALISATION_CONFIG_VERSION = "m4.5-provisional-v1"

# Provisional, unvalidated pseudo-counts/thresholds pending calibration
# data — mirrors population_prior_config.py's/onboarding.py's own
# provisional numbers. Not evidence-derived; replaceable without an ADR.
DEFAULT_PERSONALISATION_CONFIG = PersonalisationConfig(
    config_version=STATISTICS_PERSONALISATION_CONFIG_VERSION,
    location_prior_pseudo_count=5.0,
    dispersion_prior_pseudo_count=30.0,
    dispersion_min_effective_observations=2.0,
    correlation_prior_pseudo_count=60.0,
    correlation_min_effective_observations=40.0,
)


def _update_location(
    prior_value: float, observations: WeightedObservations, prior_pseudo_count: float
) -> tuple[float, DimensionUpdateOutcome, float]:
    """Pool ``prior_value`` with ``observations``' weighted mean; no evidence-count gate."""
    n = sum(observations.weights)
    if n == 0.0:
        return prior_value, DimensionUpdateOutcome.NO_EVIDENCE, n

    weighted_mean = (
        sum(v * w for v, w in zip(observations.values, observations.weights, strict=True)) / n
    )
    posterior = (prior_pseudo_count * prior_value + n * weighted_mean) / (prior_pseudo_count + n)
    return posterior, DimensionUpdateOutcome.UPDATED, n


def _update_scale(
    prior_scale: float,
    observations: WeightedObservations,
    prior_pseudo_count: float,
    min_effective_observations: float,
    factor: float,
) -> tuple[float, DimensionUpdateOutcome, float]:
    """Pool ``prior_scale`` (converted to variance via ``factor``) with the weighted sample
    variance of ``observations``, gated by ``min_effective_observations``."""
    n = sum(observations.weights)
    if n == 0.0:
        return prior_scale, DimensionUpdateOutcome.NO_EVIDENCE, n
    if n < min_effective_observations:
        return prior_scale, DimensionUpdateOutcome.INSUFFICIENT_EVIDENCE, n

    weighted_mean = (
        sum(v * w for v, w in zip(observations.values, observations.weights, strict=True)) / n
    )
    sample_variance = (
        sum(
            w * (v - weighted_mean) ** 2
            for v, w in zip(observations.values, observations.weights, strict=True)
        )
        / n
    )
    prior_variance = factor * prior_scale**2
    posterior_variance = (prior_pseudo_count * prior_variance + n * sample_variance) / (
        prior_pseudo_count + n
    )
    posterior_scale = math.sqrt(posterior_variance / factor)
    return posterior_scale, DimensionUpdateOutcome.UPDATED, n


def _update_correlation(
    prior_correlation: float,
    joint: WeightedJointObservations,
    prior_pseudo_count: float,
    min_effective_observations: float,
) -> tuple[float, DimensionUpdateOutcome, float]:
    """Pool ``prior_correlation`` with a weighted Pearson correlation of ``joint``, gated by
    ``min_effective_observations`` and guarded against near-zero-variance legs."""
    n = sum(joint.weights)
    if n == 0.0:
        return prior_correlation, DimensionUpdateOutcome.NO_EVIDENCE, n
    if n < min_effective_observations:
        return prior_correlation, DimensionUpdateOutcome.INSUFFICIENT_EVIDENCE, n

    mean_carry = sum(c * w for c, w in zip(joint.carry_values, joint.weights, strict=True)) / n
    mean_lateral = (
        sum(lat * w for lat, w in zip(joint.lateral_values, joint.weights, strict=True)) / n
    )
    var_carry = (
        sum(
            w * (c - mean_carry) ** 2
            for c, w in zip(joint.carry_values, joint.weights, strict=True)
        )
        / n
    )
    var_lateral = (
        sum(
            w * (lat - mean_lateral) ** 2
            for lat, w in zip(joint.lateral_values, joint.weights, strict=True)
        )
        / n
    )
    if var_carry < _NEAR_ZERO_VARIANCE or var_lateral < _NEAR_ZERO_VARIANCE:
        return prior_correlation, DimensionUpdateOutcome.INSUFFICIENT_EVIDENCE, n

    covariance = (
        sum(
            w * (c - mean_carry) * (lat - mean_lateral)
            for c, lat, w in zip(
                joint.carry_values, joint.lateral_values, joint.weights, strict=True
            )
        )
        / n
    )
    sample_correlation = covariance / math.sqrt(var_carry * var_lateral)
    clipped_correlation = max(
        -_CORRELATION_CLIP_BOUND, min(_CORRELATION_CLIP_BOUND, sample_correlation)
    )
    posterior = (prior_pseudo_count * prior_correlation + n * clipped_correlation) / (
        prior_pseudo_count + n
    )
    return posterior, DimensionUpdateOutcome.UPDATED, n


def shrink_shot_distribution(
    baseline_distribution: PlayerShotDistribution,
    *,
    carry_observations: WeightedObservations,
    lateral_observations: WeightedObservations,
    joint_observations: WeightedJointObservations,
    config: PersonalisationConfig = DEFAULT_PERSONALISATION_CONFIG,
) -> ShotDistributionUpdateResult:
    """Partial-pooling (empirical-Bayes-style shrinkage) update of ``baseline_distribution``
    toward evidence.

    Raises ``NotImplementedError`` if ``baseline_distribution.family`` is not
    ``ShotDistributionFamily.BIVARIATE_STUDENT_T`` — a future family would
    need its own shrinkage math, not this one silently misapplied. See the
    module docstring for the exact per-dimension formulas and gating.

    ``baseline_distribution`` must always be the same immutable cold-start
    distribution — the golfer's population-prior or onboarding-derived
    ``PlayerShotDistribution`` — and never a previously-returned
    ``ShotDistributionUpdateResult.shot_distribution``. This function
    recomputes the posterior from scratch on every call (batch
    recomputation); it does not accumulate sufficient statistics across
    calls. Callers must rebuild ``carry_observations``/``lateral_observations``/
    ``joint_observations`` from the *complete* current eligible evidence set
    each time, paired with the same fixed baseline — never with a prior call's
    own output — or evidence will be silently double-counted. See
    ``caddai.player.personalisation.update_shot_distribution_from_history``
    for the concrete misuse example.
    """
    if baseline_distribution.family is not ShotDistributionFamily.BIVARIATE_STUDENT_T:
        raise NotImplementedError(
            f"shrink_shot_distribution does not support family {baseline_distribution.family!r}"
        )

    factor = baseline_distribution.degrees_of_freedom / (
        baseline_distribution.degrees_of_freedom - 2.0
    )

    carry_location, carry_location_outcome, carry_location_n = _update_location(
        baseline_distribution.carry_location_metres,
        carry_observations,
        config.location_prior_pseudo_count,
    )
    lateral_bias, lateral_bias_outcome, lateral_bias_n = _update_location(
        baseline_distribution.lateral_bias_metres,
        lateral_observations,
        config.location_prior_pseudo_count,
    )
    carry_scale, carry_scale_outcome, carry_scale_n = _update_scale(
        baseline_distribution.carry_scale_metres,
        carry_observations,
        config.dispersion_prior_pseudo_count,
        config.dispersion_min_effective_observations,
        factor,
    )
    lateral_scale, lateral_scale_outcome, lateral_scale_n = _update_scale(
        baseline_distribution.lateral_scale_metres,
        lateral_observations,
        config.dispersion_prior_pseudo_count,
        config.dispersion_min_effective_observations,
        factor,
    )
    correlation, correlation_outcome, correlation_n = _update_correlation(
        baseline_distribution.correlation,
        joint_observations,
        config.correlation_prior_pseudo_count,
        config.correlation_min_effective_observations,
    )

    shot_distribution = PlayerShotDistribution(
        family=baseline_distribution.family,
        carry_location_metres=carry_location,
        lateral_bias_metres=lateral_bias,
        carry_scale_metres=carry_scale,
        lateral_scale_metres=lateral_scale,
        correlation=correlation,
        degrees_of_freedom=baseline_distribution.degrees_of_freedom,
    )

    return ShotDistributionUpdateResult(
        shot_distribution=shot_distribution,
        config_version=config.config_version,
        carry_location_effective_n=carry_location_n,
        carry_location_outcome=carry_location_outcome,
        lateral_bias_effective_n=lateral_bias_n,
        lateral_bias_outcome=lateral_bias_outcome,
        carry_scale_effective_n=carry_scale_n,
        carry_scale_outcome=carry_scale_outcome,
        lateral_scale_effective_n=lateral_scale_n,
        lateral_scale_outcome=lateral_scale_outcome,
        correlation_effective_n=correlation_n,
        correlation_outcome=correlation_outcome,
        degrees_of_freedom_outcome=DimensionUpdateOutcome.HELD_FIXED_BY_POLICY,
    )
