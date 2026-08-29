"""Tests for the ``PlayerShotDistribution`` domain type.

See GitHub issue #49 ("M4.1 — PlayerShotDistribution domain type") and
docs/plans/m4.1-player-shot-distribution.plan.md for the acceptance
criteria these tests are derived from, and ADR 0006
(docs/adr/0006-player-shot-distribution-bivariate-student-t.md) for the
underlying bivariate Student-t construction.

``PlayerShotDistribution`` diverges intentionally from M3's
``CarryDistribution``/``DirectionalDispersion``: ``carry_scale_metres`` and
``lateral_scale_metres`` are strictly positive (zero is rejected, unlike
M3's stddev fields which allow zero as a "no data yet" placeholder),
``correlation`` must lie in the open interval ``(-1, 1)`` (exact +/-1 makes
the 2x2 scale matrix singular), and ``degrees_of_freedom`` must be strictly
greater than 2 (the covariance of the ADR 0006 construction is only finite
for ``nu > 2``). The bulk of this module does not test sampling,
``PopulationPrior``, or ``Club``/``Player`` composition — those were out of
scope for M4.1.

The final section of this module (below the "M4.6" marker) additionally
covers GitHub issue #54 ("M4.6 — Compose ``PlayerShotDistribution`` into
Club/Player") per docs/plans/m4.6-compose-shot-distribution.plan.md: the
``caddai.player.shot_distribution`` composition/read-path glue
(``compose_club_shot_distribution``/``resolve_current_shot_distribution``).
Those tests are written against the plan's documented signatures before
``caddai.player.shot_distribution`` necessarily exists (TDD executable
spec) — expected to fail with an ``ImportError`` until the Player
Engineer's parallel M4.6 implementation lands.
"""

import math

import pytest
from pydantic import ValidationError

from caddai.player import (
    CarryProvenance,
    Club,
    ClubCategory,
    ClubShotDistributionComposition,
    ClubShotDistributionResolution,
    CommonMiss,
    OnboardingPersonalisationResult,
    ShotMeasurementMetadata,
    ShotMeasurementQuality,
    ShotMeasurementSource,
    ShotRecord,
    compose_club_shot_distribution,
    resolve_current_shot_distribution,
)
from caddai.statistics import (
    CarryDistribution,
    ClubCategorySupportStatus,
    DirectionalDispersion,
    PopulationPriorUnsupportedCategoryError,
)
from caddai.statistics.shot_distribution import (
    PlayerShotDistribution,
    ShotDistributionFamily,
)


def _valid_kwargs(**overrides: float) -> dict[str, float]:
    """Baseline valid constructor kwargs for a typical shot distribution."""
    kwargs: dict[str, float] = {
        "carry_location_metres": 140.0,
        "lateral_bias_metres": 1.5,
        "carry_scale_metres": 8.0,
        "lateral_scale_metres": 4.0,
        "correlation": 0.2,
        "degrees_of_freedom": 6.0,
    }
    kwargs.update(overrides)
    return kwargs


# --- Construction and defaults ---------------------------------------------


def test_constructs_with_typical_values() -> None:
    """A physically plausible bivariate Student-t shot distribution is accepted."""
    distribution = PlayerShotDistribution(**_valid_kwargs())

    assert distribution.carry_location_metres == pytest.approx(140.0)
    assert distribution.lateral_bias_metres == pytest.approx(1.5)
    assert distribution.carry_scale_metres == pytest.approx(8.0)
    assert distribution.lateral_scale_metres == pytest.approx(4.0)
    assert distribution.correlation == pytest.approx(0.2)
    assert distribution.degrees_of_freedom == pytest.approx(6.0)


def test_family_defaults_to_bivariate_student_t() -> None:
    """Omitting ``family`` defaults to the only currently-supported family."""
    distribution = PlayerShotDistribution(**_valid_kwargs())

    assert distribution.family == ShotDistributionFamily.BIVARIATE_STUDENT_T


def test_family_accepts_explicit_bivariate_student_t() -> None:
    """Explicitly passing the family member round-trips unchanged."""
    distribution = PlayerShotDistribution(
        family=ShotDistributionFamily.BIVARIATE_STUDENT_T, **_valid_kwargs()
    )

    assert distribution.family == ShotDistributionFamily.BIVARIATE_STUDENT_T


# --- Immutability (frozen) ----------------------------------------------------


def test_assigning_to_carry_location_metres_raises() -> None:
    """The model is frozen: attribute assignment after construction is rejected, proving
    ``PlayerShotDistribution`` is a structurally-immutable value object."""
    distribution = PlayerShotDistribution(**_valid_kwargs())

    with pytest.raises((ValidationError, TypeError)):
        distribution.carry_location_metres = 200.0


def test_assigning_to_lateral_bias_metres_raises() -> None:
    """Frozen enforcement is not field-specific: a second, unrelated field is equally
    protected from mutation after construction."""
    distribution = PlayerShotDistribution(**_valid_kwargs())

    with pytest.raises((ValidationError, TypeError)):
        distribution.lateral_bias_metres = -5.0


# --- carry_location_metres ---------------------------------------------------


@pytest.mark.parametrize("carry_location_metres", [0.0, -1.0, -140.0])
def test_rejects_non_positive_carry_location(carry_location_metres: float) -> None:
    """A zero or negative carry location is not a physically meaningful shot production mean."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(carry_location_metres=carry_location_metres))


@pytest.mark.parametrize("carry_location_metres", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_carry_location(carry_location_metres: float) -> None:
    """NaN/+inf/-inf are rejected even though +inf satisfies a ``gt=0`` bound check."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(carry_location_metres=carry_location_metres))


# --- lateral_bias_metres -----------------------------------------------------


@pytest.mark.parametrize("lateral_bias_metres", [-3.0, 0.0, 3.0])
def test_accepts_any_lateral_bias_sign(lateral_bias_metres: float) -> None:
    """Lateral bias is signed (negative left, positive right) and unconstrained in sign."""
    distribution = PlayerShotDistribution(**_valid_kwargs(lateral_bias_metres=lateral_bias_metres))

    assert distribution.lateral_bias_metres == pytest.approx(lateral_bias_metres)


@pytest.mark.parametrize("lateral_bias_metres", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_lateral_bias(lateral_bias_metres: float) -> None:
    """Lateral bias is unconstrained in sign but must still be finite."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(lateral_bias_metres=lateral_bias_metres))


# --- carry_scale_metres -------------------------------------------------------


@pytest.mark.parametrize("carry_scale_metres", [0.0, -0.0001, -8.0])
def test_rejects_non_positive_carry_scale(carry_scale_metres: float) -> None:
    """Zero (unlike M3's ``CarryDistribution.stddev_metres``) or negative scale is invalid."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(carry_scale_metres=carry_scale_metres))


@pytest.mark.parametrize("carry_scale_metres", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_carry_scale(carry_scale_metres: float) -> None:
    """NaN/+inf/-inf are rejected even though +inf satisfies a ``gt=0`` bound check."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(carry_scale_metres=carry_scale_metres))


# --- lateral_scale_metres ------------------------------------------------------


@pytest.mark.parametrize("lateral_scale_metres", [0.0, -0.0001, -4.0])
def test_rejects_non_positive_lateral_scale(lateral_scale_metres: float) -> None:
    """Zero (unlike M3's ``DirectionalDispersion``) or negative lateral scale is invalid."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(lateral_scale_metres=lateral_scale_metres))


@pytest.mark.parametrize("lateral_scale_metres", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_lateral_scale(lateral_scale_metres: float) -> None:
    """NaN/+inf/-inf are rejected even though +inf satisfies a ``gt=0`` bound check."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(lateral_scale_metres=lateral_scale_metres))


# --- correlation ---------------------------------------------------------------


@pytest.mark.parametrize("correlation", [-0.999999, -0.5, 0.0, 0.5, 0.999999])
def test_accepts_correlation_strictly_inside_open_interval(correlation: float) -> None:
    """Correlation values strictly inside (-1, 1), including near the boundary, are valid."""
    distribution = PlayerShotDistribution(**_valid_kwargs(correlation=correlation))

    assert distribution.correlation == pytest.approx(correlation)


@pytest.mark.parametrize("correlation", [-1.0, 1.0])
def test_rejects_correlation_at_open_interval_boundary(correlation: float) -> None:
    """Exactly +/-1 makes the 2x2 scale matrix singular, unlike a closed [-1, 1] range."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(correlation=correlation))


@pytest.mark.parametrize("correlation", [-1.5, -1.0001, 1.0001, 1.5])
def test_rejects_correlation_outside_open_interval(correlation: float) -> None:
    """Correlation magnitudes greater than 1 are not valid Pearson correlation coefficients."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(correlation=correlation))


@pytest.mark.parametrize("correlation", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_correlation(correlation: float) -> None:
    """NaN/+inf/-inf are rejected even though they may incidentally fail open-interval bounds."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(correlation=correlation))


# --- degrees_of_freedom ----------------------------------------------------------


def test_rejects_degrees_of_freedom_at_lower_boundary() -> None:
    """Exactly nu=2 makes the implied covariance infinite and is rejected."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(degrees_of_freedom=2.0))


@pytest.mark.parametrize("degrees_of_freedom", [2.0001, 3.0, 6.0, 1000.0])
def test_accepts_degrees_of_freedom_above_lower_boundary(degrees_of_freedom: float) -> None:
    """Values immediately above 2, and arbitrarily large values, are valid."""
    distribution = PlayerShotDistribution(**_valid_kwargs(degrees_of_freedom=degrees_of_freedom))

    assert distribution.degrees_of_freedom == pytest.approx(degrees_of_freedom)


@pytest.mark.parametrize("degrees_of_freedom", [0.0, -1.0, 1.0, 1.9999])
def test_rejects_degrees_of_freedom_at_or_below_two(degrees_of_freedom: float) -> None:
    """Non-positive or between-0-and-2 degrees of freedom is rejected, not just exactly 2."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(degrees_of_freedom=degrees_of_freedom))


@pytest.mark.parametrize("degrees_of_freedom", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_degrees_of_freedom(degrees_of_freedom: float) -> None:
    """NaN/+inf/-inf are rejected even though +inf satisfies a ``gt=2`` bound check."""
    with pytest.raises(ValidationError):
        PlayerShotDistribution(**_valid_kwargs(degrees_of_freedom=degrees_of_freedom))


# --- implied_covariance_metres_sq / implied stddev computed properties -------------


def test_implied_covariance_matches_hand_computed_values() -> None:
    """The implied covariance matrix applies the nu/(nu-2) factor to scale and correlation."""
    distribution = PlayerShotDistribution(
        **_valid_kwargs(
            carry_scale_metres=8.0,
            lateral_scale_metres=4.0,
            correlation=0.5,
            degrees_of_freedom=5.0,
        )
    )
    factor = 5.0 / (5.0 - 2.0)
    expected_var_c = factor * 8.0**2
    expected_var_l = factor * 4.0**2
    expected_cov_cl = factor * 0.5 * 8.0 * 4.0

    (var_c, cov_cl), (cov_cl_2, var_l) = distribution.implied_covariance_metres_sq

    assert var_c == pytest.approx(expected_var_c)
    assert var_l == pytest.approx(expected_var_l)
    assert cov_cl == pytest.approx(expected_cov_cl)
    assert cov_cl_2 == pytest.approx(expected_cov_cl)


def test_implied_covariance_matrix_is_symmetric() -> None:
    """The two off-diagonal covariance entries are identical, as required of a covariance matrix."""
    distribution = PlayerShotDistribution(**_valid_kwargs(correlation=-0.3))

    (_, cov_cl_top), (cov_cl_bottom, _) = distribution.implied_covariance_metres_sq

    assert cov_cl_top == pytest.approx(cov_cl_bottom)


def test_implied_carry_stddev_applies_nu_factor_for_nu_five() -> None:
    """For nu=5, factor sqrt(5/3) ~= 1.29, so implied stddev must exceed the raw scale."""
    distribution = PlayerShotDistribution(
        **_valid_kwargs(carry_scale_metres=8.0, degrees_of_freedom=5.0)
    )

    assert distribution.implied_carry_stddev_metres == pytest.approx(8.0 * math.sqrt(5.0 / 3.0))


def test_implied_lateral_stddev_applies_nu_factor_for_nu_five() -> None:
    """For nu=5, factor sqrt(5/3) ~= 1.29, so implied stddev must exceed the raw scale."""
    distribution = PlayerShotDistribution(
        **_valid_kwargs(lateral_scale_metres=4.0, degrees_of_freedom=5.0)
    )

    assert distribution.implied_lateral_stddev_metres == pytest.approx(4.0 * math.sqrt(5.0 / 3.0))


def test_implied_stddev_is_never_equal_to_raw_scale_for_finite_nu() -> None:
    """The scale parameter is not the standard deviation — they differ for any finite nu > 2."""
    distribution = PlayerShotDistribution(
        **_valid_kwargs(carry_scale_metres=8.0, lateral_scale_metres=4.0, degrees_of_freedom=6.0)
    )

    assert distribution.implied_carry_stddev_metres != pytest.approx(
        distribution.carry_scale_metres
    )
    assert distribution.implied_lateral_stddev_metres != pytest.approx(
        distribution.lateral_scale_metres
    )


def test_correlation_is_recoverable_from_implied_covariance() -> None:
    """The nu/(nu-2) factor scales the covariance matrix uniformly, so correlation is unchanged."""
    distribution = PlayerShotDistribution(**_valid_kwargs(correlation=0.35, degrees_of_freedom=4.0))

    (var_c, cov_cl), (_, var_l) = distribution.implied_covariance_metres_sq
    recovered_correlation = cov_cl / math.sqrt(var_c * var_l)

    assert recovered_correlation == pytest.approx(distribution.correlation)


# --- serialisation -----------------------------------------------------------------


def test_model_dump_round_trips_all_fields() -> None:
    """``model_dump()`` reproduces every field with its original value."""
    distribution = PlayerShotDistribution(**_valid_kwargs())

    dumped = distribution.model_dump()

    assert dumped["carry_location_metres"] == pytest.approx(140.0)
    assert dumped["lateral_bias_metres"] == pytest.approx(1.5)
    assert dumped["carry_scale_metres"] == pytest.approx(8.0)
    assert dumped["lateral_scale_metres"] == pytest.approx(4.0)
    assert dumped["correlation"] == pytest.approx(0.2)
    assert dumped["degrees_of_freedom"] == pytest.approx(6.0)
    assert dumped["family"] == ShotDistributionFamily.BIVARIATE_STUDENT_T


def test_model_dump_json_mode_serialises_family_as_plain_string() -> None:
    """JSON-mode serialisation must produce the plain string, not the enum member, for interop."""
    distribution = PlayerShotDistribution(**_valid_kwargs())

    dumped = distribution.model_dump(mode="json")

    assert dumped["family"] == "bivariate_student_t"


# =====================================================================================
# M4.6 — Compose PlayerShotDistribution into Club/Player (issue #54)
# =====================================================================================
#
# The two properties under test that matter most:
#
# 1. **Baseline immutability**: ``resolve_current_shot_distribution`` never
#    mutates ``Club.shot_distribution`` — it derives a *current* distribution
#    on demand from the fixed baseline plus history, never persisting or
#    feeding a posterior back in as a new baseline.
# 2. **``support_status`` is always derived from ``club.category``**,
#    independent of whether ``shot_distribution`` happens to be populated —
#    ``PUTTER``/``OTHER`` always resolve to ``(None, DEFERRED)``/
#    ``(None, NOT_MODELABLE)`` even before/without any onboarding attempt.

_M46_CLUB_NAME = "7 Iron"


def _compose(**overrides: object) -> ClubShotDistributionComposition:
    """Baseline valid call kwargs for ``compose_club_shot_distribution``."""
    kwargs: dict[str, object] = {
        "handicap_index": 12.3,
        "club_category": ClubCategory.IRON,
        "reported_carry_metres": 150.0,
        "carry_provenance": CarryProvenance.MEASURED,
        "common_miss": CommonMiss.NONE,
        "club_name": _M46_CLUB_NAME,
        "shot_history": [],
    }
    kwargs.update(overrides)
    return compose_club_shot_distribution(**kwargs)  # type: ignore[arg-type]


def _m46_shot_record(
    *,
    club_name: str = _M46_CLUB_NAME,
    final_downrange_metres: float = 150.0,
    lateral_offset_metres: float = 0.0,
    endpoint_quality: ShotMeasurementQuality = ShotMeasurementQuality.HIGH,
    observed_carry_metres: float | None = None,
    carry_quality: ShotMeasurementQuality = ShotMeasurementQuality.HIGH,
) -> ShotRecord:
    """Build a ShotRecord with HIGH-quality metadata by default, so it counts as evidence
    (see ``caddai.player.personalisation.MEASUREMENT_QUALITY_WEIGHTS``)."""
    observed_carry_measurement = None
    if observed_carry_metres is not None:
        observed_carry_measurement = ShotMeasurementMetadata(
            source=ShotMeasurementSource.LAUNCH_MONITOR, quality=carry_quality
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


def _club_with_shot_distribution(shot_distribution: PlayerShotDistribution | None) -> Club:
    """A supported-category (``IRON``) ``Club`` named ``_M46_CLUB_NAME`` with the given baseline."""
    return Club(
        name=_M46_CLUB_NAME,
        carry_distribution=CarryDistribution(mean_metres=150.0, stddev_metres=8.0),
        dispersion=DirectionalDispersion(lateral_stddev_metres=4.0, lateral_bias_metres=0.0),
        category=ClubCategory.IRON,
        shot_distribution=shot_distribution,
    )


# --- Empty history: current == baseline == onboarding -------------------------


def test_compose_with_empty_history_current_equals_baseline_equals_onboarding() -> None:
    """Zero history means no shrinkage evidence: current, baseline, and the onboarding
    cold-start result are all the same distribution."""
    composition = _compose(shot_history=[])

    assert isinstance(composition, ClubShotDistributionComposition)
    assert isinstance(composition.onboarding, OnboardingPersonalisationResult)
    assert composition.current_shot_distribution == composition.baseline_shot_distribution
    assert composition.baseline_shot_distribution == composition.onboarding.shot_distribution
    assert composition.update.shot_distribution == composition.current_shot_distribution


# --- Relevant history moves current away from baseline ------------------------


def test_compose_with_matching_history_current_differs_from_baseline_as_expected() -> None:
    """Historical evidence shrinks the current distribution toward the sample evidence,
    away from the (unmoved) baseline — M4.5 shrinkage semantics."""
    reported_carry_metres = 150.0
    history = [
        _m46_shot_record(observed_carry_metres=170.0, lateral_offset_metres=8.0) for _ in range(10)
    ]

    composition = _compose(
        reported_carry_metres=reported_carry_metres,
        common_miss=CommonMiss.NONE,
        shot_history=history,
    )

    assert composition.baseline_shot_distribution.carry_location_metres == pytest.approx(
        reported_carry_metres
    )
    assert composition.baseline_shot_distribution.lateral_bias_metres == pytest.approx(0.0)
    assert composition.current_shot_distribution != composition.baseline_shot_distribution
    assert (
        composition.current_shot_distribution.carry_location_metres
        > composition.baseline_shot_distribution.carry_location_metres
    )
    assert (
        composition.current_shot_distribution.lateral_bias_metres
        > composition.baseline_shot_distribution.lateral_bias_metres
    )


# --- Unrelated club_name history is filtered out -------------------------------


def test_resolve_current_shot_distribution_ignores_unrelated_club_name_history() -> None:
    """History entries for a different club must not influence the resolved distribution
    for the club under test."""
    baseline = _compose(shot_history=[]).baseline_shot_distribution
    club = _club_with_shot_distribution(baseline)
    unrelated_history = [
        _m46_shot_record(
            club_name="Driver", observed_carry_metres=250.0, lateral_offset_metres=30.0
        )
        for _ in range(5)
    ]

    empty_history_resolution = resolve_current_shot_distribution(club, [])
    unrelated_history_resolution = resolve_current_shot_distribution(club, unrelated_history)

    assert unrelated_history_resolution == empty_history_resolution


# --- Determinism ----------------------------------------------------------------


def test_compose_club_shot_distribution_is_deterministic() -> None:
    """No RNG/hidden randomness: two calls with identical arguments produce equal output."""
    history = [_m46_shot_record(observed_carry_metres=160.0, lateral_offset_metres=3.0)]

    first = _compose(shot_history=history)
    second = _compose(shot_history=history)

    assert first == second


def test_resolve_current_shot_distribution_is_deterministic() -> None:
    """Two calls with identical club/history inputs produce equal output."""
    baseline = _compose(shot_history=[]).baseline_shot_distribution
    club = _club_with_shot_distribution(baseline)
    history = [_m46_shot_record(observed_carry_metres=160.0, lateral_offset_metres=3.0)]

    first = resolve_current_shot_distribution(club, history)
    second = resolve_current_shot_distribution(club, history)

    assert first == second


def test_resolve_current_shot_distribution_does_not_mutate_club_shot_distribution() -> None:
    """Baseline immutability: repeatedly deriving a current distribution must never write
    back onto ``Club.shot_distribution``."""
    baseline = _compose(shot_history=[]).baseline_shot_distribution
    club = _club_with_shot_distribution(baseline)
    history = [
        _m46_shot_record(observed_carry_metres=200.0, lateral_offset_metres=15.0) for _ in range(5)
    ]

    resolve_current_shot_distribution(club, history)
    assert club.shot_distribution == baseline

    resolve_current_shot_distribution(club, history)
    assert club.shot_distribution == baseline


def test_resolve_current_shot_distribution_preserves_baseline_object_identity() -> None:
    """Object identity, not just value-equality: resolving a current distribution must never
    rebind ``Club.shot_distribution`` to a new (even equal-valued) object."""
    baseline = _compose(shot_history=[]).baseline_shot_distribution
    club = _club_with_shot_distribution(baseline)
    original = club.shot_distribution
    history = [
        _m46_shot_record(observed_carry_metres=200.0, lateral_offset_metres=15.0) for _ in range(5)
    ]

    resolve_current_shot_distribution(club, history)

    assert club.shot_distribution is original


def test_resolve_current_shot_distribution_does_not_mutate_baseline_field_values() -> None:
    """Behavioural regression test independent of the frozen mechanism: resolving with
    strong evidence must leave the supplied baseline object's own field values exactly as
    constructed."""
    baseline = PlayerShotDistribution(
        carry_location_metres=150.0,
        lateral_bias_metres=0.0,
        carry_scale_metres=8.0,
        lateral_scale_metres=4.0,
        correlation=0.1,
        degrees_of_freedom=6.0,
    )
    original_values = baseline.model_dump()
    club = _club_with_shot_distribution(baseline)
    history = [
        _m46_shot_record(observed_carry_metres=200.0, lateral_offset_metres=15.0) for _ in range(10)
    ]

    resolve_current_shot_distribution(club, history)

    assert baseline.model_dump() == original_values


def test_resolve_current_shot_distribution_repeated_calls_preserve_baseline_identity() -> None:
    """Idempotency includes non-mutation: repeated resolution with unchanged inputs must
    never rebind ``Club.shot_distribution``, not just produce equal results."""
    baseline = _compose(shot_history=[]).baseline_shot_distribution
    club = _club_with_shot_distribution(baseline)
    original = club.shot_distribution
    history = [_m46_shot_record(observed_carry_metres=160.0, lateral_offset_metres=3.0)]

    first = resolve_current_shot_distribution(club, history)
    assert club.shot_distribution is original

    second = resolve_current_shot_distribution(club, history)
    assert club.shot_distribution is original

    assert first == second


def test_resolve_current_shot_distribution_result_is_not_alias_of_baseline_when_it_differs() -> (
    None
):
    """The resolved 'current' distribution must be a distinct object from the stored
    baseline whenever evidence actually moves it — never a silent alias."""
    baseline = _compose(shot_history=[]).baseline_shot_distribution
    club = _club_with_shot_distribution(baseline)
    history = [
        _m46_shot_record(observed_carry_metres=200.0, lateral_offset_metres=15.0) for _ in range(10)
    ]

    resolution = resolve_current_shot_distribution(club, history)

    assert resolution.shot_distribution != club.shot_distribution
    assert resolution.shot_distribution is not club.shot_distribution


# --- PUTTER: DEFERRED ------------------------------------------------------------


def test_compose_putter_raises_deferred_error() -> None:
    """PUTTER is deferred, not invalid — the existing population-prior error propagates
    unmodified, with no new composition-specific error type."""
    with pytest.raises(PopulationPriorUnsupportedCategoryError) as excinfo:
        _compose(club_category=ClubCategory.PUTTER)

    assert excinfo.value.club_category == ClubCategory.PUTTER
    assert excinfo.value.status == ClubCategorySupportStatus.DEFERRED


def test_resolve_current_shot_distribution_putter_returns_none_deferred() -> None:
    """A never-onboarded PUTTER club resolves to ``(None, DEFERRED)``."""
    club = Club.with_expected_carry(
        name="Putter", expected_carry_metres=8.0, category=ClubCategory.PUTTER
    )

    resolution = resolve_current_shot_distribution(club, [])

    assert resolution == ClubShotDistributionResolution(
        shot_distribution=None, support_status=ClubCategorySupportStatus.DEFERRED
    )


# --- OTHER: NOT_MODELABLE ---------------------------------------------------------


def test_compose_other_raises_not_modelable_error() -> None:
    """OTHER has no modelable mechanics; the same error type propagates with a different
    status."""
    with pytest.raises(PopulationPriorUnsupportedCategoryError) as excinfo:
        _compose(club_category=ClubCategory.OTHER)

    assert excinfo.value.club_category == ClubCategory.OTHER
    assert excinfo.value.status == ClubCategorySupportStatus.NOT_MODELABLE


def test_resolve_current_shot_distribution_other_returns_none_not_modelable() -> None:
    """A never-onboarded OTHER club resolves to ``(None, NOT_MODELABLE)``."""
    club = Club.with_expected_carry(
        name="Chipper", expected_carry_metres=20.0, category=ClubCategory.OTHER
    )

    resolution = resolve_current_shot_distribution(club, [])

    assert resolution == ClubShotDistributionResolution(
        shot_distribution=None, support_status=ClubCategorySupportStatus.NOT_MODELABLE
    )


# --- Supported category, never onboarded: (None, SUPPORTED) ----------------------


def test_resolve_current_shot_distribution_supported_not_onboarded_returns_none_supported() -> None:
    """A supported category with no baseline composed yet resolves to ``(None, SUPPORTED)`` —
    distinct from ``DEFERRED``/``NOT_MODELABLE``, which never depend on onboarding state."""
    club = Club.with_expected_carry(
        name=_M46_CLUB_NAME, expected_carry_metres=150.0, category=ClubCategory.IRON
    )
    assert club.shot_distribution is None

    resolution = resolve_current_shot_distribution(club, [])

    assert resolution == ClubShotDistributionResolution(
        shot_distribution=None, support_status=ClubCategorySupportStatus.SUPPORTED
    )


# --- Invalid onboarding inputs propagate ValueError -------------------------------


@pytest.mark.parametrize(
    "reported_carry_metres",
    [0.0, -0.0001, -150.0, float("nan"), float("inf"), float("-inf")],
)
def test_compose_rejects_invalid_reported_carry_metres(reported_carry_metres: float) -> None:
    """Non-positive or non-finite reported carry is rejected, mirroring
    ``personalise_shot_distribution``'s own validation."""
    with pytest.raises(ValueError):
        _compose(reported_carry_metres=reported_carry_metres)


@pytest.mark.parametrize(
    "handicap_index", [float("nan"), float("inf"), float("-inf"), -10.01, 54.01, 100.0]
)
def test_compose_rejects_invalid_handicap_index(handicap_index: float) -> None:
    """Out-of-range or non-finite handicap propagates ``resolve_population_prior``'s
    existing ``ValueError`` unmodified."""
    with pytest.raises(ValueError):
        _compose(handicap_index=handicap_index)


# --- Serialization round-trip ------------------------------------------------------


def test_club_with_populated_shot_distribution_round_trips_through_model_dump() -> None:
    """``Club.model_dump()`` -> ``Club.model_validate(...)`` preserves a populated
    ``shot_distribution`` exactly."""
    baseline = _compose(shot_history=[]).baseline_shot_distribution
    club = _club_with_shot_distribution(baseline)

    reconstructed = Club.model_validate(club.model_dump())

    assert reconstructed.shot_distribution == baseline
    assert reconstructed == club


def test_club_with_populated_shot_distribution_round_trips_through_model_dump_json() -> None:
    """``Club.model_dump_json()`` -> ``Club.model_validate_json(...)`` preserves a populated
    ``shot_distribution`` exactly."""
    baseline = _compose(shot_history=[]).baseline_shot_distribution
    club = _club_with_shot_distribution(baseline)

    reconstructed = Club.model_validate_json(club.model_dump_json())

    assert reconstructed.shot_distribution == baseline
    assert reconstructed == club
