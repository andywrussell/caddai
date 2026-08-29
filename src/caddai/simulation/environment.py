"""Deterministic environment/physics transform for a forward-modelled shot outcome.

See docs/plans/m4.7-environment-physics-transform.plan.md (GitHub issue
#55) for the design this implements, and ``environment_config.py`` for the
evidence-quality classification of every coefficient used here.

V1 wind-exposure validity domain: the wind-exposure hang-time proxy
(``scale`` below) is defined to be exactly ``0.0`` for any non-positive
intrinsic ``outcome.downrange_metres`` (zero or negative). Consequently
**all** wind effects — both the longitudinal (headwind/tailwind) and
lateral (crosswind) terms — are exactly zero whenever the intrinsic
outcome is non-positive, regardless of wind speed or direction. This is a
deliberate V1 restriction, not a bug: a topped/grounded/severely-mishit
ball is not modelled as meaningfully airborne-exposed to wind. Elevation
and air-density effects are unaffected by this restriction and still apply
to non-positive-downrange outcomes.

This module is policy-neutral by design: it only answers "if these
environmental conditions are applied, how do they affect this shot?" —
never "is applying environmental conditions allowed in this round?". There
is no enabled/disabled flag here and none should be added. To skip
environmental adjustment entirely (e.g. a future casual-vs-tournament
round mode), a caller simply does not call ``apply_environment_transform``
and uses the intrinsic ``ShotOutcome`` unchanged. Whether a given round
permits environmental assistance is a decision for a future round/rules
layer outside ``caddai.simulation`` (see docs/roadmap.md's M5.5 entry) —
never for this module.
"""

from caddai.simulation.environment_config import (
    DEFAULT_ENVIRONMENT_TRANSFORM_CONFIG,
    EnvironmentTransformConfig,
)
from caddai.simulation.models import EnvironmentInput, ShotOutcome
from caddai.statistics.models import ClubCategory


class EnvironmentTransformUnsupportedClubCategoryError(ValueError):
    """Raised by ``apply_environment_transform`` for ``ClubCategory.PUTTER``.

    Putting has no airborne aerodynamic regime for wind/elevation/air-density
    effects to act on, so this transform does not model it at all — this is
    conceptually related to
    ``caddai.statistics.population_prior.ClubCategorySupportStatus.DEFERRED``
    (a valid category with no dedicated model yet), but it is a distinct,
    local error type: it does not reuse or subclass
    ``caddai.statistics.population_prior.PopulationPriorUnsupportedCategoryError``,
    which belongs to a different subsystem's contract.
    """

    def __init__(self, club_category: ClubCategory) -> None:
        self.club_category = club_category
        super().__init__(
            f"club_category {club_category!r} has no airborne aerodynamic regime to "
            "model — putting is out of scope for apply_environment_transform"
        )


def apply_environment_transform(
    outcome: ShotOutcome,
    environment: EnvironmentInput,
    *,
    club_category: ClubCategory | None = None,
    config: EnvironmentTransformConfig = DEFAULT_ENVIRONMENT_TRANSFORM_CONFIG,
) -> ShotOutcome:
    """Apply a deterministic wind/elevation/air-density transform to a shot outcome.

    Returns a new ``ShotOutcome`` — neither ``outcome`` nor ``environment``
    is mutated (both are already frozen Pydantic models, so this is
    structurally guaranteed, not merely a convention). This function reads
    no ``caddai.player.PlayerShotDistribution`` state and contains no RNG or
    other stochastic behaviour: given the same arguments it always returns
    the same result (see ``environment_config.py`` for the versioned,
    static coefficients consulted).

    ``EnvironmentInput()`` (i.e. every field left at its default: zero wind,
    zero elevation delta, no air-density override) is an exact identity
    transform — every additive correction term evaluates to ``0.0`` and the
    returned ``ShotOutcome`` is field-for-field equal to ``outcome``.

    Each environmental feature can already be independently neutralized via
    ``EnvironmentInput``'s per-field defaults without any extra parameter:
    e.g. ``EnvironmentInput(elevation_delta_metres=10.0)`` leaves ``wind`` at
    its zero default, ``EnvironmentInput(wind=WindComponents(longitudinal_mps=5.0))``
    leaves elevation and air density at their no-op defaults. No flag is
    needed for partial or full disablement, and none should be added.

    Raises ``EnvironmentTransformUnsupportedClubCategoryError`` if
    ``club_category`` is ``ClubCategory.PUTTER`` (checked before any config
    table lookup). Any other ``club_category`` (including ``None`` and
    ``ClubCategory.OTHER``) is accepted; a category absent from
    ``config.club_category_sensitivity_multipliers`` falls back to a
    multiplier of ``1.0``.

    The resulting ``downrange_metres``/``lateral_metres`` are never clamped
    — a large enough headwind or elevation effect can legitimately drive
    ``downrange_metres`` negative. ``ShotOutcome``'s own finite-value
    validation is relied on to guarantee no silent NaN/inf ever propagates
    out of this function; a ``pydantic.ValidationError`` from that
    construction is allowed to propagate uncaught.

    For any non-positive intrinsic ``outcome.downrange_metres``, both wind
    terms (``downrange_wind_effect`` and ``lateral_wind_effect``) evaluate
    to exactly ``0.0`` — see the module docstring for the rationale.
    **M4.8's stochastic sampling layer should be aware:** shot outcomes
    drawn from the extreme negative tail of the intrinsic distribution will
    receive no wind adjustment under this transform.
    """
    if club_category is ClubCategory.PUTTER:
        raise EnvironmentTransformUnsupportedClubCategoryError(club_category)

    multiplier = (
        config.club_category_sensitivity_multipliers.get(club_category, 1.0)
        if club_category is not None
        else 1.0
    )

    # Hang-time proxy: longer intrinsic carries spend more time exposed to wind.
    # Floored at zero: see module docstring for the documented V1 wind-exposure validity domain.
    scale = max(outcome.downrange_metres, 0.0) / config.reference_carry_metres

    w_long = environment.wind.longitudinal_mps
    if w_long >= 0.0:
        downrange_wind_effect = (
            w_long * config.tailwind_sensitivity_metres_per_mps * scale * multiplier
        )
    else:
        downrange_wind_effect = (
            w_long * config.headwind_sensitivity_metres_per_mps * scale * multiplier
        )

    lateral_wind_effect = (
        environment.wind.lateral_mps
        * config.crosswind_sensitivity_metres_per_mps
        * scale
        * multiplier
    )

    # Club/carry-independent by design, unlike the wind terms above.
    elevation_effect = -environment.elevation_delta_metres * config.elevation_sensitivity

    if environment.air_density_kg_per_m3 is None:
        air_density_effect = 0.0
    else:
        density_ratio = config.reference_air_density_kg_per_m3 / environment.air_density_kg_per_m3
        air_density_effect = (
            outcome.downrange_metres * (density_ratio - 1.0) * config.air_density_sensitivity
        )

    transformed_downrange = (
        outcome.downrange_metres + downrange_wind_effect + elevation_effect + air_density_effect
    )
    transformed_lateral = outcome.lateral_metres + lateral_wind_effect

    return ShotOutcome(downrange_metres=transformed_downrange, lateral_metres=transformed_lateral)
