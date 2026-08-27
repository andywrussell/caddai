"""Tests for onboarding personalisation of ``PlayerShotDistribution``.

See GitHub issue #51 ("M4.3 — Onboarding personalisation of
`PlayerShotDistribution`") and
docs/plans/m4.3-onboarding-personalisation.plan.md for the acceptance
criteria these tests are derived from, ADR 0006
(docs/adr/0006-player-shot-distribution-bivariate-student-t.md) for the
underlying bivariate Student-t construction, and ADR 0007
(docs/adr/0007-population-prior-replaceability.md) for the
``resolve_population_prior`` contract this module composes.

The single most important property under test is the
aleatoric/epistemic separation: ``carry_provenance`` (how a self-reported
carry was obtained) must never influence ``carry_scale_metres``,
``lateral_scale_metres``, ``correlation``, or ``degrees_of_freedom`` — those
come from the population prior alone. Provenance only ever affects the
metadata-only ``carry_confidence`` field. This module does not test
``ShotRecord`` learning, partial pooling, environment/physics, Monte Carlo
simulation, or strategy — those are out of scope for M4.3.
"""

import pytest

from caddai.player.onboarding import (
    ONBOARDING_COMMON_MISS_BIAS_STRENGTH,
    ONBOARDING_CONFIG_VERSION,
    CarryConfidence,
    CarryProvenance,
    CommonMiss,
    OnboardingPersonalisationResult,
    ShotShape,
    personalise_shot_distribution,
)
from caddai.statistics import (
    ClubCategory,
    ClubCategorySupportStatus,
    PopulationPriorUnsupportedCategoryError,
    ShotDistributionFamily,
    resolve_population_prior,
)

_SUPPORTED_CLUB_CATEGORIES = (
    ClubCategory.DRIVER,
    ClubCategory.FAIRWAY_WOOD,
    ClubCategory.HYBRID,
    ClubCategory.IRON,
    ClubCategory.WEDGE,
)

_UNSUPPORTED_CLUB_CATEGORIES = (ClubCategory.PUTTER, ClubCategory.OTHER)


def _personalise(**overrides: object) -> OnboardingPersonalisationResult:
    """Baseline valid call kwargs for ``personalise_shot_distribution``."""
    kwargs: dict[str, object] = {
        "handicap_index": 12.3,
        "club_category": ClubCategory.IRON,
        "reported_carry_metres": 150.0,
        "carry_provenance": CarryProvenance.MEASURED,
        "common_miss": CommonMiss.NONE,
    }
    kwargs.update(overrides)
    return personalise_shot_distribution(**kwargs)  # type: ignore[arg-type]


# --- Valid cold-start construction ------------------------------------------


@pytest.mark.parametrize("club_category", _SUPPORTED_CLUB_CATEGORIES)
def test_constructs_for_every_supported_club_category(club_category: ClubCategory) -> None:
    """Every supported full-swing category cold-starts without error."""
    result = _personalise(club_category=club_category)

    assert isinstance(result, OnboardingPersonalisationResult)
    assert result.shot_distribution.family == ShotDistributionFamily.BIVARIATE_STUDENT_T


# --- carry_location_metres ---------------------------------------------------


@pytest.mark.parametrize("reported_carry_metres", [1.0, 90.5, 150.0, 320.0])
def test_carry_location_equals_reported_carry_exactly(reported_carry_metres: float) -> None:
    """The self-reported carry is used directly as ``carry_location_metres``, with no
    trust-weighted blend toward any population carry-location prior."""
    result = _personalise(reported_carry_metres=reported_carry_metres)

    assert result.shot_distribution.carry_location_metres == pytest.approx(reported_carry_metres)


# --- lateral_bias_metres / common_miss ---------------------------------------


def test_common_miss_left_produces_negative_bias_of_configured_magnitude() -> None:
    """LEFT maps to exactly ``-ONBOARDING_COMMON_MISS_BIAS_STRENGTH *
    lateral_scale_metres``, matching the existing negative-left lateral sign
    convention."""
    expected_lateral_scale_metres = resolve_population_prior(
        12.3, ClubCategory.IRON
    ).parameters.lateral_scale_metres

    result = _personalise(common_miss=CommonMiss.LEFT)

    assert result.shot_distribution.lateral_bias_metres == pytest.approx(
        -ONBOARDING_COMMON_MISS_BIAS_STRENGTH * expected_lateral_scale_metres
    )


def test_common_miss_right_produces_positive_bias_of_configured_magnitude() -> None:
    """RIGHT maps to exactly ``+ONBOARDING_COMMON_MISS_BIAS_STRENGTH *
    lateral_scale_metres``."""
    expected_lateral_scale_metres = resolve_population_prior(
        12.3, ClubCategory.IRON
    ).parameters.lateral_scale_metres

    result = _personalise(common_miss=CommonMiss.RIGHT)

    assert result.shot_distribution.lateral_bias_metres == pytest.approx(
        ONBOARDING_COMMON_MISS_BIAS_STRENGTH * expected_lateral_scale_metres
    )


def test_common_miss_none_produces_exactly_zero_bias() -> None:
    """NONE maps to exactly ``0.0``, not merely a small value (0 times any
    lateral_scale_metres is exactly 0.0)."""
    result = _personalise(common_miss=CommonMiss.NONE)

    assert result.shot_distribution.lateral_bias_metres == 0.0


def test_onboarding_common_miss_bias_strength_is_strictly_positive() -> None:
    """The configured bias strength constant is a positive dimensionless value (sign is
    applied separately via ``CommonMiss``, never baked into the constant itself)."""
    assert ONBOARDING_COMMON_MISS_BIAS_STRENGTH > 0.0


def test_lateral_bias_scales_with_club_specific_lateral_scale() -> None:
    """Bias magnitude is club-sensitive: it scales with the resolved population prior's
    ``lateral_scale_metres`` rather than being a flat constant across all clubs."""
    handicap_index = 12.3

    wedge_expected_scale = resolve_population_prior(
        handicap_index, ClubCategory.WEDGE
    ).parameters.lateral_scale_metres
    driver_expected_scale = resolve_population_prior(
        handicap_index, ClubCategory.DRIVER
    ).parameters.lateral_scale_metres

    wedge_result = _personalise(
        handicap_index=handicap_index,
        club_category=ClubCategory.WEDGE,
        common_miss=CommonMiss.RIGHT,
    )
    driver_result = _personalise(
        handicap_index=handicap_index,
        club_category=ClubCategory.DRIVER,
        common_miss=CommonMiss.RIGHT,
    )

    assert wedge_result.shot_distribution.lateral_bias_metres == pytest.approx(
        ONBOARDING_COMMON_MISS_BIAS_STRENGTH * wedge_expected_scale
    )
    assert driver_result.shot_distribution.lateral_bias_metres == pytest.approx(
        ONBOARDING_COMMON_MISS_BIAS_STRENGTH * driver_expected_scale
    )
    assert wedge_result.shot_distribution.lateral_bias_metres != pytest.approx(
        driver_result.shot_distribution.lateral_bias_metres
    )


def test_lateral_scale_metres_is_unmutated_by_bias_formula() -> None:
    """Regression: deriving ``lateral_bias_metres`` from ``lateral_scale_metres`` must not
    alter the aleatoric ``lateral_scale_metres`` field itself."""
    handicap_index = 12.3
    club_category = ClubCategory.IRON
    expected_lateral_scale_metres = resolve_population_prior(
        handicap_index, club_category
    ).parameters.lateral_scale_metres

    result = _personalise(
        handicap_index=handicap_index,
        club_category=club_category,
        common_miss=CommonMiss.RIGHT,
    )

    assert result.shot_distribution.lateral_scale_metres == pytest.approx(
        expected_lateral_scale_metres
    )


# --- shot_shape has zero numeric effect --------------------------------------


@pytest.mark.parametrize("shot_shape", [ShotShape.STRAIGHT, ShotShape.DRAW, ShotShape.FADE])
def test_shot_shape_does_not_change_lateral_bias(shot_shape: ShotShape) -> None:
    """``shot_shape`` is recorded for future use but must not affect bias logic in M4.3."""
    baseline = _personalise(common_miss=CommonMiss.RIGHT, shot_shape=ShotShape.STRAIGHT)
    result = _personalise(common_miss=CommonMiss.RIGHT, shot_shape=shot_shape)

    assert result.shot_distribution.lateral_bias_metres == pytest.approx(
        baseline.shot_distribution.lateral_bias_metres
    )


@pytest.mark.parametrize("shot_shape", [ShotShape.STRAIGHT, ShotShape.DRAW, ShotShape.FADE])
def test_shot_shape_is_recorded_on_result(shot_shape: ShotShape) -> None:
    """``shot_shape`` is stored verbatim on the returned result, not discarded."""
    result = _personalise(shot_shape=shot_shape)

    assert result.shot_shape == shot_shape


def test_shot_shape_defaults_to_straight() -> None:
    """Omitting ``shot_shape`` behaves identically to passing ``ShotShape.STRAIGHT``."""
    default_result = _personalise()
    explicit_result = _personalise(shot_shape=ShotShape.STRAIGHT)

    assert (
        default_result.shot_distribution.model_dump()
        == explicit_result.shot_distribution.model_dump()
    )


# --- Aleatoric/epistemic separation: scale/correlation/dof from population prior alone ----


@pytest.mark.parametrize("club_category", _SUPPORTED_CLUB_CATEGORIES)
@pytest.mark.parametrize("handicap_index", [-5.0, 4.5, 12.0, 30.0])
def test_scale_correlation_and_dof_match_population_prior_exactly(
    handicap_index: float, club_category: ClubCategory
) -> None:
    """``carry_scale_metres``/``lateral_scale_metres``/``correlation``/``degrees_of_freedom``
    are copied verbatim from ``resolve_population_prior``'s output, independent of carry
    provenance, common miss, or shot shape."""
    expected = resolve_population_prior(handicap_index, club_category).parameters

    result = _personalise(
        handicap_index=handicap_index,
        club_category=club_category,
        carry_provenance=CarryProvenance.PERSONAL_ESTIMATE,
        common_miss=CommonMiss.LEFT,
        shot_shape=ShotShape.DRAW,
    )

    assert result.shot_distribution.carry_scale_metres == pytest.approx(expected.carry_scale_metres)
    assert result.shot_distribution.lateral_scale_metres == pytest.approx(
        expected.lateral_scale_metres
    )
    assert result.shot_distribution.correlation == pytest.approx(expected.correlation)
    assert result.shot_distribution.degrees_of_freedom == pytest.approx(expected.degrees_of_freedom)
    assert result.shot_distribution.family == expected.family


@pytest.mark.parametrize(
    "carry_provenance",
    [CarryProvenance.MEASURED, CarryProvenance.GPS_ESTIMATE, CarryProvenance.PERSONAL_ESTIMATE],
)
def test_carry_provenance_does_not_change_scale_correlation_or_dof(
    carry_provenance: CarryProvenance,
) -> None:
    """The mechanical proof of the aleatoric/epistemic separation: provenance never leaks
    into the shot-shape/scale parameters, for otherwise-identical inputs."""
    baseline = _personalise(carry_provenance=CarryProvenance.MEASURED)
    result = _personalise(carry_provenance=carry_provenance)

    assert result.shot_distribution.carry_scale_metres == pytest.approx(
        baseline.shot_distribution.carry_scale_metres
    )
    assert result.shot_distribution.lateral_scale_metres == pytest.approx(
        baseline.shot_distribution.lateral_scale_metres
    )
    assert result.shot_distribution.correlation == pytest.approx(
        baseline.shot_distribution.correlation
    )
    assert result.shot_distribution.degrees_of_freedom == pytest.approx(
        baseline.shot_distribution.degrees_of_freedom
    )


# --- carry_provenance -> carry_confidence mapping ----------------------------


@pytest.mark.parametrize(
    ("carry_provenance", "expected_confidence"),
    [
        (CarryProvenance.MEASURED, CarryConfidence.HIGH),
        (CarryProvenance.GPS_ESTIMATE, CarryConfidence.MODERATE),
        (CarryProvenance.PERSONAL_ESTIMATE, CarryConfidence.LOW),
    ],
)
def test_carry_provenance_maps_to_expected_confidence(
    carry_provenance: CarryProvenance, expected_confidence: CarryConfidence
) -> None:
    """Confidence is derived from provenance via a fixed mapping, not user-supplied."""
    result = _personalise(carry_provenance=carry_provenance)

    assert result.carry_confidence == expected_confidence
    assert result.carry_provenance == carry_provenance


# --- Unsupported club categories propagate PopulationPriorUnsupportedCategoryError ----


def test_putter_propagates_deferred_error_unmodified() -> None:
    """PUTTER is deferred, not invalid — the existing population-prior error must propagate
    unmodified, with no new onboarding-specific error type."""
    with pytest.raises(PopulationPriorUnsupportedCategoryError) as excinfo:
        _personalise(club_category=ClubCategory.PUTTER)

    error = excinfo.value
    assert isinstance(error, ValueError)
    assert error.club_category == ClubCategory.PUTTER
    assert error.status == ClubCategorySupportStatus.DEFERRED


def test_other_propagates_not_modelable_error_unmodified() -> None:
    """OTHER has no modelable mechanics; the same error type propagates with a different
    status."""
    with pytest.raises(PopulationPriorUnsupportedCategoryError) as excinfo:
        _personalise(club_category=ClubCategory.OTHER)

    error = excinfo.value
    assert isinstance(error, ValueError)
    assert error.club_category == ClubCategory.OTHER
    assert error.status == ClubCategorySupportStatus.NOT_MODELABLE


# --- Invalid reported_carry_metres -------------------------------------------


@pytest.mark.parametrize(
    "reported_carry_metres",
    [0.0, -0.0001, -150.0, float("nan"), float("inf"), float("-inf")],
)
def test_rejects_invalid_reported_carry_metres(reported_carry_metres: float) -> None:
    """Non-positive or non-finite reported carry is rejected at this boundary."""
    with pytest.raises(ValueError):
        _personalise(reported_carry_metres=reported_carry_metres)


# --- Invalid handicap_index propagates resolve_population_prior's ValueError ----


@pytest.mark.parametrize(
    "handicap_index", [float("nan"), float("inf"), float("-inf"), -10.01, 54.01, 100.0]
)
def test_rejects_invalid_handicap_index(handicap_index: float) -> None:
    """Out-of-range or non-finite handicap propagates ``resolve_population_prior``'s
    existing ``ValueError`` unmodified — no independent onboarding-specific validation."""
    with pytest.raises(ValueError):
        _personalise(handicap_index=handicap_index)


# --- Determinism --------------------------------------------------------------


def test_identical_inputs_produce_identical_results() -> None:
    """No RNG/hidden randomness: two calls with identical arguments produce equal output."""
    first = _personalise(
        handicap_index=8.25,
        club_category=ClubCategory.DRIVER,
        reported_carry_metres=210.0,
        carry_provenance=CarryProvenance.GPS_ESTIMATE,
        common_miss=CommonMiss.RIGHT,
        shot_shape=ShotShape.FADE,
    )
    second = _personalise(
        handicap_index=8.25,
        club_category=ClubCategory.DRIVER,
        reported_carry_metres=210.0,
        carry_provenance=CarryProvenance.GPS_ESTIMATE,
        common_miss=CommonMiss.RIGHT,
        shot_shape=ShotShape.FADE,
    )

    assert first.shot_distribution.model_dump() == second.shot_distribution.model_dump()
    assert first.carry_confidence == second.carry_confidence
    assert first.carry_provenance == second.carry_provenance


# --- population_prior field on the result ------------------------------------


def test_population_prior_field_matches_direct_resolve_call() -> None:
    """The echoed ``population_prior`` matches what ``resolve_population_prior`` itself
    returns for the same inputs."""
    handicap_index = 12.3
    club_category = ClubCategory.IRON
    expected = resolve_population_prior(handicap_index, club_category)

    result = _personalise(handicap_index=handicap_index, club_category=club_category)

    assert result.population_prior.parameters == expected.parameters
    assert result.population_prior.club_category == expected.club_category
    assert result.population_prior.handicap_index == pytest.approx(expected.handicap_index)


# --- family is copied through, not hardcoded independently -------------------


def test_family_is_copied_from_population_prior_parameters() -> None:
    """``family`` is copied from ``population_prior.parameters.family``, not an
    independently hardcoded value."""
    handicap_index = 30.0
    club_category = ClubCategory.WEDGE
    expected_family = resolve_population_prior(handicap_index, club_category).parameters.family

    result = _personalise(handicap_index=handicap_index, club_category=club_category)

    assert result.shot_distribution.family == expected_family


# --- Module-level constants ---------------------------------------------------


def test_onboarding_config_version_is_non_empty_string() -> None:
    """``ONBOARDING_CONFIG_VERSION`` is a non-empty, explicitly named version string."""
    assert isinstance(ONBOARDING_CONFIG_VERSION, str)
    assert len(ONBOARDING_CONFIG_VERSION) > 0


def test_result_onboarding_config_version_matches_module_constant() -> None:
    """``OnboardingPersonalisationResult.onboarding_config_version`` echoes
    ``ONBOARDING_CONFIG_VERSION``, mirroring ``PopulationPriorResult.config_version``'s
    traceability precedent (ADR 0007)."""
    result = _personalise()

    assert result.onboarding_config_version == ONBOARDING_CONFIG_VERSION


# --- Enum string values (JSON interop) ----------------------------------------


@pytest.mark.parametrize(
    ("member", "expected_value"),
    [
        (CarryProvenance.MEASURED, "measured"),
        (CarryProvenance.GPS_ESTIMATE, "gps_estimate"),
        (CarryProvenance.PERSONAL_ESTIMATE, "personal_estimate"),
    ],
)
def test_carry_provenance_string_values(member: CarryProvenance, expected_value: str) -> None:
    """``CarryProvenance`` members serialise to the documented plain strings."""
    assert member == expected_value


@pytest.mark.parametrize(
    ("member", "expected_value"),
    [
        (CarryConfidence.LOW, "low"),
        (CarryConfidence.MODERATE, "moderate"),
        (CarryConfidence.HIGH, "high"),
    ],
)
def test_carry_confidence_string_values(member: CarryConfidence, expected_value: str) -> None:
    """``CarryConfidence`` members serialise to the documented plain strings."""
    assert member == expected_value


@pytest.mark.parametrize(
    ("member", "expected_value"),
    [
        (ShotShape.STRAIGHT, "straight"),
        (ShotShape.DRAW, "draw"),
        (ShotShape.FADE, "fade"),
    ],
)
def test_shot_shape_string_values(member: ShotShape, expected_value: str) -> None:
    """``ShotShape`` members serialise to the documented plain strings."""
    assert member == expected_value


@pytest.mark.parametrize(
    ("member", "expected_value"),
    [
        (CommonMiss.LEFT, "left"),
        (CommonMiss.NONE, "none"),
        (CommonMiss.RIGHT, "right"),
    ],
)
def test_common_miss_string_values(member: CommonMiss, expected_value: str) -> None:
    """``CommonMiss`` members serialise to the documented plain strings."""
    assert member == expected_value
