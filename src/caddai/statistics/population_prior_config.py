"""Provisional handicap-band x club-category population prior config table.

See docs/research/m4-probabilistic-golfer-model.md ("Unresolved evidence/
calibration gaps", items 1-3) for the evidence classification behind these
numbers: handicap x club-category carry/lateral dispersion scale,
carry-lateral correlation, and degrees-of-freedom (tail heaviness) are all
classified as **unresolved evidence gaps** — the *direction* of the
handicap effect is evidence-backed (see Betzler et al., cited in that
report), but no public source establishes a complete numeric surface across
handicap x club x carry/lateral dispersion x correlation x tail behaviour.

The values below are therefore illustrative/provisional CaddAI
configuration, not validated population fact. They exist so
``resolve_population_prior`` (population_prior.py) has a real, testable
lookup table rather than an empty contract, per the M4.2 plan
(docs/plans/m4.2-population-prior.plan.md). Every cell is marked
``confidence=PopulationPriorConfidence.LOW`` and
``provenance=PopulationPriorProvenance.EVIDENCE_INFORMED_PROVISIONAL_CONFIG``
accordingly, and must be replaced by CaddAI's own calibration data (or a
fitted/learned model, per ADR 0007) before being treated as authoritative.

``_HandicapBand`` is a private implementation detail of this lookup table
only — it is not part of the public ``caddai.statistics`` contract.
``PopulationPriorResult`` (population_prior.py) only ever exposes the
continuous ``handicap_index`` (float), so a future fitted/learned
population-prior model (ADR 0007) can consume it directly without
depending on today's bucket scheme.
"""

from enum import StrEnum

from caddai.statistics.models import ClubCategory, PopulationPriorParameters

POPULATION_PRIOR_CONFIG_VERSION = "m4.2-provisional-v1"


class _HandicapBand(StrEnum):
    """A coarse WHS Handicap Index band used internally by this lookup table.

    Half-open range containment, no interpolation between bands — see
    ``_band_for_handicap_index``. Purely an implementation detail: never
    exposed on the public ``PopulationPriorResult`` contract.
    """

    PLUS = "plus"
    LOW = "low"
    MID = "mid"
    HIGH = "high"


def _band_for_handicap_index(handicap_index: float) -> _HandicapBand:
    """Map a validated handicap index to its half-open containing band."""
    if handicap_index < 0.0:
        return _HandicapBand.PLUS
    if handicap_index < 9.0:
        return _HandicapBand.LOW
    if handicap_index < 18.0:
        return _HandicapBand.MID
    return _HandicapBand.HIGH


def _params(
    carry_scale_metres: float,
    lateral_scale_metres: float,
    correlation: float,
    degrees_of_freedom: float,
) -> PopulationPriorParameters:
    """Build a config-table cell with the uniform confidence/provenance for this version."""
    return PopulationPriorParameters(
        carry_scale_metres=carry_scale_metres,
        lateral_scale_metres=lateral_scale_metres,
        correlation=correlation,
        degrees_of_freedom=degrees_of_freedom,
    )


# Driver gets the strongest handicap-band differentiation in scale, per
# Betzler et al. (2012/2014, cited in the research doc) — the best-evidenced
# handicap-conditioned variability effect is for driver production. Lower
# handicap bands get smaller carry_scale_metres/lateral_scale_metres than
# higher bands within the same category (directionally evidence-backed;
# exact magnitudes are not — see module docstring). correlation and
# degrees_of_freedom are held constant across bands within a category where
# the evidence gives no basis to vary them (research doc items 2-3).
_DRIVER = {
    _HandicapBand.PLUS: _params(8.0, 6.0, 0.10, 8.0),
    _HandicapBand.LOW: _params(10.0, 8.0, 0.10, 8.0),
    _HandicapBand.MID: _params(13.0, 11.0, 0.10, 6.0),
    _HandicapBand.HIGH: _params(16.0, 14.0, 0.10, 5.0),
}

# FAIRWAY_WOOD and HYBRID share identical provisional values in every band:
# the research doc groups them together rather than analysing them as
# separate club-mechanics regimes, so inventing a distinction between them
# would not be defensible from the evidence available.
_FAIRWAY_WOOD_HYBRID = {
    _HandicapBand.PLUS: _params(6.0, 5.0, 0.05, 7.0),
    _HandicapBand.LOW: _params(7.5, 6.5, 0.05, 7.0),
    _HandicapBand.MID: _params(9.5, 8.5, 0.05, 5.0),
    _HandicapBand.HIGH: _params(11.5, 10.5, 0.05, 4.5),
}

_IRON = {
    _HandicapBand.PLUS: _params(4.0, 3.5, 0.0, 7.0),
    _HandicapBand.LOW: _params(5.0, 4.5, 0.0, 7.0),
    _HandicapBand.MID: _params(6.5, 6.0, 0.0, 5.0),
    _HandicapBand.HIGH: _params(8.0, 7.5, 0.0, 4.5),
}

_WEDGE = {
    _HandicapBand.PLUS: _params(3.0, 2.5, -0.05, 7.0),
    _HandicapBand.LOW: _params(3.5, 3.0, -0.05, 7.0),
    _HandicapBand.MID: _params(4.5, 4.0, -0.05, 5.0),
    _HandicapBand.HIGH: _params(5.5, 5.0, -0.05, 4.5),
}

POPULATION_PRIOR_CONFIG: dict[tuple[_HandicapBand, ClubCategory], PopulationPriorParameters] = {
    **{(band, ClubCategory.DRIVER): params for band, params in _DRIVER.items()},
    **{(band, ClubCategory.FAIRWAY_WOOD): params for band, params in _FAIRWAY_WOOD_HYBRID.items()},
    **{(band, ClubCategory.HYBRID): params for band, params in _FAIRWAY_WOOD_HYBRID.items()},
    **{(band, ClubCategory.IRON): params for band, params in _IRON.items()},
    **{(band, ClubCategory.WEDGE): params for band, params in _WEDGE.items()},
}


def lookup(handicap_index: float, club_category: ClubCategory) -> PopulationPriorParameters:
    """Look up the config cell for a (handicap_index, club_category) pair.

    Internally maps ``handicap_index`` to its private ``_HandicapBand``
    bucket before indexing the table. Callers are responsible for
    validating ``club_category`` is one of the 5 supported full-swing
    categories before calling this — a ``KeyError`` here indicates an
    unsupported category slipped past that check.
    """
    band = _band_for_handicap_index(handicap_index)
    return POPULATION_PRIOR_CONFIG[(band, club_category)]


__all__ = [
    "POPULATION_PRIOR_CONFIG",
    "POPULATION_PRIOR_CONFIG_VERSION",
    "_HandicapBand",
    "_band_for_handicap_index",
    "lookup",
]
