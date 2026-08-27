"""Population-derived parameter prior for ``PlayerShotDistribution``.

Implements the ADR 0007 (docs/adr/0007-population-prior-replaceability.md)
``PopulationPrior`` contract: a stable, replaceable handicap/club-category
lookup that resolves to a partial bivariate Student-t parameter bundle
(``PopulationPriorParameters``), backed by a small, explicit, versioned,
provisional config table (``population_prior_config.py``).

This module does **not** return a ``PlayerShotDistribution``.
``carry_location_metres``/``lateral_bias_metres`` are not
evidence-supportable from handicap + club-category alone — a golfer's
actual carry and directional tendency require their own reported/observed
data, which is M4.3 onboarding's responsibility, not this population-level
lookup's. Inventing population defaults for those two fields would be
exactly the fabrication
docs/research/m4-probabilistic-golfer-model.md warns against.

**M3<->M4 pipeline note** (for M4.3's implementer): a future
``PlayerShotDistribution`` is built by combining onboarding-derived
``carry_location_metres``/``lateral_bias_metres`` (M4.3) with this module's
``carry_scale_metres``/``lateral_scale_metres``/``correlation``/
``degrees_of_freedom`` (``PopulationPriorParameters``, this issue) — until
M4.5 personalisation supersedes the population-sourced scale/correlation/dof
with parameters learned from a player's own ``ShotRecord`` history.

No ``sample()``, no RNG, no NumPy-random calls, and no Monte Carlo logic
exist anywhere in this module — resolution is a deterministic, side-effect
free table lookup.
"""

import math
from enum import StrEnum

from pydantic import BaseModel, Field

from caddai.statistics.models import ClubCategory, HandicapBand, PopulationPriorParameters
from caddai.statistics.population_prior_config import POPULATION_PRIOR_CONFIG_VERSION, lookup


class PopulationPriorConfidence(StrEnum):
    """Qualitative confidence in a resolved population prior cell.

    Deliberately a 3-value qualitative scale, not a numeric 0-1 score — a
    numeric score would manufacture false precision the evidence doesn't
    support.
    """

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class PopulationPriorProvenance(StrEnum):
    """Where a resolved population prior's numeric values came from."""

    EVIDENCE_INFORMED_PROVISIONAL_CONFIG = "evidence_informed_provisional_config"
    CADDAI_CALIBRATION = "caddai_calibration"
    FITTED_MODEL = "fitted_model"


_MIN_HANDICAP_INDEX = -10.0
_MAX_HANDICAP_INDEX = 54.0

_SUPPORTED_CLUB_CATEGORIES = (
    ClubCategory.DRIVER,
    ClubCategory.FAIRWAY_WOOD,
    ClubCategory.HYBRID,
    ClubCategory.IRON,
    ClubCategory.WEDGE,
)


class PopulationPriorResult(BaseModel):
    """A resolved population prior: parameters plus provenance metadata.

    Does **not** wrap a ``PlayerShotDistribution`` — see the module
    docstring. ``handicap_index``, ``handicap_band``, and ``club_category``
    echo the resolved inputs for traceability only.
    """

    parameters: PopulationPriorParameters
    confidence: PopulationPriorConfidence
    provenance: PopulationPriorProvenance
    config_version: str = Field(min_length=1)
    handicap_band: HandicapBand
    club_category: ClubCategory
    handicap_index: float


def _resolve_handicap_band(handicap_index: float) -> HandicapBand:
    """Map a validated handicap index to its half-open containing band."""
    if handicap_index < 0.0:
        return HandicapBand.PLUS
    if handicap_index < 9.0:
        return HandicapBand.LOW
    if handicap_index < 18.0:
        return HandicapBand.MID
    return HandicapBand.HIGH


def resolve_population_prior(
    handicap_index: float, club_category: ClubCategory
) -> PopulationPriorResult:
    """Resolve the population-prior parameter bundle for a handicap/club-category pair.

    Raises ``ValueError`` if ``handicap_index`` is non-finite or outside the
    WHS Handicap Index practical bounds ``[-10.0, 54.0]`` (plus-handicap
    golfers are represented as negative values), or if ``club_category`` is
    not one of the 5 supported full-swing categories (``PUTTER``/``OTHER``
    are unsupported — see ``population_prior_config.py``).
    """
    if not math.isfinite(handicap_index):
        raise ValueError("handicap_index must be finite")
    if not (_MIN_HANDICAP_INDEX <= handicap_index <= _MAX_HANDICAP_INDEX):
        raise ValueError(
            f"handicap_index must be in [{_MIN_HANDICAP_INDEX}, {_MAX_HANDICAP_INDEX}], "
            f"got {handicap_index}"
        )
    if club_category not in _SUPPORTED_CLUB_CATEGORIES:
        raise ValueError(
            f"club_category must be one of {_SUPPORTED_CLUB_CATEGORIES}, got {club_category!r}"
        )

    handicap_band = _resolve_handicap_band(handicap_index)
    parameters = lookup(handicap_band, club_category)

    return PopulationPriorResult(
        parameters=parameters,
        confidence=PopulationPriorConfidence.LOW,
        provenance=PopulationPriorProvenance.EVIDENCE_INFORMED_PROVISIONAL_CONFIG,
        config_version=POPULATION_PRIOR_CONFIG_VERSION,
        handicap_band=handicap_band,
        club_category=club_category,
        handicap_index=handicap_index,
    )
