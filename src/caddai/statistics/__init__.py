"""Statistics subsystem: carry distribution and shot dispersion models.

See docs/player-model.md for the full planned design.
"""

from caddai.statistics.models import (
    CarryDistribution,
    ClubCategory,
    DirectionalDispersion,
    PopulationPriorParameters,
)
from caddai.statistics.personalisation import (
    DEFAULT_PERSONALISATION_CONFIG,
    STATISTICS_PERSONALISATION_CONFIG_VERSION,
    DimensionUpdateOutcome,
    PersonalisationConfig,
    ShotDistributionUpdateResult,
    WeightedJointObservations,
    WeightedObservations,
    shrink_shot_distribution,
)
from caddai.statistics.population_prior import (
    CLUB_CATEGORY_SUPPORT_STATUS,
    ClubCategorySupportStatus,
    PopulationPriorConfidence,
    PopulationPriorProvenance,
    PopulationPriorResult,
    PopulationPriorUnsupportedCategoryError,
    club_category_support_status,
    resolve_population_prior,
)
from caddai.statistics.shot_distribution import (
    PlayerShotDistribution,
    ShotDistributionFamily,
)

__all__ = [
    "CLUB_CATEGORY_SUPPORT_STATUS",
    "DEFAULT_PERSONALISATION_CONFIG",
    "STATISTICS_PERSONALISATION_CONFIG_VERSION",
    "CarryDistribution",
    "ClubCategory",
    "ClubCategorySupportStatus",
    "DimensionUpdateOutcome",
    "DirectionalDispersion",
    "PersonalisationConfig",
    "PlayerShotDistribution",
    "PopulationPriorConfidence",
    "PopulationPriorParameters",
    "PopulationPriorProvenance",
    "PopulationPriorResult",
    "PopulationPriorUnsupportedCategoryError",
    "ShotDistributionFamily",
    "ShotDistributionUpdateResult",
    "WeightedJointObservations",
    "WeightedObservations",
    "club_category_support_status",
    "resolve_population_prior",
    "shrink_shot_distribution",
]
