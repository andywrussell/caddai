"""Onboarding personalisation: initialise a golfer-specific ``PlayerShotDistribution``.

Implements the cold-start step of
docs/research/m4-probabilistic-golfer-model.md's "Cold-start initialization
and personal learning" section: combine `caddai.statistics.
resolve_population_prior`'s (ADR 0007) handicap/club-category population
prior with onboarding-supplied information (self-reported carry + its
provenance, common miss, shot shape) to build a `PlayerShotDistribution`
(ADR 0006). No `ShotRecord` learning, no partial pooling, no environment/
physics, no Monte Carlo, no strategy, no course-relative mapping — those are
later milestones.

**Aleatoric vs epistemic separation (binding for this module):** carry
provenance/confidence describes how much to *trust* the self-reported
`carry_location_metres` (epistemic uncertainty about a report) and never
feeds into `carry_scale_metres`/`lateral_scale_metres`/`correlation`/
`degrees_of_freedom` (aleatoric shot-to-shot variability, which comes only
from `resolve_population_prior`). Blending trust into scale/correlation/dof
would silently conflate "how sure are we of this number" with "how
variable is this golfer's shot production," which is exactly what ADR
0006/0007 keep separate.

No RNG, no `sample()`, no randomness, no Monte Carlo, no network calls —
resolution here is deterministic and side-effect free, same as
`resolve_population_prior`.
"""

import math
from enum import StrEnum

from pydantic import BaseModel

from caddai.statistics import (
    ClubCategory,
    PlayerShotDistribution,
    PopulationPriorResult,
    resolve_population_prior,
)


class CarryProvenance(StrEnum):
    """Where a golfer's self-reported carry distance came from.

    A distinct semantic axis from
    ``caddai.statistics.population_prior.PopulationPriorConfidence``/
    ``PopulationPriorProvenance`` — those describe a population-prior
    config cell's origin; this describes the quality of one golfer's
    self-report.
    """

    MEASURED = "measured"
    GPS_ESTIMATE = "gps_estimate"
    PERSONAL_ESTIMATE = "personal_estimate"


class CarryConfidence(StrEnum):
    """Qualitative confidence in a reported carry, derived from `CarryProvenance`.

    Metadata only — never feeds into `carry_scale_metres` or any other
    `PlayerShotDistribution` scale/correlation/dof field. See the module
    docstring's aleatoric/epistemic separation.
    """

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ShotShape(StrEnum):
    """A golfer's typical stock shot shape.

    Recorded on `OnboardingPersonalisationResult.shot_shape` for future use;
    not consumed by this module's bias logic.
    """

    STRAIGHT = "straight"
    DRAW = "draw"
    FADE = "fade"


class CommonMiss(StrEnum):
    """A golfer's typical miss direction, sign-only input.

    Matches the existing lateral sign convention used elsewhere (negative
    left, zero on-line, positive right of the intended target line,
    independent of handedness) — see
    ``DirectionalDispersion.lateral_bias_metres``.
    """

    LEFT = "left"
    NONE = "none"
    RIGHT = "right"


_CARRY_CONFIDENCE_BY_PROVENANCE: dict[CarryProvenance, CarryConfidence] = {
    CarryProvenance.MEASURED: CarryConfidence.HIGH,
    CarryProvenance.GPS_ESTIMATE: CarryConfidence.MODERATE,
    CarryProvenance.PERSONAL_ESTIMATE: CarryConfidence.LOW,
}

_COMMON_MISS_SIGN: dict[CommonMiss, float] = {
    CommonMiss.LEFT: -1.0,
    CommonMiss.NONE: 0.0,
    CommonMiss.RIGHT: 1.0,
}

ONBOARDING_CONFIG_VERSION = "m4.3-provisional-v1"

# Provisional, unvalidated common-miss bias magnitude pending calibration
# data — mirrors population_prior_config.py's own provisional numbers.
# Applied only via CommonMiss's sign; never derived from handicap, club, or
# any other input. Must be replaced by CaddAI's own calibration data (or a
# fitted/learned model) before being treated as authoritative — see ADR
# 0006/ADR 0007 and docs/research/m4-probabilistic-golfer-model.md.
ONBOARDING_COMMON_MISS_BIAS_METRES = 5.0


class OnboardingPersonalisationResult(BaseModel):
    """A golfer's onboarding-personalised `PlayerShotDistribution`, plus provenance.

    An additive result type (precedented by `PopulationPriorResult`, per
    ADR 0007's "adjacent type" allowance) rather than new fields bolted
    onto `PlayerShotDistribution` itself.

    `shot_shape` echoes the `personalise_shot_distribution` argument verbatim
    — recorded here so it is retrievable, but it has zero effect on
    `shot_distribution` or any other field. `onboarding_config_version`
    echoes `ONBOARDING_CONFIG_VERSION`, mirroring `PopulationPriorResult.
    config_version`'s traceability precedent (ADR 0007).
    """

    shot_distribution: PlayerShotDistribution
    carry_provenance: CarryProvenance
    carry_confidence: CarryConfidence
    shot_shape: ShotShape
    population_prior: PopulationPriorResult
    onboarding_config_version: str


def personalise_shot_distribution(
    *,
    handicap_index: float,
    club_category: ClubCategory,
    reported_carry_metres: float,
    carry_provenance: CarryProvenance,
    common_miss: CommonMiss,
    shot_shape: ShotShape = ShotShape.STRAIGHT,
) -> OnboardingPersonalisationResult:
    """Build a cold-start `PlayerShotDistribution` from onboarding information.

    `carry_location_metres` is set directly from `reported_carry_metres` —
    it strongly anchors location per the issue/research doc, since no
    defensible population carry-location prior exists to blend it toward.
    `lateral_bias_metres` is `ONBOARDING_COMMON_MISS_BIAS_METRES` scaled
    only by `common_miss`'s sign (`LEFT` -> negative, `NONE` -> exactly
    0.0, `RIGHT` -> positive). `carry_scale_metres`, `lateral_scale_metres`,
    `correlation`, and `degrees_of_freedom` are copied verbatim from
    `resolve_population_prior(...).parameters` — untouched by carry
    provenance/confidence or `shot_shape`, per the module docstring's
    aleatoric/epistemic separation. `shot_shape` is echoed onto the
    returned `OnboardingPersonalisationResult.shot_shape` unchanged — it
    has no effect on `shot_distribution` or any other field.

    Raises `ValueError` if `reported_carry_metres` is non-finite or not
    strictly positive. Propagates `resolve_population_prior`'s own
    `ValueError`/`PopulationPriorUnsupportedCategoryError` unmodified for
    an invalid `handicap_index` or an unsupported `club_category`
    (`ClubCategory.PUTTER` -> `DEFERRED`, `ClubCategory.OTHER` ->
    `NOT_MODELABLE`).
    """
    if not math.isfinite(reported_carry_metres) or reported_carry_metres <= 0.0:
        raise ValueError(
            f"reported_carry_metres must be finite and > 0, got {reported_carry_metres}"
        )

    population_prior = resolve_population_prior(handicap_index, club_category)
    parameters = population_prior.parameters

    shot_distribution = PlayerShotDistribution(
        family=parameters.family,
        carry_location_metres=reported_carry_metres,
        lateral_bias_metres=ONBOARDING_COMMON_MISS_BIAS_METRES * _COMMON_MISS_SIGN[common_miss],
        carry_scale_metres=parameters.carry_scale_metres,
        lateral_scale_metres=parameters.lateral_scale_metres,
        correlation=parameters.correlation,
        degrees_of_freedom=parameters.degrees_of_freedom,
    )

    return OnboardingPersonalisationResult(
        shot_distribution=shot_distribution,
        carry_provenance=carry_provenance,
        carry_confidence=_CARRY_CONFIDENCE_BY_PROVENANCE[carry_provenance],
        shot_shape=shot_shape,
        population_prior=population_prior,
        onboarding_config_version=ONBOARDING_CONFIG_VERSION,
    )
