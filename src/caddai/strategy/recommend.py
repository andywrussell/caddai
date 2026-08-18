"""Deterministic M1 placeholder club recommendation logic.

This is an intentionally primitive placeholder strategy for milestone M1,
proving the end-to-end architecture. It is not a realistic golf strategy
model — see docs/roadmap.md M4/M5 for the real expected-value/Monte Carlo
model.
"""

from caddai.strategy.models import (
    LieType,
    RecommendationRequest,
    RecommendationResult,
    WindDirection,
)

# Arbitrary placeholder pending a real physical wind model.
WIND_ADJUSTMENT_METRES_PER_MPS: float = 1.5

# Arbitrary placeholders pending a real statistical lie-difficulty model.
LIE_ADJUSTMENT_METRES: dict[LieType, float] = {
    LieType.TEE: 0.0,
    LieType.FAIRWAY: 0.0,
    LieType.ROUGH: 5.0,
    LieType.BUNKER: 10.0,
    LieType.RECOVERY: 15.0,
}

# Arbitrary placeholder pending a real statistical confidence model.
CONFIDENCE_ZERO_AT_METRES: float = 20.0


def recommend_club(request: RecommendationRequest) -> RecommendationResult:
    """Recommend a club for the given shot request.

    See module docstring: this is an intentionally primitive placeholder
    strategy for milestone M1, proving the end-to-end architecture. It is
    not a realistic golf strategy model — see docs/roadmap.md M4/M5 for the
    real expected-value/Monte Carlo model.
    """
    if request.wind.direction is WindDirection.HEADWIND:
        wind_adjustment_metres = request.wind.speed_mps * WIND_ADJUSTMENT_METRES_PER_MPS
    elif request.wind.direction is WindDirection.TAILWIND:
        wind_adjustment_metres = -request.wind.speed_mps * WIND_ADJUSTMENT_METRES_PER_MPS
    else:
        wind_adjustment_metres = 0.0

    lie_adjustment_metres = LIE_ADJUSTMENT_METRES[request.lie]
    playing_distance_metres = max(
        0.0,
        request.target_distance_metres + wind_adjustment_metres + lie_adjustment_metres,
    )

    selected_club = min(
        request.player.clubs,
        key=lambda club: abs(club.expected_carry_metres - playing_distance_metres),
    )
    gap_metres = abs(selected_club.expected_carry_metres - playing_distance_metres)
    confidence = max(0.0, min(1.0, 1.0 - gap_metres / CONFIDENCE_ZERO_AT_METRES))

    reasons = [
        f"Target distance {request.target_distance_metres:.1f}m adjusted to "
        f"{playing_distance_metres:.1f}m playing distance for "
        f"{request.wind.speed_mps:.1f} m/s {request.wind.direction.value} wind and "
        f"{request.lie.value} lie.",
        f"Selected {selected_club.name} as its expected carry of "
        f"{selected_club.expected_carry_metres:.1f}m is closest to the "
        f"{playing_distance_metres:.1f}m playing distance.",
        "This is a primitive M1 placeholder strategy: it does not model shot "
        "dispersion, course conditions, or risk.",
    ]

    return RecommendationResult(
        selected_club=selected_club,
        playing_distance_metres=playing_distance_metres,
        confidence=confidence,
        reasons=reasons,
    )
