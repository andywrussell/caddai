"""Seeded bivariate Student-t shot-outcome sampling.

See ADR 0006 (docs/adr/0006-player-shot-distribution-bivariate-student-t.md)
for the binding ``X = mu + Z / sqrt(W/nu)`` construction and
docs/plans/m4.8-seeded-shot-outcome-simulation.plan.md (GitHub issue #56)
for the design implemented here.

This module draws *intrinsic* shot outcomes from a player's
``PlayerShotDistribution`` — no environmental adjustment. Composition with
M4.7's ``apply_environment_transform`` (``environment.py``) is a plain
caller-side loop over the returned tuple; this module has no opinion on
whether/when that transform is applied.
"""

from typing import Protocol

import numpy as np

from caddai.simulation.models import ShotOutcome
from caddai.statistics.shot_distribution import PlayerShotDistribution


class ShotOutcomeSampler(Protocol):
    """Contract for a technique that draws intrinsic shot outcomes from a distribution.

    ``sample_bivariate_student_t_shot_outcomes`` is the current (and only)
    implementation of this contract. It exists as a ``Protocol`` rather
    than an enum/registry so a future alternate technique can be typed
    against the same call shape without this module deciding between
    techniques at runtime — nothing here dispatches between
    implementations.
    """

    def __call__(
        self,
        distribution: PlayerShotDistribution,
        count: int,
        rng: np.random.Generator,
    ) -> tuple[ShotOutcome, ...]: ...


def sample_bivariate_student_t_shot_outcomes(
    distribution: PlayerShotDistribution,
    count: int,
    rng: np.random.Generator,
) -> tuple[ShotOutcome, ...]:
    """Draw ``count`` intrinsic shot outcomes from ``distribution``'s bivariate Student-t.

    Implements ADR 0006's construction exactly: ``Z ~ N(0, Sigma)``,
    ``W ~ chisquare(nu)``, ``X = mu + Z / sqrt(W / nu)``, where ``Sigma`` is
    the 2x2 Student-t **scale** matrix built directly from
    ``distribution.carry_scale_metres``, ``distribution.lateral_scale_metres``,
    and ``distribution.correlation``:

        Sigma = [[carry_scale**2,              correlation*carry_scale*lateral_scale],
                 [correlation*carry_scale*lateral_scale, lateral_scale**2]]

    ``Sigma`` is deliberately **not** built from
    ``distribution.implied_covariance_metres_sq``: that property already
    applies the ``nu / (nu - 2)`` factor that converts the Student-t scale
    matrix into its implied covariance matrix. The ``z / sqrt(w / nu)``
    division below reintroduces that same factor's effect statistically
    (in expectation, over many draws) — passing the already-scaled
    covariance as ``Sigma`` here would double-apply it, understating the
    true dispersion of the output. ``rng.multivariate_normal`` is called
    with ``mean=[0.0, 0.0]``, not ``mu``: per ADR 0006, the location
    (``mu = (carry_location_metres, lateral_bias_metres)``) is added
    *after* dividing by ``sqrt(w / nu)``, not before — adding it inside
    ``multivariate_normal`` would incorrectly scale the mean by the
    Student-t mixing factor along with the noise.

    Only methods on the passed-in ``rng`` are used; no module-level
    ``numpy.random.*`` function or ``numpy.random.seed`` call is made, so
    this function never reads or mutates NumPy's legacy global random
    state, and two calls with independently-constructed ``rng`` instances
    never interfere with each other.

    Raises ``ValueError`` if ``count < 1``, before ``rng`` is used at all
    (no partial random-state consumption on an invalid call — ``0`` is
    treated as a likely caller bug, not a legitimate "simulate nothing"
    request).

    No output value is ever clamped, truncated, resampled, or winsorized:
    a non-positive ``downrange_metres`` or a large-magnitude
    ``lateral_metres`` drawn from the Student-t heavy tail is retained
    unchanged. This is intentional, evidence-motivated behaviour (ADR
    0006) — distinct from, and not to be confused with,
    ``environment.py``'s wind-exposure floor, which is a physical-transform
    policy that belongs only to the optional environment-transform stage.

    ``distribution.degrees_of_freedom`` is passed unchanged as ``df=`` to
    ``rng.chisquare`` — no recalibration, rounding, or integer coercion.
    """
    if count < 1:
        raise ValueError(f"count must be >= 1, got {count}")

    carry_scale = distribution.carry_scale_metres
    lateral_scale = distribution.lateral_scale_metres
    correlation = distribution.correlation
    sigma = np.array(
        [
            [carry_scale**2, correlation * carry_scale * lateral_scale],
            [correlation * carry_scale * lateral_scale, lateral_scale**2],
        ]
    )
    mu = np.array([distribution.carry_location_metres, distribution.lateral_bias_metres])

    z = rng.multivariate_normal(mean=[0.0, 0.0], cov=sigma, size=count)
    w = rng.chisquare(df=distribution.degrees_of_freedom, size=count)
    scale = np.sqrt(w / distribution.degrees_of_freedom)
    # [:, None] reshapes (count,) to (count, 1) so each row of z divides by its
    # own scalar. Without it, NumPy aligns from the trailing axis: for
    # count != 2 this raises, but for count == 2 specifically it silently
    # cross-broadcasts — column 0 divided by scale[0], column 1 by scale[1] —
    # instead of dividing row i by scale[i].
    x = mu + z / scale[:, None]

    return tuple(
        ShotOutcome(downrange_metres=float(row[0]), lateral_metres=float(row[1])) for row in x
    )
