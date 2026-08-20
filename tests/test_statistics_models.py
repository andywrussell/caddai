"""Tests for the M3.1 carry distribution model: ``CarryDistribution``.

See GitHub issue #26 ("M3.1 — Carry distribution model") and
docs/plans/m3.1-carry-distribution-model.plan.md Task 1 for the acceptance
criteria these tests are derived from: ``mean_metres`` must be strictly
positive (``gt=0``) and ``stddev_metres`` must be non-negative (``ge=0``).
"""

import pytest
from pydantic import ValidationError

from caddai.statistics.models import CarryDistribution


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
