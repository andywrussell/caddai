"""Tests for the carry distribution and directional dispersion models.

See GitHub issue #26 ("M3.1 — Carry distribution model") and
docs/plans/m3.1-carry-distribution-model.plan.md Task 1 for the
``CarryDistribution`` acceptance criteria these tests are derived from:
``mean_metres`` must be strictly positive (``gt=0``) and ``stddev_metres``
must be non-negative (``ge=0``).

See also GitHub issue #27 ("M3.2 — Directional dispersion model") and
docs/plans/m3.2-directional-dispersion-model.plan.md Task 1 for the
``DirectionalDispersion`` acceptance criteria: ``lateral_stddev_metres``
must be non-negative (``ge=0``) and ``lateral_bias_metres`` is signed and
unconstrained.

See also GitHub issue #38 ("M3.x — Enforce finite values in statistical
domain models") and
docs/plans/m3.x-enforce-finite-statistics-values.plan.md Task 1: all four
fields (``mean_metres``, ``stddev_metres``, ``lateral_stddev_metres``,
``lateral_bias_metres``) must reject NaN and +/-infinity, since ``+inf``
otherwise passes both the ``gt=0`` and ``ge=0`` constraints.
"""

import pytest
from pydantic import ValidationError

from caddai.statistics.models import CarryDistribution, DirectionalDispersion


def test_carry_distribution_constructs_with_typical_values() -> None:
    """A carry distribution with a positive mean and typical variability is accepted."""
    distribution = CarryDistribution(mean_metres=140.0, stddev_metres=8.5)

    assert distribution.mean_metres == pytest.approx(140.0)
    assert distribution.stddev_metres == pytest.approx(8.5)


def test_carry_distribution_accepts_zero_stddev() -> None:
    """A stddev of exactly zero is valid — a club with no measured variability yet."""
    distribution = CarryDistribution(mean_metres=140.0, stddev_metres=0.0)

    assert distribution.stddev_metres == pytest.approx(0.0)


@pytest.mark.parametrize("mean_metres", [0.0, -1.0, -140.0])
def test_carry_distribution_rejects_non_positive_mean(mean_metres: float) -> None:
    """Zero or negative mean carry distance is physically meaningless."""
    with pytest.raises(ValidationError):
        CarryDistribution(mean_metres=mean_metres, stddev_metres=8.5)


@pytest.mark.parametrize("stddev_metres", [-0.0001, -1.0, -8.5])
def test_carry_distribution_rejects_negative_stddev(stddev_metres: float) -> None:
    """A negative standard deviation is not a valid dispersion measure."""
    with pytest.raises(ValidationError):
        CarryDistribution(mean_metres=140.0, stddev_metres=stddev_metres)


def test_directional_dispersion_constructs_with_typical_values() -> None:
    """A directional dispersion with a positive bias and typical spread is accepted."""
    dispersion = DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=2.1)

    assert dispersion.lateral_stddev_metres == pytest.approx(4.5)
    assert dispersion.lateral_bias_metres == pytest.approx(2.1)


def test_directional_dispersion_accepts_zero_lateral_stddev() -> None:
    """A lateral stddev of exactly zero is valid — no measured spread yet."""
    dispersion = DirectionalDispersion(lateral_stddev_metres=0.0, lateral_bias_metres=0.0)

    assert dispersion.lateral_stddev_metres == pytest.approx(0.0)


@pytest.mark.parametrize("lateral_bias_metres", [-4.2, 0.0, 4.2])
def test_directional_dispersion_accepts_any_lateral_bias_sign(
    lateral_bias_metres: float,
) -> None:
    """Lateral bias is signed and round-trips unchanged, not normalized or clamped."""
    dispersion = DirectionalDispersion(
        lateral_stddev_metres=4.5, lateral_bias_metres=lateral_bias_metres
    )

    assert dispersion.lateral_bias_metres == pytest.approx(lateral_bias_metres)


@pytest.mark.parametrize("lateral_stddev_metres", [-0.0001, -1.0, -6.0])
def test_directional_dispersion_rejects_negative_lateral_stddev(
    lateral_stddev_metres: float,
) -> None:
    """A negative lateral standard deviation is not a valid dispersion measure."""
    with pytest.raises(ValidationError):
        DirectionalDispersion(lateral_stddev_metres=lateral_stddev_metres, lateral_bias_metres=2.1)


@pytest.mark.parametrize("mean_metres", [float("nan"), float("inf"), float("-inf")])
def test_carry_distribution_rejects_non_finite_mean(mean_metres: float) -> None:
    """Issue #38: NaN/+inf/-inf are rejected even though ``+inf`` satisfies ``gt=0``."""
    with pytest.raises(ValidationError):
        CarryDistribution(mean_metres=mean_metres, stddev_metres=8.5)


@pytest.mark.parametrize("stddev_metres", [float("nan"), float("inf"), float("-inf")])
def test_carry_distribution_rejects_non_finite_stddev(stddev_metres: float) -> None:
    """Issue #38: NaN/+inf/-inf are rejected even though ``+inf`` satisfies ``ge=0``."""
    with pytest.raises(ValidationError):
        CarryDistribution(mean_metres=140.0, stddev_metres=stddev_metres)


@pytest.mark.parametrize("lateral_stddev_metres", [float("nan"), float("inf"), float("-inf")])
def test_directional_dispersion_rejects_non_finite_lateral_stddev(
    lateral_stddev_metres: float,
) -> None:
    """Issue #38: NaN/+inf/-inf are rejected even though ``+inf`` satisfies ``ge=0``."""
    with pytest.raises(ValidationError):
        DirectionalDispersion(lateral_stddev_metres=lateral_stddev_metres, lateral_bias_metres=2.1)


@pytest.mark.parametrize("lateral_bias_metres", [float("nan"), float("inf"), float("-inf")])
def test_directional_dispersion_rejects_non_finite_lateral_bias(
    lateral_bias_metres: float,
) -> None:
    """Issue #38: lateral bias is unconstrained in sign but must still be finite."""
    with pytest.raises(ValidationError):
        DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=lateral_bias_metres)
