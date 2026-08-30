"""Tests for the M4.8 seeded bivariate Student-t shot-outcome sampler (``caddai.simulation``).

See GitHub issue #56 ("M4.8 — Seeded probabilistic shot-outcome simulation")
and docs/plans/m4.8-seeded-shot-outcome-simulation.plan.md for the
acceptance criteria/Architect design these tests are derived from, and ADR
0006 (docs/adr/0006-player-shot-distribution-bivariate-student-t.md) for the
underlying ``X = mu + Z / sqrt(W/nu)`` construction.

Written against ``sample_bivariate_student_t_shot_outcomes``/
``ShotOutcomeSampler`` before ``src/caddai/simulation/sampling.py`` exists
(QA writes the executable spec first, matching the M4.7 precedent) — these
tests are expected to fail with an import error until the Strategy Engineer
implements Task 2 of the plan.

Statistical tests follow issue #56/tests.instructions.md exactly: every
stochastic test uses an explicitly seeded ``np.random.default_rng(<int>)``,
large sample sizes, and generous, non-flaky tolerances — never an exact
match against a theoretical value or a specific NumPy RNG bit sequence.

Architecture-boundary coverage (``sampling.py`` added to the ``simulation``
``SubsystemBoundary``) lives in ``tests/test_architecture_boundaries.py``
and is updated alongside the Task 2 implementation, not duplicated here.
"""

import math

import numpy as np
import pytest

from caddai.simulation import (
    EnvironmentInput,
    ShotOutcome,
    ShotOutcomeSampler,
    WindComponents,
    apply_environment_transform,
    sample_bivariate_student_t_shot_outcomes,
)
from caddai.statistics.shot_distribution import PlayerShotDistribution

# A generic, moderate-tail distribution used by tests that don't need a
# specific correlation/nu/location to make their point.
BASE_DISTRIBUTION = PlayerShotDistribution(
    carry_location_metres=150.0,
    lateral_bias_metres=2.0,
    carry_scale_metres=10.0,
    lateral_scale_metres=5.0,
    correlation=0.3,
    degrees_of_freedom=8.0,
)


# --- Valid shapes/counts, all finite ------------------------------------------


def test_single_sample_returns_one_finite_shot_outcome() -> None:
    """count=1 returns a 1-tuple of a finite ShotOutcome."""
    result = sample_bivariate_student_t_shot_outcomes(
        BASE_DISTRIBUTION, count=1, rng=np.random.default_rng(1)
    )

    assert len(result) == 1
    assert isinstance(result[0], ShotOutcome)
    assert math.isfinite(result[0].downrange_metres)
    assert math.isfinite(result[0].lateral_metres)


def test_large_batch_returns_correct_count_all_finite() -> None:
    """A large count returns exactly that many finite ShotOutcomes."""
    count = 10_000
    result = sample_bivariate_student_t_shot_outcomes(
        BASE_DISTRIBUTION, count=count, rng=np.random.default_rng(2)
    )

    assert len(result) == count
    assert all(isinstance(o, ShotOutcome) for o in result)
    assert all(
        math.isfinite(o.downrange_metres) and math.isfinite(o.lateral_metres) for o in result
    )


# --- Seeding / determinism / independence -------------------------------------


def test_same_seed_and_inputs_give_identical_output() -> None:
    """Two calls built from identically-seeded, separately-constructed generators match exactly."""
    result1 = sample_bivariate_student_t_shot_outcomes(
        BASE_DISTRIBUTION, count=50, rng=np.random.default_rng(2024)
    )
    result2 = sample_bivariate_student_t_shot_outcomes(
        BASE_DISTRIBUTION, count=50, rng=np.random.default_rng(2024)
    )

    assert result1 == result2


def test_different_seeds_give_different_output() -> None:
    """Two different seeds produce a different output (no assertion beyond inequality)."""
    result1 = sample_bivariate_student_t_shot_outcomes(
        BASE_DISTRIBUTION, count=50, rng=np.random.default_rng(1)
    )
    result2 = sample_bivariate_student_t_shot_outcomes(
        BASE_DISTRIBUTION, count=50, rng=np.random.default_rng(2)
    )

    assert result1 != result2


def test_omitted_seed_varies_across_independently_constructed_generators() -> None:
    """Two unseeded generators produce different output (each draws fresh entropy)."""
    result1 = sample_bivariate_student_t_shot_outcomes(
        BASE_DISTRIBUTION, count=50, rng=np.random.default_rng()
    )
    result2 = sample_bivariate_student_t_shot_outcomes(
        BASE_DISTRIBUTION, count=50, rng=np.random.default_rng()
    )

    assert result1 != result2


def test_no_global_numpy_random_state_mutated() -> None:
    """The legacy global NumPy random state is untouched by a seeded Generator call."""
    before = np.random.get_state()
    sample_bivariate_student_t_shot_outcomes(
        BASE_DISTRIBUTION, count=1_000, rng=np.random.default_rng(51)
    )
    after = np.random.get_state()

    assert before[0] == after[0]
    assert np.array_equal(before[1], after[1])
    assert before[2] == after[2]
    assert before[3] == after[3]
    assert before[4] == after[4]


def test_unrelated_generator_instance_unaffected_by_another_generators_call() -> None:
    """A seeded generator's output is unaffected by an unrelated generator instance's prior use."""
    probe_before = sample_bivariate_student_t_shot_outcomes(
        BASE_DISTRIBUTION, count=5, rng=np.random.default_rng(777)
    )
    # Unrelated call, different Generator instance, large count.
    sample_bivariate_student_t_shot_outcomes(
        BASE_DISTRIBUTION, count=10_000, rng=np.random.default_rng(42)
    )
    probe_after = sample_bivariate_student_t_shot_outcomes(
        BASE_DISTRIBUTION, count=5, rng=np.random.default_rng(777)
    )

    assert probe_before == probe_after


def test_player_shot_distribution_construction_performs_no_random_work() -> None:
    """Building a PlayerShotDistribution touches no NumPy random state at all."""
    before = np.random.get_state()
    PlayerShotDistribution(
        carry_location_metres=140.0,
        lateral_bias_metres=-1.0,
        carry_scale_metres=9.0,
        lateral_scale_metres=4.0,
        correlation=-0.2,
        degrees_of_freedom=5.0,
    )
    after = np.random.get_state()

    assert before[0] == after[0]
    assert np.array_equal(before[1], after[1])
    assert before[2] == after[2]


# --- ShotOutcomeSampler Protocol -----------------------------------------------


def test_sample_bivariate_student_t_shot_outcomes_usable_through_protocol_alias() -> None:
    """The concrete sampler is callable through a ShotOutcomeSampler-typed reference."""
    sampler: ShotOutcomeSampler = sample_bivariate_student_t_shot_outcomes

    result = sampler(BASE_DISTRIBUTION, 3, np.random.default_rng(6))

    assert len(result) == 3
    assert all(isinstance(o, ShotOutcome) for o in result)


# --- Location, correlation, and the nu/(nu-2) covariance regression -----------


def test_large_sample_mean_is_close_to_configured_location() -> None:
    """A large-count sample mean lands within a loose tolerance band of (mu_carry, mu_lateral)."""
    count = 200_000
    result = sample_bivariate_student_t_shot_outcomes(
        BASE_DISTRIBUTION, count=count, rng=np.random.default_rng(71)
    )
    downrange = np.array([o.downrange_metres for o in result])
    lateral = np.array([o.lateral_metres for o in result])

    # Loose tolerance: implied stddevs are ~11.5m/~5.8m, so the mean's standard
    # error at this sample size is a small fraction of a metre.
    assert downrange.mean() == pytest.approx(BASE_DISTRIBUTION.carry_location_metres, abs=1.0)
    assert lateral.mean() == pytest.approx(BASE_DISTRIBUTION.lateral_bias_metres, abs=1.0)


@pytest.mark.parametrize(
    "correlation,expect_sign",
    [(0.6, 1), (-0.6, -1), (0.0, 0)],
)
def test_configured_correlation_reflected_in_empirical_correlation(
    correlation: float, expect_sign: int
) -> None:
    """Positive/negative/zero configured correlation shows up (loosely) in numpy.corrcoef."""
    distribution = PlayerShotDistribution(
        carry_location_metres=150.0,
        lateral_bias_metres=0.0,
        carry_scale_metres=10.0,
        lateral_scale_metres=5.0,
        correlation=correlation,
        degrees_of_freedom=10.0,
    )
    count = 200_000
    result = sample_bivariate_student_t_shot_outcomes(
        distribution, count=count, rng=np.random.default_rng(81)
    )
    downrange = np.array([o.downrange_metres for o in result])
    lateral = np.array([o.lateral_metres for o in result])
    empirical_correlation = np.corrcoef(downrange, lateral)[0, 1]

    if expect_sign > 0:
        assert empirical_correlation > 0.3
    elif expect_sign < 0:
        assert empirical_correlation < -0.3
    else:
        assert empirical_correlation == pytest.approx(0.0, abs=0.05)


def test_empirical_covariance_matches_implied_covariance_not_raw_scale_matrix() -> None:
    """Regression for ADR 0006's nu/(nu-2) factor: catches a double-applied or omitted factor.

    Empirical sample covariance must approximate
    ``distribution.implied_covariance_metres_sq`` (which already applies
    ``nu/(nu-2)``), and must NOT approximate the raw scale matrix (factor
    omitted) or the raw scale matrix scaled by ``factor**2`` (factor
    double-applied).
    """
    distribution = PlayerShotDistribution(
        carry_location_metres=140.0,
        lateral_bias_metres=-1.0,
        carry_scale_metres=12.0,
        lateral_scale_metres=6.0,
        correlation=0.4,
        degrees_of_freedom=6.0,
    )
    count = 300_000
    result = sample_bivariate_student_t_shot_outcomes(
        distribution, count=count, rng=np.random.default_rng(41)
    )
    downrange = np.array([o.downrange_metres for o in result])
    lateral = np.array([o.lateral_metres for o in result])
    empirical_cov = np.cov(downrange, lateral)

    (expected_var_downrange, expected_cov), (_, expected_var_lateral) = (
        distribution.implied_covariance_metres_sq
    )

    assert empirical_cov[0, 0] == pytest.approx(expected_var_downrange, rel=0.15)
    assert empirical_cov[1, 1] == pytest.approx(expected_var_lateral, rel=0.15)
    assert empirical_cov[0, 1] == pytest.approx(expected_cov, rel=0.2)

    factor = distribution.degrees_of_freedom / (distribution.degrees_of_freedom - 2.0)
    raw_var_downrange = distribution.carry_scale_metres**2
    assert empirical_cov[0, 0] != pytest.approx(raw_var_downrange, rel=0.1)
    assert empirical_cov[0, 0] != pytest.approx(raw_var_downrange * factor**2, rel=0.1)


def test_low_degrees_of_freedom_produces_heavier_than_gaussian_tails() -> None:
    """A robust, non-flaky heavier-tails-than-Gaussian check via sample excess kurtosis.

    Student-t(nu=6)'s theoretical excess kurtosis is 6/(nu-4) = 3.0; Gaussian
    is 0. The assertion threshold (1.0) is well below the theoretical value
    and far above sampling noise at this sample size, so this is not a
    flaky exact-value comparison.
    """
    distribution = PlayerShotDistribution(
        carry_location_metres=150.0,
        lateral_bias_metres=0.0,
        carry_scale_metres=10.0,
        lateral_scale_metres=5.0,
        correlation=0.0,
        degrees_of_freedom=6.0,
    )
    count = 300_000
    result = sample_bivariate_student_t_shot_outcomes(
        distribution, count=count, rng=np.random.default_rng(31)
    )
    downrange = np.array([o.downrange_metres for o in result])
    standardized = (downrange - downrange.mean()) / downrange.std()
    excess_kurtosis = float(np.mean(standardized**4) - 3.0)

    assert excess_kurtosis > 1.0


# --- count == 2 broadcasting-pitfall regression -------------------------------


def test_count_two_regression_row_uses_own_scale_not_cross_broadcast() -> None:
    """Regression for the count==2 broadcasting pitfall (plan Architect design §4b).

    ``z / scale`` (without ``[:, None]``) aligns NumPy broadcasting from the
    trailing axis, so for count == 2 specifically it silently divides
    column 0 by scale[0] and column 1 by scale[1] instead of dividing row i
    by its own scale[i] — no exception is raised, so this must be caught by
    value comparison. This reproduces the plan's exact, specified reference
    computation (documented algorithm, not an internal implementation
    detail) with an identically-seeded generator and asserts the sampler
    matches the correct per-row division.
    """
    seed = 909
    distribution = BASE_DISTRIBUTION

    actual = sample_bivariate_student_t_shot_outcomes(
        distribution, count=2, rng=np.random.default_rng(seed)
    )

    reference_rng = np.random.default_rng(seed)
    sigma = np.array(
        [
            [
                distribution.carry_scale_metres**2,
                distribution.correlation
                * distribution.carry_scale_metres
                * distribution.lateral_scale_metres,
            ],
            [
                distribution.correlation
                * distribution.carry_scale_metres
                * distribution.lateral_scale_metres,
                distribution.lateral_scale_metres**2,
            ],
        ]
    )
    z = reference_rng.multivariate_normal(mean=[0.0, 0.0], cov=sigma, size=2)
    w = reference_rng.chisquare(df=distribution.degrees_of_freedom, size=2)
    scale = np.sqrt(w / distribution.degrees_of_freedom)
    mu = np.array([distribution.carry_location_metres, distribution.lateral_bias_metres])

    correct_x = mu + z / scale[:, None]
    wrong_x = mu + z / scale  # the broadcasting pitfall this test guards against

    # Sanity: the wrong computation must actually differ from the correct one
    # for this seed/distribution, otherwise this regression test wouldn't be
    # distinguishing anything.
    assert correct_x[1, 0] != pytest.approx(wrong_x[1, 0])

    assert actual[0].downrange_metres == pytest.approx(correct_x[0, 0])
    assert actual[0].lateral_metres == pytest.approx(correct_x[0, 1])
    assert actual[1].downrange_metres == pytest.approx(correct_x[1, 0])
    assert actual[1].lateral_metres == pytest.approx(correct_x[1, 1])
    assert actual[1].downrange_metres != pytest.approx(wrong_x[1, 0])


# --- count validation ----------------------------------------------------------


@pytest.mark.parametrize("invalid_count", [0, -1])
def test_invalid_count_raises_value_error_with_no_rng_side_effects(invalid_count: int) -> None:
    """count=0 and count=-1 raise ValueError, with the passed-in Generator left untouched."""
    rng = np.random.default_rng(555)
    state_before = rng.bit_generator.state

    with pytest.raises(ValueError):
        sample_bivariate_student_t_shot_outcomes(BASE_DISTRIBUTION, count=invalid_count, rng=rng)

    assert rng.bit_generator.state == state_before


# --- Non-positive downrange / extreme outcomes are never filtered -------------


def test_non_positive_downrange_samples_retained_not_filtered() -> None:
    """Some non-positive downrange draws occur and are retained unmodified in the output."""
    distribution = PlayerShotDistribution(
        carry_location_metres=5.0,
        lateral_bias_metres=0.0,
        carry_scale_metres=10.0,
        lateral_scale_metres=5.0,
        correlation=0.0,
        degrees_of_freedom=3.0,
    )
    count = 5_000
    result = sample_bivariate_student_t_shot_outcomes(
        distribution, count=count, rng=np.random.default_rng(99)
    )

    assert len(result) == count  # nothing dropped
    non_positive = [o for o in result if o.downrange_metres <= 0.0]
    assert len(non_positive) > 0


def test_extreme_heavy_tail_outliers_not_filtered() -> None:
    """A low-nu (heavy-tail) distribution produces at least one multi-sigma outlier, retained."""
    distribution = PlayerShotDistribution(
        carry_location_metres=150.0,
        lateral_bias_metres=0.0,
        carry_scale_metres=10.0,
        lateral_scale_metres=5.0,
        correlation=0.0,
        degrees_of_freedom=2.5,
    )
    count = 50_000
    result = sample_bivariate_student_t_shot_outcomes(
        distribution, count=count, rng=np.random.default_rng(101)
    )
    downrange = np.array([o.downrange_metres for o in result])
    implied_stddev = distribution.implied_carry_stddev_metres

    max_abs_deviation = float(np.max(np.abs(downrange - distribution.carry_location_metres)))
    assert max_abs_deviation > 5.0 * implied_stddev


# --- Composition with M4.7's environment transform ----------------------------


def test_intrinsic_outcomes_unmodified_by_environment_transform() -> None:
    """Sampled intrinsic ShotOutcomes are unchanged after being passed through the transform."""
    intrinsic = sample_bivariate_student_t_shot_outcomes(
        BASE_DISTRIBUTION, count=20, rng=np.random.default_rng(7)
    )
    intrinsic_snapshot = tuple(intrinsic)
    environment = EnvironmentInput(wind=WindComponents(longitudinal_mps=8.0, lateral_mps=-3.0))

    adjusted = tuple(apply_environment_transform(o, environment) for o in intrinsic)

    assert intrinsic == intrinsic_snapshot
    assert adjusted != intrinsic


def test_optional_environment_and_no_environment_paths_both_work() -> None:
    """Intrinsic sampling alone, and intrinsic sampling + transform, both yield valid sequences."""
    intrinsic = sample_bivariate_student_t_shot_outcomes(
        BASE_DISTRIBUTION, count=10, rng=np.random.default_rng(11)
    )
    with_environment = tuple(
        apply_environment_transform(o, EnvironmentInput(wind=WindComponents(longitudinal_mps=4.0)))
        for o in intrinsic
    )

    assert len(intrinsic) == len(with_environment) == 10
    assert all(isinstance(o, ShotOutcome) for o in intrinsic)
    assert all(isinstance(o, ShotOutcome) for o in with_environment)
    assert intrinsic != with_environment


def test_headwind_tailwind_crosswind_integration_through_environment_transform() -> None:
    """Sampled intrinsic outcomes + environment transform reproduce M4.7's directional effects."""
    intrinsic = sample_bivariate_student_t_shot_outcomes(
        BASE_DISTRIBUTION, count=500, rng=np.random.default_rng(13)
    )
    baseline = tuple(apply_environment_transform(o, EnvironmentInput()) for o in intrinsic)
    headwind = tuple(
        apply_environment_transform(o, EnvironmentInput(wind=WindComponents(longitudinal_mps=-6.0)))
        for o in intrinsic
    )
    tailwind = tuple(
        apply_environment_transform(o, EnvironmentInput(wind=WindComponents(longitudinal_mps=6.0)))
        for o in intrinsic
    )
    crosswind = tuple(
        apply_environment_transform(o, EnvironmentInput(wind=WindComponents(lateral_mps=6.0)))
        for o in intrinsic
    )

    mean_baseline_downrange = sum(o.downrange_metres for o in baseline) / len(baseline)
    mean_headwind_downrange = sum(o.downrange_metres for o in headwind) / len(headwind)
    mean_tailwind_downrange = sum(o.downrange_metres for o in tailwind) / len(tailwind)
    mean_baseline_lateral = sum(o.lateral_metres for o in baseline) / len(baseline)
    mean_crosswind_lateral = sum(o.lateral_metres for o in crosswind) / len(crosswind)

    assert mean_headwind_downrange < mean_baseline_downrange
    assert mean_tailwind_downrange > mean_baseline_downrange
    assert mean_crosswind_lateral > mean_baseline_lateral


def test_environment_transform_deterministic_given_same_intrinsic_samples() -> None:
    """Applying apply_environment_transform twice to the same intrinsic samples is deterministic."""
    intrinsic = sample_bivariate_student_t_shot_outcomes(
        BASE_DISTRIBUTION, count=15, rng=np.random.default_rng(21)
    )
    environment = EnvironmentInput(
        wind=WindComponents(longitudinal_mps=-3.0, lateral_mps=2.0), elevation_delta_metres=4.0
    )

    first = tuple(apply_environment_transform(o, environment) for o in intrinsic)
    second = tuple(apply_environment_transform(o, environment) for o in intrinsic)

    assert first == second
