"""``ShotRecord`` history -> partial-pooling update glue.

See GitHub issue #53 ("M4.5 — Personal partial-pooling player-model
updater") and
docs/plans/m4.5-personal-partial-pooling-updater.plan.md for the full
Architect-approved design. This module turns a golfer's raw
``ShotRecord`` history into the ``WeightedObservations``/
``WeightedJointObservations`` inputs
``caddai.statistics.personalisation.shrink_shot_distribution`` consumes,
then calls it. All shrinkage math itself lives in
``caddai.statistics.personalisation`` — this module is glue only.

**Architect Decision A (endpoint lateral vs intrinsic lateral, V1
limitation):** ``PlayerShotDistribution.lateral_bias_metres``/
``lateral_scale_metres`` are, strictly, parameters of the ball's *intrinsic*
lateral shot production. In V1, this module approximates that with
``ShotRecord.lateral_offset_metres`` — the lateral offset at the shot's
*final resting position*, not its first-landing/carry-point lateral
offset. This is a documented, accepted, replaceable approximation, not a
silent substitution: rollout after landing can change the lateral offset
between carry and final position, so this is a real (if likely small for
most full-swing shots) source of estimation error. Carry-space parameters
(``carry_location_metres``, ``carry_scale_metres``) are never derived from
endpoint data — only from genuinely observed ``observed_carry_metres``.
``ShotRecord.final_downrange_metres`` is not consumed anywhere in this
module.

**Architect Decision B (measurement-quality weighting):** every evidence
value contributes with an explicit numeric weight from
``MEASUREMENT_QUALITY_WEIGHTS`` (keyed by ``ShotMeasurementQuality``), not
by filtering records in/out. ``UNKNOWN`` quality contributes zero weight by
default — equivalent to the record not existing for that dimension.
``ShotMeasurementSource`` remains metadata-only in V1 (not a second
weighting axis).

Evidence selection is per-dimension, per-record: a record can contribute to
carry, lateral, both, or neither, without ever being discarded wholesale.
Joint (correlation) evidence requires both legs usable for the same
record, weighted by the ``min()`` of the two leg weights.
"""

from collections.abc import Mapping

from caddai.player.models import ShotMeasurementQuality, ShotRecord
from caddai.statistics.personalisation import (
    PersonalisationConfig,
    ShotDistributionUpdateResult,
    WeightedJointObservations,
    WeightedObservations,
    shrink_shot_distribution,
)
from caddai.statistics.shot_distribution import PlayerShotDistribution

# Provisional, unvalidated quality weights pending calibration data —
# mirrors population_prior_config.py's/onboarding.py's own provisional
# numbers. UNKNOWN contributes zero weight: equivalent to that dimension
# not existing for the record, not to discarding the whole record.
MEASUREMENT_QUALITY_WEIGHTS: Mapping[ShotMeasurementQuality, float] = {
    ShotMeasurementQuality.HIGH: 1.0,
    ShotMeasurementQuality.MODERATE: 0.6,
    ShotMeasurementQuality.LOW: 0.25,
    ShotMeasurementQuality.UNKNOWN: 0.0,
}

PLAYER_PERSONALISATION_CONFIG_VERSION = "m4.5-provisional-v1"


def build_shot_distribution_update_inputs(
    baseline_distribution: PlayerShotDistribution, club_name: str, shot_history: list[ShotRecord]
) -> tuple[WeightedObservations, WeightedObservations, WeightedJointObservations]:
    """Build the ``(carry, lateral, joint)`` weighted-evidence arrays for one club.

    Filters ``shot_history`` to records matching ``club_name``. For each
    matching record, ``lateral_offset_metres`` contributes to the lateral
    array weighted by ``MEASUREMENT_QUALITY_WEIGHTS[endpoint_measurement.
    quality]`` (only if that weight is > 0), and, when
    ``observed_carry_metres`` is not ``None``, it contributes to the carry
    array weighted by ``MEASUREMENT_QUALITY_WEIGHTS[observed_carry_
    measurement.quality]`` (only if that weight is > 0) —
    ``observed_carry_measurement`` is guaranteed non-``None`` whenever
    ``observed_carry_metres`` is set, per ``ShotRecord``'s own null-pairing
    invariant. ``final_downrange_metres`` is never read here (Architect
    Decision A). A record contributes a joint (correlation) leg only when
    *both* its carry and lateral weights are > 0, weighted by the
    ``min()`` of the two. ``baseline_distribution`` is accepted for
    signature symmetry with ``shrink_shot_distribution`` but is not
    otherwise used by this function.

    ``baseline_distribution`` must always be the same immutable cold-start
    distribution — the golfer's population-prior or onboarding-derived
    ``PlayerShotDistribution`` — and never a previously-returned
    ``ShotDistributionUpdateResult.shot_distribution``. This function
    recomputes the posterior from scratch on every call (batch
    recomputation); it does not accumulate sufficient statistics across
    calls. Always pair the same fixed baseline with the *complete* current
    eligible shot history:

        result_a = update_shot_distribution_from_history(baseline, club, history[:10])
        # shot 11 occurs
        result_b = update_shot_distribution_from_history(baseline, club, history[:11])  # correct

        # WRONG: feeding a previous result back in as the baseline silently
        # double-counts shots 1-10
        result_b = update_shot_distribution_from_history(
            result_a.shot_distribution, club, history[:11]
        )
    """

    carry_values: list[float] = []
    carry_weights: list[float] = []
    lateral_values: list[float] = []
    lateral_weights: list[float] = []
    joint_carry_values: list[float] = []
    joint_lateral_values: list[float] = []
    joint_weights: list[float] = []

    for record in shot_history:
        if record.club_name != club_name:
            continue

        endpoint_weight = MEASUREMENT_QUALITY_WEIGHTS[record.endpoint_measurement.quality]
        if endpoint_weight > 0.0:
            lateral_values.append(record.lateral_offset_metres)
            lateral_weights.append(endpoint_weight)

        carry_weight = 0.0
        if record.observed_carry_metres is not None:
            assert record.observed_carry_measurement is not None  # ShotRecord invariant
            carry_weight = MEASUREMENT_QUALITY_WEIGHTS[record.observed_carry_measurement.quality]
            if carry_weight > 0.0:
                carry_values.append(record.observed_carry_metres)
                carry_weights.append(carry_weight)
            if carry_weight > 0.0 and endpoint_weight > 0.0:
                joint_carry_values.append(record.observed_carry_metres)
                joint_lateral_values.append(record.lateral_offset_metres)
                joint_weights.append(min(carry_weight, endpoint_weight))

    return (
        WeightedObservations(values=tuple(carry_values), weights=tuple(carry_weights)),
        WeightedObservations(values=tuple(lateral_values), weights=tuple(lateral_weights)),
        WeightedJointObservations(
            carry_values=tuple(joint_carry_values),
            lateral_values=tuple(joint_lateral_values),
            weights=tuple(joint_weights),
        ),
    )


def update_shot_distribution_from_history(
    baseline_distribution: PlayerShotDistribution,
    club_name: str,
    shot_history: list[ShotRecord],
    config: PersonalisationConfig | None = None,
) -> ShotDistributionUpdateResult:
    """Shrink ``baseline_distribution`` toward ``club_name``'s evidence within ``shot_history``.

    Builds the shrinkage inputs via ``build_shot_distribution_update_inputs``,
    then delegates to ``shrink_shot_distribution``. When ``config`` is
    ``None``, ``shrink_shot_distribution``'s own default
    (``DEFAULT_PERSONALISATION_CONFIG``) applies.

    ``baseline_distribution`` must always be the same immutable cold-start
    distribution — the golfer's population-prior or onboarding-derived
    ``PlayerShotDistribution`` — and never a previously-returned
    ``ShotDistributionUpdateResult.shot_distribution``. This function
    recomputes the posterior from scratch on every call (batch
    recomputation); it does not accumulate sufficient statistics across
    calls. Always pair the same fixed baseline with the *complete* current
    eligible shot history:

        result_a = update_shot_distribution_from_history(baseline, club, history[:10])
        # shot 11 occurs
        result_b = update_shot_distribution_from_history(baseline, club, history[:11])  # correct

        # WRONG: feeding a previous result back in as the baseline silently
        # double-counts shots 1-10
        result_b = update_shot_distribution_from_history(
            result_a.shot_distribution, club, history[:11]
        )
    """
    carry_observations, lateral_observations, joint_observations = (
        build_shot_distribution_update_inputs(baseline_distribution, club_name, shot_history)
    )
    if config is None:
        return shrink_shot_distribution(
            baseline_distribution,
            carry_observations=carry_observations,
            lateral_observations=lateral_observations,
            joint_observations=joint_observations,
        )
    return shrink_shot_distribution(
        baseline_distribution,
        carry_observations=carry_observations,
        lateral_observations=lateral_observations,
        joint_observations=joint_observations,
        config=config,
    )
