"""Developer demo: run the real recommendation engine on a fixed scenario.

Run with ``uv run python -m caddai.strategy.demo``. This is a thin
presentation wrapper only — all club-selection, wind/lie-adjustment, and
confidence logic comes from the real `recommend_club()` in
`caddai.strategy.recommend`.
"""

from caddai.player import Club, ClubCategory, Player
from caddai.statistics import CarryDistribution, DirectionalDispersion
from caddai.strategy.models import LieType, RecommendationRequest, Wind, WindDirection
from caddai.strategy.recommend import recommend_club


def build_demo_request() -> RecommendationRequest:
    """Build a fixed, deterministic demo scenario for a single shot.

    Clubs are constructed directly (not via ``Club.with_expected_carry``) so
    each carries a realistic, non-degenerate carry distribution and
    directional dispersion — this makes the player-model context printed by
    `main()` non-trivial. These values are illustrative sample figures, not
    measured data, and are not used by `recommend_club()`'s selection logic.
    """
    player = Player(
        name="Demo Golfer",
        clubs=[
            Club(
                name="7 Iron",
                carry_distribution=CarryDistribution(mean_metres=145.0, stddev_metres=4.5),
                dispersion=DirectionalDispersion(
                    lateral_stddev_metres=6.0, lateral_bias_metres=1.0
                ),
                category=ClubCategory.IRON,
            ),
            Club(
                name="6 Iron",
                carry_distribution=CarryDistribution(mean_metres=155.0, stddev_metres=5.0),
                dispersion=DirectionalDispersion(
                    lateral_stddev_metres=6.5, lateral_bias_metres=0.5
                ),
                category=ClubCategory.IRON,
            ),
            Club(
                name="5 Iron",
                carry_distribution=CarryDistribution(mean_metres=165.0, stddev_metres=5.5),
                dispersion=DirectionalDispersion(
                    lateral_stddev_metres=7.0, lateral_bias_metres=-3.5
                ),
                category=ClubCategory.IRON,
            ),
            Club(
                name="Hybrid",
                carry_distribution=CarryDistribution(mean_metres=180.0, stddev_metres=7.0),
                dispersion=DirectionalDispersion(
                    lateral_stddev_metres=9.0, lateral_bias_metres=2.0
                ),
                category=ClubCategory.HYBRID,
            ),
            Club(
                name="3 Wood",
                carry_distribution=CarryDistribution(mean_metres=210.0, stddev_metres=9.0),
                dispersion=DirectionalDispersion(
                    lateral_stddev_metres=11.0, lateral_bias_metres=4.0
                ),
                category=ClubCategory.FAIRWAY_WOOD,
            ),
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
    selected_club = result.selected_club

    print("CaddAI recommendation demo")
    print("===========================")
    print(f"Selected club: {selected_club.name}")
    print(f"Playing distance: {result.playing_distance_metres:.1f}m")
    print(f"Confidence: {result.confidence * 100:.1f}%")
    print("Reasons:")
    for reason in result.reasons:
        print(f"- {reason}")

    bias_metres = selected_club.dispersion.lateral_bias_metres
    if bias_metres < 0:
        bias_side = "left"
    elif bias_metres > 0:
        bias_side = "right"
    else:
        bias_side = "on-line"

    print()
    print("Player-model context (informational only — not used in club selection):")
    print(f"- Club category: {selected_club.category.value}")
    print(f"- Expected carry: {selected_club.expected_carry_metres:.1f}m")
    print(f"- Carry variability (stddev): {selected_club.carry_distribution.stddev_metres:.1f}m")
    print(f"- Lateral dispersion (stddev): {selected_club.dispersion.lateral_stddev_metres:.1f}m")
    print(f"- Lateral bias: {bias_metres:+.1f}m ({bias_side} of target line)")


if __name__ == "__main__":
    main()
