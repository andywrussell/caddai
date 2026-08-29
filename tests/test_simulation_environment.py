"""Tests for the M4.7 environment/physics transform (``caddai.simulation``).

See GitHub issue #55 ("M4.7 — Environment/physics transformation layer and
simulation bootstrap") and
docs/plans/m4.7-environment-physics-transform.plan.md for the acceptance
criteria these tests are derived from.

Architecture-boundary coverage (no forbidden/out-of-scope imports from
``caddai.simulation``) lives in ``tests/test_architecture_boundaries.py``'s
``simulation`` entry — not duplicated here.
"""

import pytest
from pydantic import ValidationError

from caddai.simulation import (
    ENVIRONMENT_TRANSFORM_CONFIG_VERSION,
    EnvironmentInput,
    EnvironmentTransformConfig,
    EnvironmentTransformUnsupportedClubCategoryError,
    ShotOutcome,
    WindComponents,
    apply_environment_transform,
)
from caddai.statistics.models import ClubCategory

BASELINE_OUTCOME = ShotOutcome(downrange_metres=150.0, lateral_metres=2.0)


# --- Identity transform ------------------------------------------------------


def test_reference_environment_is_exact_identity_transform() -> None:
    """EnvironmentInput() (all defaults) leaves the outcome exactly unchanged."""
    result = apply_environment_transform(BASELINE_OUTCOME, EnvironmentInput())

    assert result.downrange_metres == BASELINE_OUTCOME.downrange_metres
    assert result.lateral_metres == BASELINE_OUTCOME.lateral_metres


# --- Headwind / tailwind -----------------------------------------------------


def test_headwind_reduces_downrange_vs_baseline() -> None:
    """A headwind (negative longitudinal_mps) reduces downrange vs. zero wind."""
    baseline = apply_environment_transform(BASELINE_OUTCOME, EnvironmentInput())
    headwind_environment = EnvironmentInput(wind=WindComponents(longitudinal_mps=-5.0))
    result = apply_environment_transform(BASELINE_OUTCOME, headwind_environment)

    assert result.downrange_metres < baseline.downrange_metres


def test_stronger_headwind_has_larger_downrange_reducing_effect() -> None:
    """A stronger headwind reduces downrange strictly more than a weaker one."""
    weak_environment = EnvironmentInput(wind=WindComponents(longitudinal_mps=-3.0))
    strong_environment = EnvironmentInput(wind=WindComponents(longitudinal_mps=-8.0))

    weak_result = apply_environment_transform(BASELINE_OUTCOME, weak_environment)
    strong_result = apply_environment_transform(BASELINE_OUTCOME, strong_environment)

    assert strong_result.downrange_metres < weak_result.downrange_metres


def test_tailwind_increases_downrange_vs_baseline() -> None:
    """A tailwind (positive longitudinal_mps) increases downrange vs. zero wind."""
    baseline = apply_environment_transform(BASELINE_OUTCOME, EnvironmentInput())
    tailwind_environment = EnvironmentInput(wind=WindComponents(longitudinal_mps=5.0))
    result = apply_environment_transform(BASELINE_OUTCOME, tailwind_environment)

    assert result.downrange_metres > baseline.downrange_metres


def test_stronger_tailwind_has_larger_downrange_increasing_effect() -> None:
    """A stronger tailwind increases downrange strictly more than a weaker one."""
    weak_environment = EnvironmentInput(wind=WindComponents(longitudinal_mps=3.0))
    strong_environment = EnvironmentInput(wind=WindComponents(longitudinal_mps=8.0))

    weak_result = apply_environment_transform(BASELINE_OUTCOME, weak_environment)
    strong_result = apply_environment_transform(BASELINE_OUTCOME, strong_environment)

    assert strong_result.downrange_metres > weak_result.downrange_metres


def test_headwind_and_tailwind_effect_magnitudes_are_asymmetric() -> None:
    """A -N headwind effect magnitude differs from a +N tailwind effect magnitude.

    Proves the asymmetric headwind/tailwind coefficient design decision was
    actually implemented, not accidentally symmetric.
    """
    baseline = apply_environment_transform(BASELINE_OUTCOME, EnvironmentInput())
    headwind_result = apply_environment_transform(
        BASELINE_OUTCOME, EnvironmentInput(wind=WindComponents(longitudinal_mps=-6.0))
    )
    tailwind_result = apply_environment_transform(
        BASELINE_OUTCOME, EnvironmentInput(wind=WindComponents(longitudinal_mps=6.0))
    )

    headwind_effect_magnitude = abs(headwind_result.downrange_metres - baseline.downrange_metres)
    tailwind_effect_magnitude = abs(tailwind_result.downrange_metres - baseline.downrange_metres)

    assert headwind_effect_magnitude != pytest.approx(tailwind_effect_magnitude)
    assert headwind_effect_magnitude > tailwind_effect_magnitude


# --- Crosswind ----------------------------------------------------------------


def test_left_crosswind_shifts_lateral_outcome_left() -> None:
    """A left crosswind (negative lateral_mps) shifts the lateral outcome negative."""
    baseline = apply_environment_transform(BASELINE_OUTCOME, EnvironmentInput())
    left_crosswind = EnvironmentInput(wind=WindComponents(lateral_mps=-4.0))
    result = apply_environment_transform(BASELINE_OUTCOME, left_crosswind)

    assert result.lateral_metres < baseline.lateral_metres


def test_right_crosswind_shifts_lateral_outcome_right() -> None:
    """A right crosswind (positive lateral_mps) shifts the lateral outcome positive."""
    baseline = apply_environment_transform(BASELINE_OUTCOME, EnvironmentInput())
    right_crosswind = EnvironmentInput(wind=WindComponents(lateral_mps=4.0))
    result = apply_environment_transform(BASELINE_OUTCOME, right_crosswind)

    assert result.lateral_metres > baseline.lateral_metres


def test_stronger_crosswind_has_larger_lateral_shift() -> None:
    """A stronger crosswind gives a strictly larger lateral shift than a weaker one."""
    weak_environment = EnvironmentInput(wind=WindComponents(lateral_mps=2.0))
    strong_environment = EnvironmentInput(wind=WindComponents(lateral_mps=7.0))

    weak_result = apply_environment_transform(BASELINE_OUTCOME, weak_environment)
    strong_result = apply_environment_transform(BASELINE_OUTCOME, strong_environment)

    assert strong_result.lateral_metres > weak_result.lateral_metres


def test_zero_crosswind_leaves_lateral_outcome_exactly_unchanged() -> None:
    """lateral_mps == 0.0 leaves the lateral outcome exactly unchanged."""
    environment = EnvironmentInput(wind=WindComponents(lateral_mps=0.0, longitudinal_mps=5.0))
    result = apply_environment_transform(BASELINE_OUTCOME, environment)

    assert result.lateral_metres == BASELINE_OUTCOME.lateral_metres


# --- Elevation ------------------------------------------------------------


def test_uphill_reduces_downrange_vs_baseline() -> None:
    """A positive elevation_delta_metres (uphill) reduces downrange vs. zero elevation."""
    baseline = apply_environment_transform(BASELINE_OUTCOME, EnvironmentInput())
    uphill_environment = EnvironmentInput(elevation_delta_metres=10.0)
    result = apply_environment_transform(BASELINE_OUTCOME, uphill_environment)

    assert result.downrange_metres < baseline.downrange_metres


def test_downhill_increases_downrange_vs_baseline() -> None:
    """A negative elevation_delta_metres (downhill) increases downrange vs. zero elevation."""
    baseline = apply_environment_transform(BASELINE_OUTCOME, EnvironmentInput())
    downhill_environment = EnvironmentInput(elevation_delta_metres=-10.0)
    result = apply_environment_transform(BASELINE_OUTCOME, downhill_environment)

    assert result.downrange_metres > baseline.downrange_metres


# --- Air density ------------------------------------------------------------


def test_air_density_none_gives_no_effect() -> None:
    """air_density_kg_per_m3=None matches the baseline with no air-density override."""
    baseline = apply_environment_transform(BASELINE_OUTCOME, EnvironmentInput())
    explicit_none_environment = EnvironmentInput(air_density_kg_per_m3=None)
    result = apply_environment_transform(BASELINE_OUTCOME, explicit_none_environment)

    assert result.downrange_metres == baseline.downrange_metres
    assert result.lateral_metres == baseline.lateral_metres


def test_below_reference_air_density_increases_downrange() -> None:
    """A below-reference air density (thinner air) increases downrange vs. reference."""
    reference_result = apply_environment_transform(
        BASELINE_OUTCOME, EnvironmentInput(air_density_kg_per_m3=1.225)
    )
    thin_air_result = apply_environment_transform(
        BASELINE_OUTCOME, EnvironmentInput(air_density_kg_per_m3=1.0)
    )

    assert thin_air_result.downrange_metres > reference_result.downrange_metres


def test_above_reference_air_density_decreases_downrange() -> None:
    """An above-reference air density (thicker air) decreases downrange vs. reference."""
    reference_result = apply_environment_transform(
        BASELINE_OUTCOME, EnvironmentInput(air_density_kg_per_m3=1.225)
    )
    thick_air_result = apply_environment_transform(
        BASELINE_OUTCOME, EnvironmentInput(air_density_kg_per_m3=1.4)
    )

    assert thick_air_result.downrange_metres < reference_result.downrange_metres


# --- Club-category sensitivity ------------------------------------------------


def test_different_club_categories_give_different_wind_effect_magnitudes() -> None:
    """The same wind input produces different-magnitude effects for DRIVER vs WEDGE."""
    environment = EnvironmentInput(wind=WindComponents(longitudinal_mps=6.0, lateral_mps=3.0))

    driver_result = apply_environment_transform(
        BASELINE_OUTCOME, environment, club_category=ClubCategory.DRIVER
    )
    wedge_result = apply_environment_transform(
        BASELINE_OUTCOME, environment, club_category=ClubCategory.WEDGE
    )

    assert driver_result.downrange_metres != wedge_result.downrange_metres
    assert driver_result.lateral_metres != wedge_result.lateral_metres


def test_none_and_other_club_category_produce_identical_results() -> None:
    """club_category=None and club_category=ClubCategory.OTHER behave identically."""
    environment = EnvironmentInput(wind=WindComponents(longitudinal_mps=6.0, lateral_mps=3.0))

    none_result = apply_environment_transform(BASELINE_OUTCOME, environment, club_category=None)
    other_result = apply_environment_transform(
        BASELINE_OUTCOME, environment, club_category=ClubCategory.OTHER
    )

    assert none_result == other_result


def test_putter_club_category_raises() -> None:
    """club_category=ClubCategory.PUTTER raises EnvironmentTransformUnsupportedClubCategoryError."""
    with pytest.raises(EnvironmentTransformUnsupportedClubCategoryError) as exc_info:
        apply_environment_transform(
            BASELINE_OUTCOME, EnvironmentInput(), club_category=ClubCategory.PUTTER
        )

    assert exc_info.value.club_category is ClubCategory.PUTTER


# --- Determinism and immutability --------------------------------------------


def test_repeated_calls_with_identical_inputs_are_identical() -> None:
    """Calling apply_environment_transform twice with identical inputs is deterministic."""
    environment = EnvironmentInput(
        wind=WindComponents(longitudinal_mps=-4.0, lateral_mps=2.5),
        elevation_delta_metres=5.0,
        air_density_kg_per_m3=1.1,
    )

    first = apply_environment_transform(
        BASELINE_OUTCOME, environment, club_category=ClubCategory.IRON
    )
    second = apply_environment_transform(
        BASELINE_OUTCOME, environment, club_category=ClubCategory.IRON
    )

    assert first == second


def test_inputs_are_unchanged_after_call() -> None:
    """Input ShotOutcome/EnvironmentInput instances are unchanged after the call."""
    outcome = ShotOutcome(downrange_metres=120.0, lateral_metres=-3.0)
    environment = EnvironmentInput(
        wind=WindComponents(longitudinal_mps=4.0, lateral_mps=-1.5),
        elevation_delta_metres=-8.0,
        air_density_kg_per_m3=1.3,
    )

    apply_environment_transform(outcome, environment, club_category=ClubCategory.HYBRID)

    assert outcome.downrange_metres == 120.0
    assert outcome.lateral_metres == -3.0
    assert environment.wind.longitudinal_mps == 4.0
    assert environment.wind.lateral_mps == -1.5
    assert environment.elevation_delta_metres == -8.0
    assert environment.air_density_kg_per_m3 == 1.3


# --- Finite-value validation --------------------------------------------------


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
def test_wind_components_rejects_non_finite_values(bad_value: float) -> None:
    """WindComponents rejects NaN/inf in either field."""
    with pytest.raises(ValidationError):
        WindComponents(longitudinal_mps=bad_value)
    with pytest.raises(ValidationError):
        WindComponents(lateral_mps=bad_value)


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
def test_environment_input_rejects_non_finite_values(bad_value: float) -> None:
    """EnvironmentInput rejects NaN/inf in elevation_delta_metres/air_density_kg_per_m3."""
    with pytest.raises(ValidationError):
        EnvironmentInput(elevation_delta_metres=bad_value)
    with pytest.raises(ValidationError):
        EnvironmentInput(air_density_kg_per_m3=bad_value)


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
def test_shot_outcome_rejects_non_finite_values(bad_value: float) -> None:
    """ShotOutcome rejects NaN/inf in either field."""
    with pytest.raises(ValidationError):
        ShotOutcome(downrange_metres=bad_value, lateral_metres=0.0)
    with pytest.raises(ValidationError):
        ShotOutcome(downrange_metres=0.0, lateral_metres=bad_value)


# --- Config validation/versioning --------------------------------------------


def test_default_config_version_matches_module_constant() -> None:
    """EnvironmentTransformConfig's default config_version matches the module constant."""
    config = EnvironmentTransformConfig()

    assert config.config_version == ENVIRONMENT_TRANSFORM_CONFIG_VERSION


def test_negative_tailwind_sensitivity_is_rejected() -> None:
    """An out-of-bounds coefficient (negative tailwind sensitivity) raises ValidationError."""
    with pytest.raises(ValidationError):
        EnvironmentTransformConfig(tailwind_sensitivity_metres_per_mps=-1.0)


def test_negative_elevation_sensitivity_is_rejected() -> None:
    """An out-of-bounds coefficient (negative elevation sensitivity) raises ValidationError."""
    with pytest.raises(ValidationError):
        EnvironmentTransformConfig(elevation_sensitivity=-1.0)


def test_negative_air_density_sensitivity_is_rejected() -> None:
    """An out-of-bounds coefficient (negative air-density sensitivity) raises ValidationError."""
    with pytest.raises(ValidationError):
        EnvironmentTransformConfig(air_density_sensitivity=-1.0)


# --- Negative downrange is preserved, not clamped -----------------------------


def test_negative_transformed_downrange_is_not_clamped() -> None:
    """A negative intrinsic downrange plus a strong headwind stays negative, unclamped."""
    small_negative_outcome = ShotOutcome(downrange_metres=-2.0, lateral_metres=0.0)
    strong_headwind = EnvironmentInput(wind=WindComponents(longitudinal_mps=-20.0))

    result = apply_environment_transform(small_negative_outcome, strong_headwind)

    # scale is floored at zero for a negative intrinsic outcome, so the wind
    # term contributes nothing here; downrange stays exactly at its intrinsic
    # (negative) value and is not clamped to 0.0.
    assert result.downrange_metres == pytest.approx(-2.0)
    assert result.downrange_metres != 0.0


def test_negative_transformed_downrange_from_elevation_is_not_clamped() -> None:
    """A small positive intrinsic downrange plus strong uphill can go negative, unclamped."""
    small_outcome = ShotOutcome(downrange_metres=5.0, lateral_metres=0.0)
    strong_uphill = EnvironmentInput(elevation_delta_metres=50.0)

    result = apply_environment_transform(small_outcome, strong_uphill)

    assert result.downrange_metres < 0.0
