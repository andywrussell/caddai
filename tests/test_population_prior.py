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
    ClubCategory,
    HandicapBand,
    PlayerShotDistribution,
    PopulationPriorConfidence,
    PopulationPriorParameters,
    PopulationPriorProvenance,
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

# One representative handicap_index per band, strictly inside that band's
# half-open range.
_REPRESENTATIVE_HANDICAP_BY_BAND = {
    HandicapBand.PLUS: -5.0,
    HandicapBand.LOW: 4.5,
    HandicapBand.MID: 12.0,
    HandicapBand.HIGH: 30.0,
}

# (handicap_index, expected HandicapBand) at and around every band edge —
# see population_prior.py's `_resolve_handicap_band`: PLUS for < 0.0, LOW
# for [0.0, 9.0), MID for [9.0, 18.0), HIGH for [18.0, 54.0].
_BOUNDARY_HANDICAP_CASES = [
    (-10.0, HandicapBand.PLUS),
    (-0.01, HandicapBand.PLUS),
    (0.0, HandicapBand.LOW),
    (8.99, HandicapBand.LOW),
    (9.0, HandicapBand.MID),
    (17.99, HandicapBand.MID),
    (18.0, HandicapBand.HIGH),
    (54.0, HandicapBand.HIGH),
]


# --- Valid lookups across every band x supported category -------------------


@pytest.mark.parametrize("handicap_band", list(HandicapBand))
@pytest.mark.parametrize("club_category", _SUPPORTED_CLUB_CATEGORIES)
def test_resolves_every_band_and_supported_category(
    handicap_band: HandicapBand, club_category: ClubCategory
) -> None:
    """Every (band, supported category) combination resolves without error."""
    handicap_index = _REPRESENTATIVE_HANDICAP_BY_BAND[handicap_band]

    result = resolve_population_prior(handicap_index, club_category)

    assert result.handicap_band == handicap_band
    assert result.club_category == club_category
    assert result.handicap_index == pytest.approx(handicap_index)


# --- Boundary handicap values -------------------------------------------------


@pytest.mark.parametrize(("handicap_index", "expected_band"), _BOUNDARY_HANDICAP_CASES)
def test_resolves_correct_band_at_boundary_handicap_values(
    handicap_index: float, expected_band: HandicapBand
) -> None:
    """Band edges use half-open containment: the lower edge belongs to the higher band."""
    result = resolve_population_prior(handicap_index, ClubCategory.IRON)

    assert result.handicap_band == expected_band


@pytest.mark.parametrize("handicap_index", [-10.0, -5.0, -0.01])
def test_negative_handicap_resolves_to_plus_band(handicap_index: float) -> None:
    """Plus-handicap (negative) values resolve to ``HandicapBand.PLUS``, never assumed >= 0."""
    result = resolve_population_prior(handicap_index, ClubCategory.IRON)

    assert result.handicap_band == HandicapBand.PLUS


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


# --- Compatibility with PlayerShotDistribution ---------------------------------


@pytest.mark.parametrize("handicap_band", list(HandicapBand))
@pytest.mark.parametrize("club_category", _SUPPORTED_CLUB_CATEGORIES)
def test_resolved_parameters_construct_a_valid_player_shot_distribution(
    handicap_band: HandicapBand, club_category: ClubCategory
) -> None:
    """Every resolved ``PopulationPriorParameters`` satisfies ``PlayerShotDistribution``'s
    own field constraints (positive scales, correlation in (-1, 1), dof > 2)."""
    handicap_index = _REPRESENTATIVE_HANDICAP_BY_BAND[handicap_band]
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


@pytest.mark.parametrize("handicap_band", list(HandicapBand))
@pytest.mark.parametrize("club_category", _SUPPORTED_CLUB_CATEGORIES)
def test_provenance_and_confidence_are_uniform(
    handicap_band: HandicapBand, club_category: ClubCategory
) -> None:
    """Every M4.2 cell is uniformly LOW confidence / evidence-informed-provisional-config."""
    handicap_index = _REPRESENTATIVE_HANDICAP_BY_BAND[handicap_band]

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
    """``handicap_band``/``club_category``/``handicap_index`` echo the resolved inputs."""
    result = resolve_population_prior(12.0, ClubCategory.IRON)

    assert result.handicap_band == HandicapBand.MID
    assert result.club_category == ClubCategory.IRON
    assert result.handicap_index == pytest.approx(12.0)


# --- FAIRWAY_WOOD / HYBRID alias ------------------------------------------------


@pytest.mark.parametrize("handicap_band", list(HandicapBand))
def test_fairway_wood_and_hybrid_share_identical_parameters(handicap_band: HandicapBand) -> None:
    """FAIRWAY_WOOD and HYBRID are identical in every band: the research doc groups them
    together rather than treating them as separate club-mechanics regimes, so the
    config table intentionally aliases the two rather than inventing a distinction."""
    handicap_index = _REPRESENTATIVE_HANDICAP_BY_BAND[handicap_band]

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
