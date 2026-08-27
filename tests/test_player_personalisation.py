"""Tests for the ``ShotRecord`` -> arrays glue in ``caddai.player.personalisation``.

See GitHub issue #53 ("M4.5 — Personal partial-pooling player-model
updater") and docs/plans/m4.5-personal-partial-pooling-updater.plan.md for
the acceptance criteria these tests are derived from. This module tests
only the glue (``build_shot_distribution_update_inputs``,
``update_shot_distribution_from_history``, ``MEASUREMENT_QUALITY_WEIGHTS``)
— the pure shrinkage math is tested in
tests/test_statistics_personalisation.py.

Written before ``caddai.player.personalisation`` exists (TDD executable
spec) — every test here is expected to fail with an ``ImportError`` until
the Player Engineer implements it.

The single most important property under test is the carry-vs-downrange
semantic separation (Architect Decision A /
docs/plans/m4.5-personal-partial-pooling-updater.plan.md item 5):
``final_downrange_metres`` must never be treated as carry evidence, only
``observed_carry_metres`` may be, and ``lateral_offset_metres`` (the final
resting position) is the accepted V1 lateral evidence source.
"""

import pytest

from caddai.player.models import (
    ShotMeasurementMetadata,
    ShotMeasurementQuality,
    ShotMeasurementSource,
    ShotRecord,
)
from caddai.player.onboarding import CarryProvenance, CommonMiss, personalise_shot_distribution
from caddai.player.personalisation import (
    MEASUREMENT_QUALITY_WEIGHTS,
    PLAYER_PERSONALISATION_CONFIG_VERSION,
    build_shot_distribution_update_inputs,
    update_shot_distribution_from_history,
)
from caddai.statistics import ClubCategory, PlayerShotDistribution
from caddai.statistics.personalisation import (
    STATISTICS_PERSONALISATION_CONFIG_VERSION,
    DimensionUpdateOutcome,
    PersonalisationConfig,
)

_CLUB_NAME = "7 Iron"


# --- Helpers -----------------------------------------------------------------


def _prior(**overrides: float) -> PlayerShotDistribution:
    kwargs: dict[str, float] = {
        "carry_location_metres": 140.0,
        "lateral_bias_metres": 0.0,
        "carry_scale_metres": 8.0,
        "lateral_scale_metres": 4.0,
        "correlation": 0.1,
        "degrees_of_freedom": 6.0,
    }
    kwargs.update(overrides)
    return PlayerShotDistribution(**kwargs)


def _shot_record(
    *,
    club_name: str = _CLUB_NAME,
    final_downrange_metres: float = 140.0,
    lateral_offset_metres: float = 0.0,
    endpoint_quality: ShotMeasurementQuality = ShotMeasurementQuality.HIGH,
    observed_carry_metres: float | None = None,
    carry_quality: ShotMeasurementQuality | None = None,
) -> ShotRecord:
    """Build a ShotRecord; only attaches observed-carry metadata when a carry value exists,
    matching ShotRecord's own null-pairing invariant."""
    observed_carry_measurement = None
    if observed_carry_metres is not None:
        observed_carry_measurement = ShotMeasurementMetadata(
            source=ShotMeasurementSource.LAUNCH_MONITOR,
            quality=carry_quality or ShotMeasurementQuality.HIGH,
        )
    return ShotRecord(
        club_name=club_name,
        final_downrange_metres=final_downrange_metres,
        lateral_offset_metres=lateral_offset_metres,
        endpoint_measurement=ShotMeasurementMetadata(
            source=ShotMeasurementSource.GPS_DEVICE, quality=endpoint_quality
        ),
        observed_carry_metres=observed_carry_metres,
        observed_carry_measurement=observed_carry_measurement,
    )


# --- MEASUREMENT_QUALITY_WEIGHTS ----------------------------------------------


@pytest.mark.parametrize(
    ("quality", "expected_weight"),
    [
        (ShotMeasurementQuality.HIGH, 1.0),
        (ShotMeasurementQuality.MODERATE, 0.6),
        (ShotMeasurementQuality.LOW, 0.25),
        (ShotMeasurementQuality.UNKNOWN, 0.0),
    ],
)
def test_measurement_quality_weights_mapping(
    quality: ShotMeasurementQuality, expected_weight: float
) -> None:
    assert MEASUREMENT_QUALITY_WEIGHTS[quality] == pytest.approx(expected_weight)


def test_measurement_quality_weights_covers_every_quality_member() -> None:
    assert set(MEASUREMENT_QUALITY_WEIGHTS) == set(ShotMeasurementQuality)


def test_player_personalisation_config_version_is_nonempty_string() -> None:
    assert isinstance(PLAYER_PERSONALISATION_CONFIG_VERSION, str)
    assert len(PLAYER_PERSONALISATION_CONFIG_VERSION) > 0


# --- club_name filtering -------------------------------------------------------


def test_only_matching_club_name_records_are_used() -> None:
    prior = _prior()
    history = [
        _shot_record(club_name="7 Iron", observed_carry_metres=150.0),
        _shot_record(club_name="Driver", observed_carry_metres=250.0),
    ]

    carry_obs, _, _ = build_shot_distribution_update_inputs(prior, "7 Iron", history)

    assert carry_obs.values == (150.0,)


def test_no_matching_club_name_records_yields_no_evidence() -> None:
    prior = _prior()
    history = [_shot_record(club_name="Driver", observed_carry_metres=250.0)]

    result = update_shot_distribution_from_history(prior, "7 Iron", history)

    assert result.carry_location_outcome is DimensionUpdateOutcome.NO_EVIDENCE
    assert result.shot_distribution == prior


# --- Quality-weight mapping applied to real records --------------------------


def test_carry_weight_uses_observed_carry_measurement_quality() -> None:
    prior = _prior()
    history = [
        _shot_record(observed_carry_metres=150.0, carry_quality=ShotMeasurementQuality.MODERATE)
    ]

    carry_obs, _, _ = build_shot_distribution_update_inputs(prior, _CLUB_NAME, history)

    assert carry_obs.weights == (pytest.approx(0.6),)


def test_lateral_weight_uses_endpoint_measurement_quality() -> None:
    prior = _prior()
    history = [_shot_record(lateral_offset_metres=3.0, endpoint_quality=ShotMeasurementQuality.LOW)]

    _, lateral_obs, _ = build_shot_distribution_update_inputs(prior, _CLUB_NAME, history)

    assert lateral_obs.weights == (pytest.approx(0.25),)


# --- Carry-vs-downrange semantic separation -----------------------------------


def test_final_downrange_metres_is_never_used_as_carry_evidence() -> None:
    """A record with no genuine observed_carry_metres, but a large distinctive
    final_downrange_metres, must never leak into carry evidence."""
    prior = _prior(carry_location_metres=140.0)
    history = [
        _shot_record(
            final_downrange_metres=999.0,
            observed_carry_metres=None,
            endpoint_quality=ShotMeasurementQuality.UNKNOWN,
        )
    ]

    carry_obs, _, _ = build_shot_distribution_update_inputs(prior, _CLUB_NAME, history)
    result = update_shot_distribution_from_history(prior, _CLUB_NAME, history)

    assert carry_obs.values == ()
    assert result.carry_location_outcome is DimensionUpdateOutcome.NO_EVIDENCE
    assert result.shot_distribution.carry_location_metres == pytest.approx(
        prior.carry_location_metres
    )


def test_lateral_offset_metres_is_accepted_as_lateral_evidence() -> None:
    prior = _prior(lateral_bias_metres=0.0)
    history = [_shot_record(lateral_offset_metres=10.0) for _ in range(5)]

    result = update_shot_distribution_from_history(prior, _CLUB_NAME, history)

    assert result.lateral_bias_outcome is DimensionUpdateOutcome.UPDATED
    assert result.shot_distribution.lateral_bias_metres > prior.lateral_bias_metres


# --- Partial observations: dimension-specific, no whole-record discarding ----


def test_partial_record_with_only_carry_contributes_to_carry_dimension_only() -> None:
    prior = _prior()
    history = [
        _shot_record(
            observed_carry_metres=160.0,
            lateral_offset_metres=5.0,
            endpoint_quality=ShotMeasurementQuality.UNKNOWN,
        )
    ]

    carry_obs, lateral_obs, joint_obs = build_shot_distribution_update_inputs(
        prior, _CLUB_NAME, history
    )

    assert carry_obs.values == (160.0,)
    assert lateral_obs.values == ()
    assert joint_obs.carry_values == ()
    assert joint_obs.lateral_values == ()


def test_partial_record_with_only_endpoint_contributes_to_lateral_dimension_only() -> None:
    prior = _prior()
    history = [
        _shot_record(
            observed_carry_metres=None,
            lateral_offset_metres=-3.0,
            endpoint_quality=ShotMeasurementQuality.HIGH,
        )
    ]

    carry_obs, lateral_obs, joint_obs = build_shot_distribution_update_inputs(
        prior, _CLUB_NAME, history
    )

    assert carry_obs.values == ()
    assert lateral_obs.values == (-3.0,)
    assert joint_obs.carry_values == ()


def test_joint_weight_is_minimum_of_carry_and_lateral_weights() -> None:
    prior = _prior()
    history = [
        _shot_record(
            observed_carry_metres=150.0,
            carry_quality=ShotMeasurementQuality.HIGH,  # weight 1.0
            lateral_offset_metres=2.0,
            endpoint_quality=ShotMeasurementQuality.LOW,  # weight 0.25
        )
    ]

    _, _, joint_obs = build_shot_distribution_update_inputs(prior, _CLUB_NAME, history)

    assert joint_obs.carry_values == (150.0,)
    assert joint_obs.lateral_values == (2.0,)
    assert joint_obs.weights == (pytest.approx(0.25),)


def test_joint_evidence_excluded_when_either_leg_unusable() -> None:
    """A record contributing to only one dimension must never contribute a joint (correlation)
    leg — correlation evidence requires both legs usable for the same record."""
    prior = _prior()
    history = [
        _shot_record(observed_carry_metres=150.0, endpoint_quality=ShotMeasurementQuality.UNKNOWN),
        _shot_record(observed_carry_metres=None, lateral_offset_metres=2.0),
    ]

    _, _, joint_obs = build_shot_distribution_update_inputs(prior, _CLUB_NAME, history)

    assert joint_obs.carry_values == ()
    assert joint_obs.lateral_values == ()
    assert joint_obs.weights == ()


# --- UNKNOWN quality contributes nothing, same as an absent record ------------


def test_unknown_quality_record_contributes_nothing_same_as_absent() -> None:
    prior = _prior()
    baseline_history = [_shot_record(observed_carry_metres=150.0)]
    extra_unknown_record = _shot_record(
        observed_carry_metres=400.0,
        carry_quality=ShotMeasurementQuality.UNKNOWN,
        lateral_offset_metres=50.0,
        endpoint_quality=ShotMeasurementQuality.UNKNOWN,
    )

    baseline_result = update_shot_distribution_from_history(prior, _CLUB_NAME, baseline_history)
    with_unknown_result = update_shot_distribution_from_history(
        prior, _CLUB_NAME, [*baseline_history, extra_unknown_record]
    )

    assert with_unknown_result == baseline_result


# --- Determinism ----------------------------------------------------------------


def test_identical_inputs_produce_identical_results() -> None:
    prior = _prior()
    history = [
        _shot_record(observed_carry_metres=150.0),
        _shot_record(
            lateral_offset_metres=-2.0,
            endpoint_quality=ShotMeasurementQuality.MODERATE,
        ),
    ]

    result_a = update_shot_distribution_from_history(prior, _CLUB_NAME, history)
    result_b = update_shot_distribution_from_history(prior, _CLUB_NAME, history)

    assert result_a == result_b


# --- Common-miss bias superseded by sufficient contradicting evidence --------


def test_sufficient_contradicting_evidence_supersedes_onboarding_common_miss_bias() -> None:
    """An onboarding-derived RIGHT common-miss bias must be overridable by enough strongly
    LEFT personal evidence, moving the posterior bias toward/past zero."""
    onboarding_result = personalise_shot_distribution(
        handicap_index=18.0,
        club_category=ClubCategory.IRON,
        reported_carry_metres=140.0,
        carry_provenance=CarryProvenance.PERSONAL_ESTIMATE,
        common_miss=CommonMiss.RIGHT,
    )
    prior = onboarding_result.shot_distribution
    assert prior.lateral_bias_metres > 0.0

    history = [_shot_record(lateral_offset_metres=-15.0) for _ in range(100)]

    result = update_shot_distribution_from_history(prior, _CLUB_NAME, history)

    assert result.shot_distribution.lateral_bias_metres < 0.0


# --- Quality-weighted differential influence ----------------------------------


def test_higher_quality_evidence_has_stronger_influence_than_lower_quality() -> None:
    prior = _prior(carry_location_metres=140.0)
    sample_value = 200.0

    high_quality_history = [
        _shot_record(observed_carry_metres=sample_value, carry_quality=ShotMeasurementQuality.HIGH)
    ]
    moderate_quality_history = [
        _shot_record(
            observed_carry_metres=sample_value, carry_quality=ShotMeasurementQuality.MODERATE
        )
    ]
    low_quality_history = [
        _shot_record(observed_carry_metres=sample_value, carry_quality=ShotMeasurementQuality.LOW)
    ]

    high_result = update_shot_distribution_from_history(prior, _CLUB_NAME, high_quality_history)
    moderate_result = update_shot_distribution_from_history(
        prior, _CLUB_NAME, moderate_quality_history
    )
    low_result = update_shot_distribution_from_history(prior, _CLUB_NAME, low_quality_history)

    high_distance = abs(
        high_result.shot_distribution.carry_location_metres - prior.carry_location_metres
    )
    moderate_distance = abs(
        moderate_result.shot_distribution.carry_location_metres - prior.carry_location_metres
    )
    low_distance = abs(
        low_result.shot_distribution.carry_location_metres - prior.carry_location_metres
    )

    assert high_distance > moderate_distance > low_distance > 0.0


# --- Empty history, config propagation ------------------------------------------


def test_empty_shot_history_yields_no_evidence_outcomes() -> None:
    prior = _prior()

    result = update_shot_distribution_from_history(prior, _CLUB_NAME, [])

    assert result.carry_location_outcome is DimensionUpdateOutcome.NO_EVIDENCE
    assert result.shot_distribution == prior


def test_default_config_used_when_config_argument_omitted() -> None:
    prior = _prior()
    history = [_shot_record(observed_carry_metres=150.0)]

    result = update_shot_distribution_from_history(prior, _CLUB_NAME, history)

    assert result.config_version == STATISTICS_PERSONALISATION_CONFIG_VERSION


def test_custom_config_overrides_default() -> None:
    """A config with a much larger location prior pseudo-count should shrink evidence toward
    the prior far more strongly than the default config does."""
    prior = _prior(carry_location_metres=140.0)
    history = [_shot_record(observed_carry_metres=200.0)]
    strong_prior_config = PersonalisationConfig(
        config_version="test-strong-prior",
        location_prior_pseudo_count=10_000.0,
        dispersion_prior_pseudo_count=30.0,
        dispersion_min_effective_observations=2.0,
        correlation_prior_pseudo_count=60.0,
        correlation_min_effective_observations=40.0,
    )

    default_result = update_shot_distribution_from_history(prior, _CLUB_NAME, history)
    strong_prior_result = update_shot_distribution_from_history(
        prior, _CLUB_NAME, history, config=strong_prior_config
    )

    default_distance = abs(
        default_result.shot_distribution.carry_location_metres - prior.carry_location_metres
    )
    strong_prior_distance = abs(
        strong_prior_result.shot_distribution.carry_location_metres - prior.carry_location_metres
    )
    assert strong_prior_distance < default_distance


# --- Genuine severe shot retained, no outlier filtering -----------------------


def test_genuine_severe_shot_pulls_posterior_and_is_not_excluded() -> None:
    prior = _prior(carry_location_metres=140.0)
    normal_history = [_shot_record(observed_carry_metres=140.0) for _ in range(20)]
    severe_shot = _shot_record(observed_carry_metres=40.0)

    baseline_result = update_shot_distribution_from_history(prior, _CLUB_NAME, normal_history)
    with_severe_result = update_shot_distribution_from_history(
        prior, _CLUB_NAME, [*normal_history, severe_shot]
    )

    assert (
        with_severe_result.shot_distribution.carry_location_metres
        < baseline_result.shot_distribution.carry_location_metres
    )


# --- Large, adversarial evidence set: invariant stress test -------------------


def test_large_history_still_yields_a_valid_distribution() -> None:
    prior = _prior()
    history = [
        _shot_record(
            observed_carry_metres=140.0 + (i % 3) * 0.01,
            lateral_offset_metres=(i % 5) * 0.01 - 0.02,
        )
        for i in range(500)
    ]

    result = update_shot_distribution_from_history(prior, _CLUB_NAME, history)

    distribution = result.shot_distribution
    assert distribution.carry_scale_metres > 0.0
    assert distribution.lateral_scale_metres > 0.0
    assert -1.0 < distribution.correlation < 1.0
    assert distribution.degrees_of_freedom > 2.0
