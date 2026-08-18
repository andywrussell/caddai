"""Strategy subsystem: deterministic shot recommendation.

See docs/strategy-engine.md for the full planned design.
"""

from caddai.strategy.models import (
    LieType,
    RecommendationRequest,
    RecommendationResult,
    Wind,
    WindDirection,
)
from caddai.strategy.recommend import recommend_club

__all__ = [
    "LieType",
    "RecommendationRequest",
    "RecommendationResult",
    "Wind",
    "WindDirection",
    "recommend_club",
]
