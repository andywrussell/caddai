"""Tests for the pure partial-pooling shrinkage math in ``caddai.statistics.personalisation``.

See GitHub issue #53 ("M4.5 — Personal partial-pooling player-model
updater") and docs/plans/m4.5-personal-partial-pooling-updater.plan.md for
the acceptance criteria and exact shrinkage formulas these tests are
derived from, and ADR 0006
(docs/adr/0006-player-shot-distribution-bivariate-student-t.md) for the
underlying bivariate Student-t construction (``factor = nu / (nu - 2)``,
scale != stddev).

This module is written before ``caddai.statistics.personalisation`` exists
(TDD executable spec) — every test here is expected to fail with an
``ImportError`` until the Player Engineer implements it. This module tests
only the pure statistics-side math (``shrink_shot_distribution``,
``PersonalisationConfig``, ``WeightedObservations``,
``WeightedJointObservations``, ``DimensionUpdateOutcome``). The
``ShotRecord`` -> arrays glue is tested separately in
tests/test_player_personalisation.py.

Per the plan, most assertions here are deliberately qualitative/structural
(posterior lies strictly between prior and sample, monotonic convergence
with increasing evidence, values held exactly at the prior below an
evidence gate) rather than pinned to exact numeric outputs, so tests remain
valid across reasonable recalibration of ``DEFAULT_PERSONALISATION_CONFIG``.
A small number of precise arithmetic tests exist for the location formula,
which the plan states exactly and unambiguously.
"""

import math

import pytest
from pydantic import ValidationError

from caddai.statistics.personalisation import (
    DEFAULT_PERSONALISATION_CONFIG,
    STATISTICS_PERSONALISATION_CONFIG_VERSION,
    DimensionUpdateOutcome,
    PersonalisationConfig,
    WeightedJointObservations,
    WeightedObservations,
    shrink_shot_distribution,
)
from caddai.statistics.shot_distribution import PlayerShotDistribution

# --- Helpers -----------------------------------------------------------------


def _prior(**overrides: float) -> PlayerShotDistribution:
    """Baseline valid ``PlayerShotDistribution`` to shrink against."""
    kwargs: dict[str, float] = {
        "carry_location_metres": 140.0,
        "lateral_bias_metres": 1.0,
        "carry_scale_metres": 8.0,
        "lateral_scale_metres": 4.0,
        "correlation": 0.1,
        "degrees_of_freedom": 6.0,
    }
    kwargs.update(overrides)
    return PlayerShotDistribution(**kwargs)


def _obs(values: list[float], weights: list[float] | None = None) -> WeightedObservations:
    if weights is None:
        weights = [1.0] * len(values)
    return WeightedObservations(values=tuple(values), weights=tuple(weights))


def _joint(
    carry_values: list[float],
    lateral_values: list[float],
    weights: list[float] | None = None,
) -> WeightedJointObservations:
    if weights is None:
        weights = [1.0] * len(carry_values)
    return WeightedJointObservations(
        carry_values=tuple(carry_values),
        lateral_values=tuple(lateral_values),
        weights=tuple(weights),
    )


def _weighted_mean(values: list[float], weights: list[float]) -> float:
    total_weight = sum(weights)
    return sum(v * w for v, w in zip(values, weights, strict=True)) / total_weight


def _config_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "config_version": "test-v1",
        "location_prior_pseudo_count": 5.0,
        "dispersion_prior_pseudo_count": 30.0,
        "dispersion_min_effective_observations": 2.0,
        "correlation_prior_pseudo_count": 60.0,
        "correlation_min_effective_observations": 40.0,
    }
    kwargs.update(overrides)
    return kwargs


_POSITIVE_NUMERIC_CONFIG_FIELDS = [
    "location_prior_pseudo_count",
    "dispersion_prior_pseudo_count",
    "dispersion_min_effective_observations",
    "correlation_prior_pseudo_count",
    "correlation_min_effective_observations",
]


# --- PersonalisationConfig validation -----------------------------------------


def test_config_constructs_with_typical_values() -> None:
    """A physically plausible config with all-positive pseudo-counts/thresholds is accepted."""
    config = PersonalisationConfig(**_config_kwargs())

    assert config.location_prior_pseudo_count == pytest.approx(5.0)
    assert config.dispersion_prior_pseudo_count == pytest.approx(30.0)
    assert config.dispersion_min_effective_observations == pytest.approx(2.0)
    assert config.correlation_prior_pseudo_count == pytest.approx(60.0)
    assert config.correlation_min_effective_observations == pytest.approx(40.0)


@pytest.mark.parametrize("field_name", _POSITIVE_NUMERIC_CONFIG_FIELDS)
@pytest.mark.parametrize("bad_value", [0.0, -1.0, -100.0])
def test_config_rejects_non_positive_fields(field_name: str, bad_value: float) -> None:
    """Every numeric config field must be strictly > 0 per the plan."""
    with pytest.raises(ValidationError):
        PersonalisationConfig(**_config_kwargs(**{field_name: bad_value}))


@pytest.mark.parametrize("field_name", _POSITIVE_NUMERIC_CONFIG_FIELDS)
@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
def test_config_rejects_non_finite_fields(field_name: str, bad_value: float) -> None:
    """NaN/+inf/-inf are rejected even though +inf incidentally satisfies a ``gt=0`` bound."""
    with pytest.raises(ValidationError):
        PersonalisationConfig(**_config_kwargs(**{field_name: bad_value}))


def test_default_config_version_matches_module_constant() -> None:
    """``DEFAULT_PERSONALISATION_CONFIG`` echoes ``STATISTICS_PERSONALISATION_CONFIG_VERSION``."""
    assert (
        DEFAULT_PERSONALISATION_CONFIG.config_version == STATISTICS_PERSONALISATION_CONFIG_VERSION
    )


def test_default_config_values_are_all_positive() -> None:
    """The illustrative default config values are all valid (> 0), not just present."""
    assert DEFAULT_PERSONALISATION_CONFIG.location_prior_pseudo_count > 0.0
    assert DEFAULT_PERSONALISATION_CONFIG.dispersion_prior_pseudo_count > 0.0
    assert DEFAULT_PERSONALISATION_CONFIG.dispersion_min_effective_observations > 0.0
    assert DEFAULT_PERSONALISATION_CONFIG.correlation_prior_pseudo_count > 0.0
    assert DEFAULT_PERSONALISATION_CONFIG.correlation_min_effective_observations > 0.0


# --- WeightedObservations / WeightedJointObservations validation -------------


def test_weighted_observations_accepts_matching_lengths() -> None:
    obs = WeightedObservations(values=(1.0, 2.0), weights=(0.5, 1.0))

    assert obs.values == (1.0, 2.0)
    assert obs.weights == (0.5, 1.0)


def test_weighted_observations_accepts_empty_sequences() -> None:
    """Empty observations (no evidence at all) must be constructible, not just non-empty ones."""
    obs = WeightedObservations(values=(), weights=())

    assert obs.values == ()
    assert obs.weights == ()


def test_weighted_observations_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValidationError):
        WeightedObservations(values=(1.0, 2.0), weights=(1.0,))


@pytest.mark.parametrize("weight", [-1.0, -0.0001])
def test_weighted_observations_rejects_negative_weight(weight: float) -> None:
    with pytest.raises(ValidationError):
        WeightedObservations(values=(1.0,), weights=(weight,))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_weighted_observations_rejects_non_finite_value(value: float) -> None:
    with pytest.raises(ValidationError):
        WeightedObservations(values=(value,), weights=(1.0,))


@pytest.mark.parametrize("weight", [float("nan"), float("inf")])
def test_weighted_observations_rejects_non_finite_weight(weight: float) -> None:
    with pytest.raises(ValidationError):
        WeightedObservations(values=(1.0,), weights=(weight,))


def test_weighted_joint_observations_accepts_matching_lengths() -> None:
    joint = WeightedJointObservations(
        carry_values=(150.0, 160.0), lateral_values=(1.0, -1.0), weights=(1.0, 0.5)
    )

    assert joint.carry_values == (150.0, 160.0)
    assert joint.lateral_values == (1.0, -1.0)
    assert joint.weights == (1.0, 0.5)


def test_weighted_joint_observations_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValidationError):
        WeightedJointObservations(
            carry_values=(1.0, 2.0), lateral_values=(1.0,), weights=(1.0, 1.0)
        )


@pytest.mark.parametrize("weight", [-1.0, -0.0001])
def test_weighted_joint_observations_rejects_negative_weight(weight: float) -> None:
    with pytest.raises(ValidationError):
        WeightedJointObservations(carry_values=(1.0,), lateral_values=(1.0,), weights=(weight,))


# --- shrink_shot_distribution: no evidence at all -----------------------------


def test_no_observations_leaves_distribution_unchanged_with_no_evidence_outcomes() -> None:
    """With zero evidence everywhere, every field is retained exactly, all outcomes NO_EVIDENCE
    (except degrees_of_freedom, which is always HELD_FIXED_BY_POLICY)."""
    prior = _prior()

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([]),
        lateral_observations=_obs([]),
        joint_observations=_joint([], []),
        config=DEFAULT_PERSONALISATION_CONFIG,
    )

    assert result.shot_distribution == prior
    assert result.carry_location_outcome is DimensionUpdateOutcome.NO_EVIDENCE
    assert result.lateral_bias_outcome is DimensionUpdateOutcome.NO_EVIDENCE
    assert result.carry_scale_outcome is DimensionUpdateOutcome.NO_EVIDENCE
    assert result.lateral_scale_outcome is DimensionUpdateOutcome.NO_EVIDENCE
    assert result.correlation_outcome is DimensionUpdateOutcome.NO_EVIDENCE
    assert result.degrees_of_freedom_outcome is DimensionUpdateOutcome.HELD_FIXED_BY_POLICY
    assert result.carry_location_effective_n == pytest.approx(0.0)
    assert result.carry_scale_effective_n == pytest.approx(0.0)
    assert result.lateral_bias_effective_n == pytest.approx(0.0)
    assert result.lateral_scale_effective_n == pytest.approx(0.0)
    assert result.correlation_effective_n == pytest.approx(0.0)


# --- Unsupported family guard --------------------------------------------------


def test_raises_not_implemented_for_unsupported_family() -> None:
    """A non-bivariate-Student-t family (constructed via model_copy to bypass the enum's
    current single member) must raise NotImplementedError, not silently proceed."""
    prior = _prior().model_copy(update={"family": "unsupported_family"})

    with pytest.raises(NotImplementedError):
        shrink_shot_distribution(
            prior,
            carry_observations=_obs([150.0]),
            lateral_observations=_obs([1.0]),
            joint_observations=_joint([150.0], [1.0]),
        )


# --- Location: exact formula, partial movement, monotonic convergence --------


def test_location_matches_exact_pooling_formula() -> None:
    """The location formula is stated exactly by the plan, so it can be checked precisely."""
    prior = _prior(carry_location_metres=140.0)
    values = [150.0, 152.0, 148.0]
    weights = [1.0, 0.6, 1.0]

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs(values, weights),
        lateral_observations=_obs([]),
        joint_observations=_joint([], []),
        config=DEFAULT_PERSONALISATION_CONFIG,
    )

    n = sum(weights)
    weighted_mean = _weighted_mean(values, weights)
    location_prior_pseudo_count = DEFAULT_PERSONALISATION_CONFIG.location_prior_pseudo_count
    expected = (location_prior_pseudo_count * 140.0 + n * weighted_mean) / (
        location_prior_pseudo_count + n
    )

    assert result.shot_distribution.carry_location_metres == pytest.approx(expected)
    assert result.carry_location_outcome is DimensionUpdateOutcome.UPDATED
    assert result.carry_location_effective_n == pytest.approx(n)


def test_single_observation_moves_location_partially_not_fully() -> None:
    """One observation should shrink the location toward the sample, not replace it outright."""
    prior = _prior(carry_location_metres=140.0)
    sample_value = 200.0

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([sample_value]),
        lateral_observations=_obs([]),
        joint_observations=_joint([], []),
    )

    posterior = result.shot_distribution.carry_location_metres
    assert prior.carry_location_metres < posterior < sample_value
    assert result.carry_location_outcome is DimensionUpdateOutcome.UPDATED


def test_increasing_observation_count_moves_location_monotonically_closer_to_sample() -> None:
    prior = _prior(carry_location_metres=140.0)
    sample_value = 200.0

    distances = [
        abs(
            shrink_shot_distribution(
                prior,
                carry_observations=_obs([sample_value] * n),
                lateral_observations=_obs([]),
                joint_observations=_joint([], []),
            ).shot_distribution.carry_location_metres
            - sample_value
        )
        for n in (1, 5, 25, 100)
    ]

    assert distances == sorted(distances, reverse=True)
    assert distances[-1] < distances[0]


def test_zero_weight_sum_carry_location_is_no_evidence() -> None:
    """Observations present but summing to zero weight (e.g. all UNKNOWN-quality) behave
    identically to no observations at all: NO_EVIDENCE, value unchanged."""
    prior = _prior(carry_location_metres=140.0)

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([999.0], weights=[0.0]),
        lateral_observations=_obs([]),
        joint_observations=_joint([], []),
    )

    assert result.carry_location_outcome is DimensionUpdateOutcome.NO_EVIDENCE
    assert result.shot_distribution.carry_location_metres == pytest.approx(
        prior.carry_location_metres
    )


# --- Lateral bias: signed evidence, sufficient evidence supersedes bias -------


def test_lateral_bias_accepts_negative_and_positive_evidence() -> None:
    prior = _prior(lateral_bias_metres=0.0)

    left_result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([]),
        lateral_observations=_obs([-10.0] * 5),
        joint_observations=_joint([], []),
    )
    right_result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([]),
        lateral_observations=_obs([10.0] * 5),
        joint_observations=_joint([], []),
    )

    assert left_result.shot_distribution.lateral_bias_metres < 0.0
    assert right_result.shot_distribution.lateral_bias_metres > 0.0


def test_sufficient_contradicting_lateral_evidence_moves_bias_past_zero() -> None:
    """A strong existing positive (RIGHT) bias can be moved negative given enough
    contradicting evidence — bias is not a permanent fixture once evidence disagrees."""
    prior = _prior(lateral_bias_metres=5.0)

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([]),
        lateral_observations=_obs([-20.0] * 200),
        joint_observations=_joint([], []),
    )

    assert result.shot_distribution.lateral_bias_metres < 0.0


# --- Scale: gating, exact-threshold boundary, and scale/covariance conversion -


def test_one_observation_never_moves_carry_scale_and_reports_insufficient_evidence() -> None:
    prior = _prior(carry_scale_metres=8.0)

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([300.0]),
        lateral_observations=_obs([]),
        joint_observations=_joint([], []),
    )

    assert result.carry_scale_outcome is DimensionUpdateOutcome.INSUFFICIENT_EVIDENCE
    assert result.shot_distribution.carry_scale_metres == pytest.approx(prior.carry_scale_metres)


def test_scale_just_below_threshold_is_insufficient_evidence() -> None:
    """With the default config's dispersion_min_effective_observations == 2.0, n == 1.9 is
    below the gate — INSUFFICIENT_EVIDENCE, prior kept exactly."""
    prior = _prior(carry_scale_metres=8.0)

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([130.0, 150.0], weights=[0.95, 0.95]),
        lateral_observations=_obs([]),
        joint_observations=_joint([], []),
        config=DEFAULT_PERSONALISATION_CONFIG,
    )

    assert result.carry_scale_outcome is DimensionUpdateOutcome.INSUFFICIENT_EVIDENCE
    assert result.shot_distribution.carry_scale_metres == pytest.approx(prior.carry_scale_metres)


def test_scale_at_exact_threshold_is_updated() -> None:
    """The gate is a strict less-than (n < threshold), so n == threshold exactly updates."""
    prior = _prior(carry_scale_metres=8.0)

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([130.0, 150.0], weights=[1.0, 1.0]),
        lateral_observations=_obs([]),
        joint_observations=_joint([], []),
        config=DEFAULT_PERSONALISATION_CONFIG,
    )

    assert result.carry_scale_outcome is DimensionUpdateOutcome.UPDATED
    assert result.shot_distribution.carry_scale_metres != pytest.approx(prior.carry_scale_metres)


def test_large_sample_scale_converges_toward_variance_over_nu_factor_not_raw_variance() -> None:
    """The critical Student-t scale-vs-covariance test: with nu=6 (factor=1.5) and a huge,
    perfectly-alternating +-d sample (population variance exactly d^2), the posterior scale
    must approach sqrt(d^2 / factor), not sqrt(d^2) — a stddev/scale mix-up would fail this."""
    nu = 6.0
    prior = _prior(carry_scale_metres=8.0, degrees_of_freedom=nu)
    d = 20.0
    n = 4000
    values = [d if i % 2 == 0 else -d for i in range(n)]

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs(values),
        lateral_observations=_obs([]),
        joint_observations=_joint([], []),
    )

    factor = nu / (nu - 2.0)
    expected_scale_correct = math.sqrt(d**2 / factor)
    expected_scale_if_mistaken_for_stddev = d

    posterior_scale = result.shot_distribution.carry_scale_metres
    assert posterior_scale == pytest.approx(expected_scale_correct, rel=0.05)
    assert posterior_scale != pytest.approx(expected_scale_if_mistaken_for_stddev, rel=0.02)


def test_increasing_sample_size_moves_scale_monotonically_toward_sample() -> None:
    prior = _prior(carry_scale_metres=8.0)
    sample_half_range = 20.0

    distances = []
    for n in (2, 10, 100, 1000):
        values = [sample_half_range if i % 2 == 0 else -sample_half_range for i in range(n)]
        result = shrink_shot_distribution(
            prior,
            carry_observations=_obs(values),
            lateral_observations=_obs([]),
            joint_observations=_joint([], []),
        )
        posterior_scale = result.shot_distribution.carry_scale_metres
        distances.append(abs(posterior_scale - sample_half_range))

    assert distances == sorted(distances, reverse=True)


def test_lateral_scale_gating_mirrors_carry_scale_gating() -> None:
    prior = _prior(lateral_scale_metres=4.0)

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([]),
        lateral_observations=_obs([25.0]),
        joint_observations=_joint([], []),
    )

    assert result.lateral_scale_outcome is DimensionUpdateOutcome.INSUFFICIENT_EVIDENCE
    assert result.shot_distribution.lateral_scale_metres == pytest.approx(
        prior.lateral_scale_metres
    )


# --- Correlation: hard gate, exact-threshold boundary, shrinkage -------------


def test_correlation_below_gate_leaves_prior_unchanged() -> None:
    """Below the default correlation_min_effective_observations (40.0), even a strongly
    correlated sample must not move correlation at all."""
    prior = _prior(correlation=0.1)
    n_below_gate = 39
    carry_values = [140.0 + i for i in range(n_below_gate)]
    lateral_values = [1.0 * i for i in range(n_below_gate)]

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([]),
        lateral_observations=_obs([]),
        joint_observations=_joint(carry_values, lateral_values),
        config=DEFAULT_PERSONALISATION_CONFIG,
    )

    assert result.correlation_outcome is DimensionUpdateOutcome.INSUFFICIENT_EVIDENCE
    assert result.shot_distribution.correlation == pytest.approx(prior.correlation)


def test_correlation_at_exact_gate_is_updated() -> None:
    prior = _prior(correlation=0.1)
    n_at_gate = 40
    carry_values = [140.0 + i for i in range(n_at_gate)]
    lateral_values = [1.0 * i for i in range(n_at_gate)]

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([]),
        lateral_observations=_obs([]),
        joint_observations=_joint(carry_values, lateral_values),
        config=DEFAULT_PERSONALISATION_CONFIG,
    )

    assert result.correlation_outcome is DimensionUpdateOutcome.UPDATED
    assert result.shot_distribution.correlation != pytest.approx(prior.correlation)


def test_correlation_update_is_shrunk_toward_sample_not_fully_replaced() -> None:
    """A perfectly-correlated (correlation == 1) large sample must still be pooled with the
    prior, landing strictly inside (prior_correlation, 1), never exactly at either bound."""
    prior = _prior(correlation=0.0)
    n = 200
    carry_values = [140.0 + (i - n / 2) * 0.5 for i in range(n)]
    lateral_values = list(carry_values)

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([]),
        lateral_observations=_obs([]),
        joint_observations=_joint(carry_values, lateral_values),
    )

    assert 0.0 < result.shot_distribution.correlation < 1.0


def test_two_observations_never_collapse_correlation_toward_sample() -> None:
    prior = _prior(correlation=0.1)

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([]),
        lateral_observations=_obs([]),
        joint_observations=_joint([140.0, 160.0], [-5.0, 5.0]),
    )

    assert result.correlation_outcome is DimensionUpdateOutcome.INSUFFICIENT_EVIDENCE
    assert result.shot_distribution.correlation == pytest.approx(prior.correlation)


# --- Degrees of freedom: always retained, never estimated ---------------------


def test_degrees_of_freedom_always_held_fixed_regardless_of_evidence_volume() -> None:
    prior = _prior(degrees_of_freedom=6.0)

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([300.0] * 500),
        lateral_observations=_obs([50.0] * 500),
        joint_observations=_joint([300.0] * 500, [50.0] * 500),
    )

    assert result.degrees_of_freedom_outcome is DimensionUpdateOutcome.HELD_FIXED_BY_POLICY
    assert result.shot_distribution.degrees_of_freedom == pytest.approx(prior.degrees_of_freedom)


# --- Effective-n bookkeeping ----------------------------------------------------


def test_effective_n_fields_equal_sum_of_weights_per_dimension() -> None:
    prior = _prior()
    carry_obs = _obs([150.0, 160.0], [1.0, 0.5])
    lateral_obs = _obs([1.0, -1.0, 2.0], [1.0, 1.0, 0.25])
    joint_obs = _joint([150.0, 160.0], [1.0, -1.0], [1.0, 0.5])

    result = shrink_shot_distribution(
        prior,
        carry_observations=carry_obs,
        lateral_observations=lateral_obs,
        joint_observations=joint_obs,
    )

    assert result.carry_location_effective_n == pytest.approx(1.5)
    assert result.carry_scale_effective_n == pytest.approx(1.5)
    assert result.lateral_bias_effective_n == pytest.approx(2.25)
    assert result.lateral_scale_effective_n == pytest.approx(2.25)
    assert result.correlation_effective_n == pytest.approx(1.5)


# --- Config version echoing ------------------------------------------------------


def test_result_echoes_supplied_config_version() -> None:
    custom_config = PersonalisationConfig(**_config_kwargs(config_version="custom-v7"))
    prior = _prior()

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([150.0]),
        lateral_observations=_obs([]),
        joint_observations=_joint([], []),
        config=custom_config,
    )

    assert result.config_version == "custom-v7"


def test_default_config_used_when_not_specified() -> None:
    prior = _prior()

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([150.0]),
        lateral_observations=_obs([]),
        joint_observations=_joint([], []),
    )

    assert result.config_version == STATISTICS_PERSONALISATION_CONFIG_VERSION


# --- Determinism ----------------------------------------------------------------


def test_identical_inputs_produce_identical_results() -> None:
    """No randomness anywhere: calling twice with identical inputs must be exactly equal."""
    prior = _prior()
    carry_obs = _obs([150.0, 160.0, 145.0], [1.0, 0.6, 0.25])
    lateral_obs = _obs([2.0, -1.0, 0.5], [1.0, 0.6, 0.25])
    joint_obs = _joint([150.0, 160.0], [2.0, -1.0], [1.0, 0.6])

    result_a = shrink_shot_distribution(
        prior,
        carry_observations=carry_obs,
        lateral_observations=lateral_obs,
        joint_observations=joint_obs,
    )
    result_b = shrink_shot_distribution(
        prior,
        carry_observations=carry_obs,
        lateral_observations=lateral_obs,
        joint_observations=joint_obs,
    )

    assert result_a == result_b


# --- Invariant protection / adversarial evidence --------------------------------


def test_near_degenerate_evidence_still_yields_a_valid_distribution() -> None:
    """A large, near-zero-variance, near-perfectly-correlated evidence set must still
    produce a PlayerShotDistribution satisfying all of its own Pydantic invariants."""
    prior = _prior()
    n = 300
    carry_values = [140.0 + (i % 2) * 1e-6 for i in range(n)]
    lateral_values = [(i % 2) * 1e-6 for i in range(n)]

    result = shrink_shot_distribution(
        prior,
        carry_observations=_obs(carry_values),
        lateral_observations=_obs(lateral_values),
        joint_observations=_joint(carry_values, lateral_values),
    )

    distribution = result.shot_distribution
    assert distribution.carry_scale_metres > 0.0
    assert distribution.lateral_scale_metres > 0.0
    assert -1.0 < distribution.correlation < 1.0
    assert distribution.degrees_of_freedom > 2.0
    assert math.isfinite(distribution.carry_location_metres)
    assert math.isfinite(distribution.lateral_bias_metres)


def test_severe_outlier_carry_value_pulls_posterior_and_is_not_excluded() -> None:
    """A genuinely severe (very short) carry observation must visibly pull the posterior
    location down, proving it was used, not filtered out as an outlier."""
    prior = _prior(carry_location_metres=140.0)
    normal_values = [140.0] * 20
    severe_short_shot = 40.0

    baseline_result = shrink_shot_distribution(
        prior,
        carry_observations=_obs(normal_values),
        lateral_observations=_obs([]),
        joint_observations=_joint([], []),
    )
    with_outlier_result = shrink_shot_distribution(
        prior,
        carry_observations=_obs([*normal_values, severe_short_shot]),
        lateral_observations=_obs([]),
        joint_observations=_joint([], []),
    )

    assert (
        with_outlier_result.shot_distribution.carry_location_metres
        < baseline_result.shot_distribution.carry_location_metres
    )
