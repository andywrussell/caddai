"""Tests for the ``PlayerShotDistribution`` domain type.

See GitHub issue #49 ("M4.1 — PlayerShotDistribution domain type") and
docs/plans/m4.1-player-shot-distribution.plan.md for the acceptance
criteria these tests are derived from, and ADR 0006
(docs/adr/0006-player-shot-distribution-bivariate-student-t.md) for the
underlying bivariate Student-t construction.

``PlayerShotDistribution`` diverges intentionally from M3's
``CarryDistribution``/``DirectionalDispersion``: ``carry_scale_metres`` and
``lateral_scale_metres`` are strictly positive (zero is rejected, unlike
M3's stddev fields which allow zero as a "no data yet" placeholder),
``correlation`` must lie in the open interval ``(-1, 1)`` (exact +/-1 makes
the 2x2 scale matrix singular), and ``degrees_of_freedom`` must be strictly
greater than 2 (the covariance of the ADR 0006 construction is only finite
for ``nu > 2``). This module does not test sampling, ``PopulationPrior``,
or ``Club``/``Player`` composition — those are out of scope for M4.1.
"""

import math

import pytest
from pydantic import ValidationError

from caddai.statistics.shot_distribution import (
    PlayerShotDistribution,
    ShotDistributionFamily,
)


def _valid_kwargs(**overrides: float) -> dict[str, float]:
    """Baseline valid constructor kwargs for a typical shot distribution."""
    kwargs: dict[str, float] = {
        "carry_location_metres": 140.0,
        "lateral_bias_metres": 1.5,
        "carry_scale_metres": 8.0,
        "lateral_scale_metres": 4.0,
        "correlation": 0.2,
        "degrees_of_freedom": 6.0,
    }
    kwargs.update(overrides)
    return kwargs


# --- Construction and defaults ---------------------------------------------


def test_constructs_with_typical_values() -> None:
    """A physically plausible bivariate Student-t shot distribution is accepted."""
    distribution = PlayerShotDistribution(**_valid_kwargs())

    assert distribution.carry_location_metres == pytest.approx(140.0)
    assert distribution.lateral_bias_metres == pytest.approx(1.5)
    assert distribution.carry_scale_metres == pytest.approx(8.0)
    assert distribution.lateral_scale_metres == pytest.approx(4.0)
    assert distribution.correlation == pytest.approx(0.2)
    assert distribution.degrees_of_freedom == pytest.approx(6.0)


def test_family_defaults_to_bivariate_student_t() -> None:
    """Omitting ``family`` defaults to the only currently-supported family."""
    distribution = PlayerShotDistribution(**_valid_kwargs())

    assert distribution.family == ShotDistributionFamily.BIVARIATE_STUDENT_T


def test_family_accepts_explicit_bivariate_student_t() -> None:
    """Explicitly passing the family member round-trips unchanged."""
    distribution = PlayerShotDistribution(
        family=ShotDistributionFamily.BIVARIATE_STUDENT_T, **_valid_kwargs()
    )

    assert distribution.family == ShotDistributionFamily.BIVARIATE_STUDENT_T


# --- carry_location_metres ---------------------------------------------------


@pytest.mark.parametrize("carry_location_metres", [0.0, -1.0, -140.0])
def test_rejects_non_positive_carry_location(carry_location_metres: float) -> None:
    """A zero or negative carry location is not a physically meaningful shot production mean."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(carry_location_metres=carry_location_metres))


@pytest.mark.parametrize("carry_location_metres", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_carry_location(carry_location_metres: float) -> None:
    """NaN/+inf/-inf are rejected even though +inf satisfies a ``gt=0`` bound check."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(carry_location_metres=carry_location_metres))


# --- lateral_bias_metres -----------------------------------------------------


@pytest.mark.parametrize("lateral_bias_metres", [-3.0, 0.0, 3.0])
def test_accepts_any_lateral_bias_sign(lateral_bias_metres: float) -> None:
    """Lateral bias is signed (negative left, positive right) and unconstrained in sign."""
    distribution = PlayerShotDistribution(**_valid_kwargs(lateral_bias_metres=lateral_bias_metres))

    assert distribution.lateral_bias_metres == pytest.approx(lateral_bias_metres)


@pytest.mark.parametrize("lateral_bias_metres", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_lateral_bias(lateral_bias_metres: float) -> None:
    """Lateral bias is unconstrained in sign but must still be finite."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(lateral_bias_metres=lateral_bias_metres))


# --- carry_scale_metres -------------------------------------------------------


@pytest.mark.parametrize("carry_scale_metres", [0.0, -0.0001, -8.0])
def test_rejects_non_positive_carry_scale(carry_scale_metres: float) -> None:
    """Zero (unlike M3's ``CarryDistribution.stddev_metres``) or negative scale is invalid."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(carry_scale_metres=carry_scale_metres))


@pytest.mark.parametrize("carry_scale_metres", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_carry_scale(carry_scale_metres: float) -> None:
    """NaN/+inf/-inf are rejected even though +inf satisfies a ``gt=0`` bound check."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(carry_scale_metres=carry_scale_metres))


# --- lateral_scale_metres ------------------------------------------------------


@pytest.mark.parametrize("lateral_scale_metres", [0.0, -0.0001, -4.0])
def test_rejects_non_positive_lateral_scale(lateral_scale_metres: float) -> None:
    """Zero (unlike M3's ``DirectionalDispersion``) or negative lateral scale is invalid."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(lateral_scale_metres=lateral_scale_metres))


@pytest.mark.parametrize("lateral_scale_metres", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_lateral_scale(lateral_scale_metres: float) -> None:
    """NaN/+inf/-inf are rejected even though +inf satisfies a ``gt=0`` bound check."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(lateral_scale_metres=lateral_scale_metres))


# --- correlation ---------------------------------------------------------------


@pytest.mark.parametrize("correlation", [-0.999999, -0.5, 0.0, 0.5, 0.999999])
def test_accepts_correlation_strictly_inside_open_interval(correlation: float) -> None:
    """Correlation values strictly inside (-1, 1), including near the boundary, are valid."""
    distribution = PlayerShotDistribution(**_valid_kwargs(correlation=correlation))

    assert distribution.correlation == pytest.approx(correlation)


@pytest.mark.parametrize("correlation", [-1.0, 1.0])
def test_rejects_correlation_at_open_interval_boundary(correlation: float) -> None:
    """Exactly +/-1 makes the 2x2 scale matrix singular, unlike a closed [-1, 1] range."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(correlation=correlation))


@pytest.mark.parametrize("correlation", [-1.5, -1.0001, 1.0001, 1.5])
def test_rejects_correlation_outside_open_interval(correlation: float) -> None:
    """Correlation magnitudes greater than 1 are not valid Pearson correlation coefficients."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(correlation=correlation))


@pytest.mark.parametrize("correlation", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_correlation(correlation: float) -> None:
    """NaN/+inf/-inf are rejected even though they may incidentally fail open-interval bounds."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(correlation=correlation))


# --- degrees_of_freedom ----------------------------------------------------------


def test_rejects_degrees_of_freedom_at_lower_boundary() -> None:
    """Exactly nu=2 makes the implied covariance infinite and is rejected."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(degrees_of_freedom=2.0))


@pytest.mark.parametrize("degrees_of_freedom", [2.0001, 3.0, 6.0, 1000.0])
def test_accepts_degrees_of_freedom_above_lower_boundary(degrees_of_freedom: float) -> None:
    """Values immediately above 2, and arbitrarily large values, are valid."""
    distribution = PlayerShotDistribution(**_valid_kwargs(degrees_of_freedom=degrees_of_freedom))

    assert distribution.degrees_of_freedom == pytest.approx(degrees_of_freedom)


@pytest.mark.parametrize("degrees_of_freedom", [0.0, -1.0, 1.0, 1.9999])
def test_rejects_degrees_of_freedom_at_or_below_two(degrees_of_freedom: float) -> None:
    """Non-positive or between-0-and-2 degrees of freedom is rejected, not just exactly 2."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(degrees_of_freedom=degrees_of_freedom))


@pytest.mark.parametrize("degrees_of_freedom", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_degrees_of_freedom(degrees_of_freedom: float) -> None:
    """NaN/+inf/-inf are rejected even though +inf satisfies a ``gt=2`` bound check."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(degrees_of_freedom=degrees_of_freedom))


# --- implied_covariance_metres_sq / implied stddev computed properties -------------


def test_implied_covariance_matches_hand_computed_values() -> None:
    """The implied covariance matrix applies the nu/(nu-2) factor to scale and correlation."""
    distribution = PlayerShotDistribution(
        **_valid_kwargs(
            carry_scale_metres=8.0,
            lateral_scale_metres=4.0,
            correlation=0.5,
            degrees_of_freedom=5.0,
        )
    )
    factor = 5.0 / (5.0 - 2.0)
    expected_var_c = factor * 8.0**2
    expected_var_l = factor * 4.0**2
    expected_cov_cl = factor * 0.5 * 8.0 * 4.0

    (var_c, cov_cl), (cov_cl_2, var_l) = distribution.implied_covariance_metres_sq

    assert var_c == pytest.approx(expected_var_c)
    assert var_l == pytest.approx(expected_var_l)
    assert cov_cl == pytest.approx(expected_cov_cl)
    assert cov_cl_2 == pytest.approx(expected_cov_cl)


def test_implied_covariance_matrix_is_symmetric() -> None:
    """The two off-diagonal covariance entries are identical, as required of a covariance matrix."""
    distribution = PlayerShotDistribution(**_valid_kwargs(correlation=-0.3))

    (_, cov_cl_top), (cov_cl_bottom, _) = distribution.implied_covariance_metres_sq

    assert cov_cl_top == pytest.approx(cov_cl_bottom)


def test_implied_carry_stddev_applies_nu_factor_for_nu_five() -> None:
    """For nu=5, factor sqrt(5/3) ~= 1.29, so implied stddev must exceed the raw scale."""
    distribution = PlayerShotDistribution(
        **_valid_kwargs(carry_scale_metres=8.0, degrees_of_freedom=5.0)
    )

    assert distribution.implied_carry_stddev_metres == pytest.approx(8.0 * math.sqrt(5.0 / 3.0))


def test_implied_lateral_stddev_applies_nu_factor_for_nu_five() -> None:
    """For nu=5, factor sqrt(5/3) ~= 1.29, so implied stddev must exceed the raw scale."""
    distribution = PlayerShotDistribution(
        **_valid_kwargs(lateral_scale_metres=4.0, degrees_of_freedom=5.0)
    )

    assert distribution.implied_lateral_stddev_metres == pytest.approx(4.0 * math.sqrt(5.0 / 3.0))


def test_implied_stddev_is_never_equal_to_raw_scale_for_finite_nu() -> None:
    """The scale parameter is not the standard deviation — they differ for any finite nu > 2."""
    distribution = PlayerShotDistribution(
        **_valid_kwargs(carry_scale_metres=8.0, lateral_scale_metres=4.0, degrees_of_freedom=6.0)
    )

    assert distribution.implied_carry_stddev_metres != pytest.approx(
        distribution.carry_scale_metres
    )
    assert distribution.implied_lateral_stddev_metres != pytest.approx(
        distribution.lateral_scale_metres
    )


def test_correlation_is_recoverable_from_implied_covariance() -> None:
    """The nu/(nu-2) factor scales the covariance matrix uniformly, so correlation is unchanged."""
    distribution = PlayerShotDistribution(**_valid_kwargs(correlation=0.35, degrees_of_freedom=4.0))

    (var_c, cov_cl), (_, var_l) = distribution.implied_covariance_metres_sq
    recovered_correlation = cov_cl / math.sqrt(var_c * var_l)

    assert recovered_correlation == pytest.approx(distribution.correlation)


# --- serialisation -----------------------------------------------------------------


def test_model_dump_round_trips_all_fields() -> None:
    """``model_dump()`` reproduces every field with its original value."""
    distribution = PlayerShotDistribution(**_valid_kwargs())

    dumped = distribution.model_dump()

    assert dumped["carry_location_metres"] == pytest.approx(140.0)
    assert dumped["lateral_bias_metres"] == pytest.approx(1.5)
    assert dumped["carry_scale_metres"] == pytest.approx(8.0)
    assert dumped["lateral_scale_metres"] == pytest.approx(4.0)
    assert dumped["correlation"] == pytest.approx(0.2)
    assert dumped["degrees_of_freedom"] == pytest.approx(6.0)
    assert dumped["family"] == ShotDistributionFamily.BIVARIATE_STUDENT_T


def test_model_dump_json_mode_serialises_family_as_plain_string() -> None:
    """JSON-mode serialisation must produce the plain string, not the enum member, for interop."""
    distribution = PlayerShotDistribution(**_valid_kwargs())

    dumped = distribution.model_dump(mode="json")

    assert dumped["family"] == "bivariate_student_t"
