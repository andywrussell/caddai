"""Tests for the ``PopulationPrior`` contract.

See GitHub issue #50 ("M4.2 — `PopulationPrior` population parameter
model") and docs/plans/m4.2-population-prior.plan.md for the acceptance
criteria these tests are derived from, ADR 0006
(docs/adr/0006-player-shot-distribution-bivariate-student-t.md) for the
underlying bivariate Student-t construction, and ADR 0007
(docs/adr/0007-population-prior-replaceability.md) for the
stable-interface/replaceable-implementation and provisional-provenance
contract that ``resolve_population_prior`` must satisfy.

This module does not test ``PlayerShotDistribution``'s own field
constraints (see tests/test_player_shot_distribution.py) beyond proving a
resolved ``PopulationPriorParameters`` is compatible with them, and does
not test onboarding personalisation, sampling/RNG, or simulation — those
are out of scope for M4.2.
"""

import pytest
from pydantic import ValidationError

from caddai.statistics import (
    CLUB_CATEGORY_SUPPORT_STATUS,
    ClubCategory,
    ClubCategorySupportStatus,
    PlayerShotDistribution,
    PopulationPriorConfidence,
    PopulationPriorParameters,
    PopulationPriorProvenance,
    PopulationPriorUnsupportedCategoryError,
    club_category_support_status,
    resolve_population_prior,
)
from caddai.statistics.population_prior_config import POPULATION_PRIOR_CONFIG, lookup

_SUPPORTED_CLUB_CATEGORIES = (
    ClubCategory.DRIVER,
    ClubCategory.FAIRWAY_WOOD,
    ClubCategory.HYBRID,
    ClubCategory.IRON,
    ClubCategory.WEDGE,
)

_UNSUPPORTED_CLUB_CATEGORIES = (ClubCategory.PUTTER, ClubCategory.OTHER)

# One representative handicap_index per internal band bucket, strictly
# inside that bucket's half-open range (PLUS/LOW/MID/HIGH).
_REPRESENTATIVE_HANDICAP_BY_BAND = [-5.0, 4.5, 12.0, 30.0]

# (handicap_index, another handicap_index in the same internal bucket) at
# and around every band edge — see population_prior_config.py's
# `_band_for_handicap_index`: PLUS for < 0.0, LOW for [0.0, 9.0), MID for
# [9.0, 18.0), HIGH for [18.0, 54.0]. Same-bucket pairs must resolve to
# identical parameters; a boundary-straddling pair must not.
_BOUNDARY_HANDICAP_CASES = [
    (-10.0, -0.01),
    (0.0, 8.99),
    (9.0, 17.99),
    (18.0, 54.0),
]


# --- Valid lookups across every band x supported category -------------------


@pytest.mark.parametrize("handicap_index", _REPRESENTATIVE_HANDICAP_BY_BAND)
@pytest.mark.parametrize("club_category", _SUPPORTED_CLUB_CATEGORIES)
def test_resolves_every_band_and_supported_category(
    handicap_index: float, club_category: ClubCategory
) -> None:
    """Every (band, supported category) combination resolves without error."""
    result = resolve_population_prior(handicap_index, club_category)

    assert result.parameters == lookup(handicap_index, club_category)
    assert result.club_category == club_category
    assert result.handicap_index == pytest.approx(handicap_index)


# --- Boundary handicap values -------------------------------------------------


@pytest.mark.parametrize(("same_bucket_a", "same_bucket_b"), _BOUNDARY_HANDICAP_CASES)
def test_same_bucket_boundary_handicaps_resolve_to_same_parameters(
    same_bucket_a: float, same_bucket_b: float
) -> None:
    """Band edges use half-open containment: both ends of a bucket's range resolve to
    identical parameters, proving the same lookup bucket without a public handicap_band."""
    result_a = resolve_population_prior(same_bucket_a, ClubCategory.DRIVER)
    result_b = resolve_population_prior(same_bucket_b, ClubCategory.DRIVER)

    assert result_a.parameters == result_b.parameters


@pytest.mark.parametrize(
    ("lower_handicap", "higher_handicap"),
    [(-0.01, 0.0), (8.99, 9.0), (17.99, 18.0)],
)
def test_boundary_straddling_handicaps_resolve_to_different_parameters(
    lower_handicap: float, higher_handicap: float
) -> None:
    """A handicap just below a band edge and one at the edge fall in different internal
    buckets and must resolve to different parameters (DRIVER is band-differentiated)."""
    lower_result = resolve_population_prior(lower_handicap, ClubCategory.DRIVER)
    higher_result = resolve_population_prior(higher_handicap, ClubCategory.DRIVER)

    assert lower_result.parameters != higher_result.parameters


@pytest.mark.parametrize("handicap_index", [-10.0, -5.0, -0.01])
def test_negative_handicap_resolves_same_as_other_plus_handicaps(handicap_index: float) -> None:
    """Plus-handicap (negative) values all resolve to the same internal bucket, never
    assumed >= 0."""
    result = resolve_population_prior(handicap_index, ClubCategory.IRON)
    reference = resolve_population_prior(-5.0, ClubCategory.IRON)

    assert result.parameters == reference.parameters


# --- Out-of-range / non-finite handicap ---------------------------------------


@pytest.mark.parametrize("handicap_index", [-10.01, -11.0, 54.01, 100.0])
def test_rejects_out_of_range_handicap(handicap_index: float) -> None:
    """Handicap values outside [-10.0, 54.0] are rejected."""
    with pytest.raises(ValueError, match="handicap_index"):
        resolve_population_prior(handicap_index, ClubCategory.IRON)


@pytest.mark.parametrize("handicap_index", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_handicap(handicap_index: float) -> None:
    """NaN/+inf/-inf are rejected even though +inf/-inf may incidentally fail the range check."""
    with pytest.raises(ValueError, match="handicap_index"):
        resolve_population_prior(handicap_index, ClubCategory.IRON)


# --- Unsupported club categories -----------------------------------------------


@pytest.mark.parametrize("club_category", _UNSUPPORTED_CLUB_CATEGORIES)
def test_rejects_unsupported_club_category(club_category: ClubCategory) -> None:
    """PUTTER/OTHER are not supported full-swing categories and are rejected."""
    with pytest.raises(ValueError, match="club_category"):
        resolve_population_prior(0.0, club_category)


def test_putter_raises_deferred_error_not_generic_invalid_message() -> None:
    """PUTTER is a valid category with a deferred model, not an invalid input — the error
    must not claim it's an invalid category (e.g. "must be one of")."""
    with pytest.raises(PopulationPriorUnsupportedCategoryError) as excinfo:
        resolve_population_prior(0.0, ClubCategory.PUTTER)

    error = excinfo.value
    assert isinstance(error, ValueError)  # backward compatible with pytest.raises(ValueError)
    assert error.club_category == ClubCategory.PUTTER
    assert error.status == ClubCategorySupportStatus.DEFERRED
    assert "no population-prior model yet" in str(error)
    assert "must be one of" not in str(error)


def test_other_raises_not_modelable_error() -> None:
    """OTHER is an intentional catch-all with no modelable mechanics."""
    with pytest.raises(PopulationPriorUnsupportedCategoryError) as excinfo:
        resolve_population_prior(0.0, ClubCategory.OTHER)

    error = excinfo.value
    assert isinstance(error, ValueError)
    assert error.club_category == ClubCategory.OTHER
    assert error.status == ClubCategorySupportStatus.NOT_MODELABLE


@pytest.mark.parametrize("club_category", list(ClubCategory))
def test_club_category_support_status_covers_every_category(
    club_category: ClubCategory,
) -> None:
    """``club_category_support_status`` resolves every ``ClubCategory`` member."""
    expected = (
        ClubCategorySupportStatus.SUPPORTED
        if club_category in _SUPPORTED_CLUB_CATEGORIES
        else (
            ClubCategorySupportStatus.DEFERRED
            if club_category is ClubCategory.PUTTER
            else ClubCategorySupportStatus.NOT_MODELABLE
        )
    )

    assert club_category_support_status(club_category) == expected


def test_club_category_support_status_mapping_covers_every_category() -> None:
    """``CLUB_CATEGORY_SUPPORT_STATUS`` has no missing ``ClubCategory`` member."""
    assert set(CLUB_CATEGORY_SUPPORT_STATUS.keys()) == set(ClubCategory)


def test_population_prior_config_has_no_putter_entries() -> None:
    """Putting must not be pooled into the full-swing config table (no PUTTER rows)."""
    putter_keys = [key for key in POPULATION_PRIOR_CONFIG if key[1] is ClubCategory.PUTTER]

    assert putter_keys == []


# --- Compatibility with PlayerShotDistribution ---------------------------------


@pytest.mark.parametrize("handicap_index", _REPRESENTATIVE_HANDICAP_BY_BAND)
@pytest.mark.parametrize("club_category", _SUPPORTED_CLUB_CATEGORIES)
def test_resolved_parameters_construct_a_valid_player_shot_distribution(
    handicap_index: float, club_category: ClubCategory
) -> None:
    """Every resolved ``PopulationPriorParameters`` satisfies ``PlayerShotDistribution``'s
    own field constraints (positive scales, correlation in (-1, 1), dof > 2)."""
    result = resolve_population_prior(handicap_index, club_category)
    parameters = result.parameters

    distribution = PlayerShotDistribution(
        family=parameters.family,
        carry_location_metres=100.0,
        lateral_bias_metres=0.0,
        carry_scale_metres=parameters.carry_scale_metres,
        lateral_scale_metres=parameters.lateral_scale_metres,
        correlation=parameters.correlation,
        degrees_of_freedom=parameters.degrees_of_freedom,
    )

    assert distribution.carry_scale_metres == pytest.approx(parameters.carry_scale_metres)
    assert distribution.lateral_scale_metres == pytest.approx(parameters.lateral_scale_metres)
    assert distribution.correlation == pytest.approx(parameters.correlation)
    assert distribution.degrees_of_freedom == pytest.approx(parameters.degrees_of_freedom)


# --- Provenance / confidence metadata ------------------------------------------


@pytest.mark.parametrize("handicap_index", _REPRESENTATIVE_HANDICAP_BY_BAND)
@pytest.mark.parametrize("club_category", _SUPPORTED_CLUB_CATEGORIES)
def test_provenance_and_confidence_are_uniform(
    handicap_index: float, club_category: ClubCategory
) -> None:
    """Every M4.2 cell is uniformly LOW confidence / evidence-informed-provisional-config."""
    result = resolve_population_prior(handicap_index, club_category)

    assert result.confidence == PopulationPriorConfidence.LOW
    assert result.provenance == PopulationPriorProvenance.EVIDENCE_INFORMED_PROVISIONAL_CONFIG


# --- config_version ------------------------------------------------------------


def test_config_version_is_non_empty_string() -> None:
    """``config_version`` is a non-empty string, per ``PopulationPriorResult``'s ``min_length``."""
    result = resolve_population_prior(10.0, ClubCategory.DRIVER)

    assert isinstance(result.config_version, str)
    assert len(result.config_version) > 0


def test_config_version_is_identical_across_multiple_calls() -> None:
    """The config version is stable across separate calls, regardless of inputs."""
    first = resolve_population_prior(-5.0, ClubCategory.DRIVER)
    second = resolve_population_prior(30.0, ClubCategory.WEDGE)

    assert first.config_version == second.config_version


# --- Echoed inputs on PopulationPriorResult ------------------------------------


def test_result_echoes_resolved_inputs() -> None:
    """``club_category``/``handicap_index`` echo the resolved inputs."""
    result = resolve_population_prior(12.0, ClubCategory.IRON)

    assert result.club_category == ClubCategory.IRON
    assert result.handicap_index == pytest.approx(12.0)


# --- FAIRWAY_WOOD / HYBRID alias ------------------------------------------------


@pytest.mark.parametrize("handicap_index", _REPRESENTATIVE_HANDICAP_BY_BAND)
def test_fairway_wood_and_hybrid_share_identical_parameters(handicap_index: float) -> None:
    """FAIRWAY_WOOD and HYBRID are identical in every band: the research doc groups them
    together rather than treating them as separate club-mechanics regimes, so the
    config table intentionally aliases the two rather than inventing a distinction."""
    fairway_wood_result = resolve_population_prior(handicap_index, ClubCategory.FAIRWAY_WOOD)
    hybrid_result = resolve_population_prior(handicap_index, ClubCategory.HYBRID)

    assert fairway_wood_result.parameters == hybrid_result.parameters


def test_population_prior_parameters_supports_equality() -> None:
    """Sanity check: ``PopulationPriorParameters`` (a Pydantic model) supports ``==``."""
    same_params = PopulationPriorParameters(
        carry_scale_metres=8.0,
        lateral_scale_metres=6.0,
        correlation=0.1,
        degrees_of_freedom=8.0,
    )
    other_params = PopulationPriorParameters(
        carry_scale_metres=8.0,
        lateral_scale_metres=6.0,
        correlation=0.1,
        degrees_of_freedom=8.0,
    )
    different_params = PopulationPriorParameters(
        carry_scale_metres=9.0,
        lateral_scale_metres=6.0,
        correlation=0.1,
        degrees_of_freedom=8.0,
    )

    assert same_params == other_params
    assert same_params != different_params


# --- PopulationPriorParameters own field constraints ---------------------------


@pytest.mark.parametrize(
    ("carry_scale_metres", "lateral_scale_metres", "correlation", "degrees_of_freedom"),
    [
        (0.0, 6.0, 0.1, 8.0),
        (8.0, 0.0, 0.1, 8.0),
        (8.0, 6.0, 1.0, 8.0),
        (8.0, 6.0, -1.0, 8.0),
        (8.0, 6.0, 0.1, 2.0),
    ],
)
def test_population_prior_parameters_rejects_invalid_values(
    carry_scale_metres: float,
    lateral_scale_metres: float,
    correlation: float,
    degrees_of_freedom: float,
) -> None:
    """``PopulationPriorParameters`` mirrors ``PlayerShotDistribution``'s field bounds."""
    with pytest.raises(ValidationError):
        PopulationPriorParameters(
            carry_scale_metres=carry_scale_metres,
            lateral_scale_metres=lateral_scale_metres,
            correlation=correlation,
            degrees_of_freedom=degrees_of_freedom,
        )
