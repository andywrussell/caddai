"""Bivariate Student-t shot-production distribution.

See ADR 0006 (docs/adr/0006-player-shot-distribution-bivariate-student-t.md)
for the underlying construction (``X = mu + Z / sqrt(W/nu)``, ``Z ~ N(0,
Sigma)``, ``W ~ chisquare(nu)``) and
docs/plans/m4.1-player-shot-distribution.plan.md for the boundary decisions
implemented here. See docs/player-model.md for the full planned design of
this subsystem.
"""

import math
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


def _require_finite(value: float) -> float:
    """Reject NaN/+inf/-inf, which otherwise satisfy ``gt``/``lt`` constraints."""
    if not math.isfinite(value):
        raise ValueError("must be finite")
    return value


class ShotDistributionFamily(StrEnum):
    """Statistical family used to model a player's shot production."""

    BIVARIATE_STUDENT_T = "bivariate_student_t"


class PlayerShotDistribution(BaseModel):
    """A player's shot-production distribution for a single club, as a
    bivariate Student-t over (carry, lateral offset), in metres.

    This is the ADR 0006 shot-production representation. It holds its own
    independent joint parameters — it is **not** derived from, and does not
    compose with, M3's ``CarryDistribution``/``DirectionalDispersion``
    (both remain valid, unmodified primitives). Composing the two is
    deferred to a future milestone (M4.6).

    ``carry_scale_metres`` and ``lateral_scale_metres`` are Student-t
    **scale** parameters, not standard deviations, and
    ``(carry_scale_metres, lateral_scale_metres, correlation)`` together do
    **not** form the covariance matrix directly. For degrees of freedom
    ``nu``, the implied covariance matrix is::

        Cov = (nu / (nu - 2)) * Sigma

    where ``Sigma`` is the 2x2 scale matrix built from
    ``carry_scale_metres``, ``lateral_scale_metres``, and ``correlation``.
    See ``implied_covariance_metres_sq``,
    ``implied_carry_stddev_metres``, and ``implied_lateral_stddev_metres``
    for the derived quantities. Because the ``nu / (nu - 2)`` factor scales
    the whole covariance matrix uniformly, ``correlation`` is literally the
    distribution's Pearson correlation coefficient, invariant to that
    scaling factor — it is not merely a scale-matrix parameter that needs
    separate reinterpretation.

    ``degrees_of_freedom`` (``nu``) must be strictly greater than 2: the
    mean of this construction exists only for ``nu > 1``, and the
    covariance exists (is finite) only for ``nu > 2``. CaddAI needs both an
    expected carry and a finite dispersion/covariance to always be
    meaningful domain quantities, so ``nu > 2`` is enforced at construction
    time rather than left for every downstream consumer to special-case.

    ``correlation`` must lie in the open interval ``(-1, 1)``: exactly +/-1
    makes the 2x2 scale matrix singular/rank-deficient, which is
    unsuitable for the ADR 0006 ``numpy.random.Generator.multivariate_normal``
    sampling construction (not implemented in this type) and does not
    describe a meaningful shot-production distribution (all probability
    mass on a line).

    Numeric hyperparameters are provisional pending calibration data per
    ADR 0006/ADR 0007 — this type stores no calibration defaults (no
    numeric field has a default value) and no ADR 0007 provenance/
    confidence metadata (deliberately deferred to the future
    ``PopulationPrior`` type, M4.2, per ADR 0007's "or an adjacent type"
    allowance).

    Construction is deterministic and side-effect free: this type defines
    no ``sample()`` method, no RNG parameter, and no NumPy random usage —
    Monte Carlo sampling is out of scope for M4.1.
    """

    family: ShotDistributionFamily = ShotDistributionFamily.BIVARIATE_STUDENT_T
    carry_location_metres: float = Field(gt=0)
    lateral_bias_metres: float
    carry_scale_metres: float = Field(gt=0)
    lateral_scale_metres: float = Field(gt=0)
    correlation: float = Field(gt=-1.0, lt=1.0)
    degrees_of_freedom: float = Field(gt=2.0)

    @field_validator(
        "carry_location_metres",
        "lateral_bias_metres",
        "carry_scale_metres",
        "lateral_scale_metres",
        "correlation",
        "degrees_of_freedom",
    )
    @classmethod
    def _validate_finite(cls, value: float) -> float:
        return _require_finite(value)

    @property
    def implied_covariance_metres_sq(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """The 2x2 covariance matrix ``(nu / (nu - 2)) * Sigma``, in metres squared.

        Not the same as the scale parameters — see the class docstring.
        """
        factor = self.degrees_of_freedom / (self.degrees_of_freedom - 2.0)
        var_carry = factor * self.carry_scale_metres**2
        var_lateral = factor * self.lateral_scale_metres**2
        cov = factor * self.correlation * self.carry_scale_metres * self.lateral_scale_metres
        return ((var_carry, cov), (cov, var_lateral))

    @property
    def implied_carry_stddev_metres(self) -> float:
        """The implied carry standard deviation, ``sqrt(nu / (nu - 2)) * carry_scale_metres``.

        Not equal to ``carry_scale_metres`` — see the class docstring.
        """
        factor = self.degrees_of_freedom / (self.degrees_of_freedom - 2.0)
        return math.sqrt(factor) * self.carry_scale_metres

    @property
    def implied_lateral_stddev_metres(self) -> float:
        """The implied lateral standard deviation, ``sqrt(nu / (nu - 2)) * lateral_scale_metres``.

        Not equal to ``lateral_scale_metres`` — see the class docstring.
        """
        factor = self.degrees_of_freedom / (self.degrees_of_freedom - 2.0)
        return math.sqrt(factor) * self.lateral_scale_metres
