"""Provisional environment/physics transform coefficient config.

See docs/plans/m4.7-environment-physics-transform.plan.md (GitHub issue
#55) for the design this implements, and
docs/adr/0001-deterministic-strategy-engine.md /
docs/adr/0006-player-shot-distribution-bivariate-student-t.md for the wider
deterministic-modelling context this config sits within.

Every coefficient below is a provisional placeholder for
``apply_environment_transform`` (``environment.py``) to have a real,
testable config rather than an empty contract. None of these values may be
described as "calibrated" anywhere in code or docs until they are replaced
by CaddAI's own measured/evidence-derived data — this module's job is only
to make the *shape* of the transform (linear wind/elevation/air-density
terms, asymmetric headwind/tailwind response, per-club-category
sensitivity) concrete and unit-tested, not to assert any of these numbers
are correct. Each coefficient is classified below by evidence quality:

- **physics-derived** — follows directly from an uncontested physical
  relationship (not merely "informed by" evidence, but derivable from
  first principles), even though the exact numeric coefficient chosen here
  is still provisional:
  - ``reference_air_density_kg_per_m3`` (default ``1.225``): the ICAO
    standard atmosphere sea-level air density. This constant itself is a
    physical fact, not a CaddAI estimate — only its use as *this* system's
    reference point is a modelling choice.
  - The general *form* of the air-density correction (lower density than
    reference increases carry, higher density decreases it, applied
    multiplicatively via a density ratio) follows directly from projectile
    drag physics; the coefficient magnitude (``air_density_sensitivity``)
    is not measured for CaddAI's shot model and remains
    arbitrary-provisional (see below).
  - The general *sign* of the elevation effect (uphill reduces effective
    downrange progress toward the target, downhill increases it) is a
    physical/geometric fact; the specific linear coefficient
    (``elevation_sensitivity``) is arbitrary-provisional.

- **evidence-informed-provisional** — direction/relative-ordering is
  supported by general ballistics/golf-instruction knowledge, but the
  numeric magnitude is CaddAI's own provisional estimate, not measured from
  CaddAI's own data:
  - ``headwind_sensitivity_metres_per_mps`` >
    ``tailwind_sensitivity_metres_per_mps`` (default ``1.2`` vs ``0.8``):
    it is well-established golf-ballistics folk wisdom (and consistent
    with backspin-induced lift depending on relative airspeed) that a
    headwind costs more distance than an equivalent tailwind gains —
    headwind increases the ball's relative airspeed, which increases
    induced backspin lift and drag, disproportionately steepening its
    descent and shortening carry, whereas a tailwind reduces relative
    airspeed and lift roughly proportionately rather than
    disproportionately. This asymmetry (headwind coefficient strictly
    greater than tailwind coefficient) is deliberately encoded here, but
    the specific values ``1.2``/``0.8`` and their exact ratio are
    illustrative/uncalibrated — **not** measured for any real ball, club,
    or launch condition.
  - ``club_category_sensitivity_multipliers``: it is well-established golf
    knowledge that lower-lofted, lower-flight-time shots (e.g. driver) are
    less wind-affected than higher-lofted, higher-flight-time shots (e.g.
    wedge) for a given ball speed, so the relative ordering
    (``DRIVER`` < ``FAIRWAY_WOOD`` < ``HYBRID`` < ``IRON`` < ``WEDGE``) is
    evidence-informed. The exact multiplier values (``0.85``-``1.20``) are
    illustrative/uncalibrated.

- **arbitrary-provisional** — CaddAI has chosen a value/shape only to make
  the transform well-defined and testable; there is no external evidence
  basis for the magnitude, and no directional claim is being asserted
  beyond "some sensitivity exists":
  - ``crosswind_sensitivity_metres_per_mps`` (default ``0.6``).
  - ``elevation_sensitivity`` (default ``1.0``, i.e. one metre of lateral
    downrange effect per metre of elevation delta).
  - ``air_density_sensitivity`` (default ``1.0``, i.e. the full linear
    density-ratio correction with no damping).
  - ``reference_carry_metres`` (default ``100.0``): an arbitrary
    normalisation constant used only to build a dimensionless
    "hang-time proxy" scale factor (``outcome.downrange_metres /
    reference_carry_metres``) for the wind terms — it is not a claim about
    any particular club's typical carry. Because that scale factor is
    floored at zero, any non-positive intrinsic ``outcome.downrange_metres``
    deliberately zeroes all wind effects (both longitudinal and lateral)
    regardless of wind magnitude — see ``environment.py``'s module/function
    docstrings for the documented V1 validity domain.

Nothing in this module performs calibration, fitting, or learning; it is a
static, versioned (``config_version``) lookup consumed by
``apply_environment_transform``.
"""

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field

from caddai.statistics.models import ClubCategory

ENVIRONMENT_TRANSFORM_CONFIG_VERSION = "m4.7-provisional-v1"

# PUTTER is deliberately absent: apply_environment_transform rejects PUTTER
# before this table is ever consulted (putting has no airborne aerodynamic
# regime to model) — see environment.py.
_DEFAULT_CLUB_CATEGORY_SENSITIVITY_MULTIPLIERS: Mapping[ClubCategory, float] = {
    ClubCategory.DRIVER: 0.85,
    ClubCategory.FAIRWAY_WOOD: 0.95,
    ClubCategory.HYBRID: 1.00,
    ClubCategory.IRON: 1.05,
    ClubCategory.WEDGE: 1.20,
    ClubCategory.OTHER: 1.00,
}


class EnvironmentTransformConfig(BaseModel):
    """Versioned, provisional coefficients for ``apply_environment_transform``.

    See the module docstring for the evidence-quality classification of
    every field. This model is structurally immutable (``frozen=True``).
    """

    model_config = ConfigDict(frozen=True)

    config_version: str = Field(default=ENVIRONMENT_TRANSFORM_CONFIG_VERSION, min_length=1)
    reference_carry_metres: float = Field(default=100.0, gt=0.0)
    reference_air_density_kg_per_m3: float = Field(default=1.225, gt=0.0)
    tailwind_sensitivity_metres_per_mps: float = Field(default=0.8, ge=0.0)
    headwind_sensitivity_metres_per_mps: float = Field(default=1.2, ge=0.0)
    crosswind_sensitivity_metres_per_mps: float = Field(default=0.6, ge=0.0)
    elevation_sensitivity: float = Field(default=1.0, ge=0.0)
    air_density_sensitivity: float = Field(default=1.0, ge=0.0)
    club_category_sensitivity_multipliers: Mapping[ClubCategory, float] = Field(
        default_factory=lambda: dict(_DEFAULT_CLUB_CATEGORY_SENSITIVITY_MULTIPLIERS)
    )


DEFAULT_ENVIRONMENT_TRANSFORM_CONFIG = EnvironmentTransformConfig()
