"""Developer demo: run the real recommendation engine on a fixed scenario.

Run with ``uv run python -m caddai.strategy.demo``. This is a thin
presentation wrapper only — all club-selection, wind/lie-adjustment, and
confidence logic comes from the real `recommend_club()` in
`caddai.strategy.recommend`.
"""

from caddai.player import Club, Player
from caddai.strategy.models import LieType, RecommendationRequest, Wind, WindDirection
from caddai.strategy.recommend import recommend_club


def build_demo_request() -> RecommendationRequest:
    """Build a fixed, deterministic demo scenario for a single shot."""
    player = Player(
        name="Demo Golfer",
        clubs=[
            Club.with_expected_carry(name="7 Iron", expected_carry_metres=145.0),
            Club.with_expected_carry(name="6 Iron", expected_carry_metres=155.0),
            Club.with_expected_carry(name="5 Iron", expected_carry_metres=165.0),
            Club.with_expected_carry(name="Hybrid", expected_carry_metres=180.0),
            Club.with_expected_carry(name="3 Wood", expected_carry_metres=210.0),
        ],
    )
    return RecommendationRequest(
        player=player,
        target_distance_metres=160.0,
        wind=Wind(speed_mps=6.0, direction=WindDirection.HEADWIND),
        lie=LieType.FAIRWAY,
    )


def main() -> None:
    """Print a human-readable recommendation for the fixed demo scenario."""
    result = recommend_club(build_demo_request())

    print("CaddAI recommendation demo")
    print("===========================")
    print(f"Selected club: {result.selected_club.name}")
    print(f"Playing distance: {result.playing_distance_metres:.1f}m")
    print(f"Confidence: {result.confidence * 100:.1f}%")
    print("Reasons:")
    for reason in result.reasons:
        print(f"- {reason}")


if __name__ == "__main__":
    main()
