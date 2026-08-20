"""Tests for the M1 recommendation logic in ``caddai.strategy.recommend``.

See docs/plans/m1-core-domain-vertical-slice.plan.md Task 2 for the
acceptance criteria these tests are derived from.
"""

import pytest
from pydantic import ValidationError

from caddai.player.models import Club, Player
from caddai.strategy.models import (
    LieType,
    RecommendationRequest,
    Wind,
    WindDirection,
)
from caddai.strategy.recommend import (
    CONFIDENCE_ZERO_AT_METRES,
    LIE_ADJUSTMENT_METRES,
    recommend_club,
)


def _three_club_player() -> Player:
    """A player with clubs carrying 100m, 120m, and 140m, in that order."""
    return Player(
        name="Ada",
        clubs=[
            Club.with_expected_carry(name="Wedge", expected_carry_metres=100.0),
            Club.with_expected_carry(name="8 Iron", expected_carry_metres=120.0),
            Club.with_expected_carry(name="6 Iron", expected_carry_metres=140.0),
        ],
    )


def _single_club_player(expected_carry_metres: float) -> Player:
    """A player with a single club, useful for isolating the confidence formula."""
    return Player(
        name="Ada",
        clubs=[
            Club.with_expected_carry(name="Test Club", expected_carry_metres=expected_carry_metres)
        ],
    )


def _request(
    player: Player,
    target_distance_metres: float,
    wind: Wind,
    lie: LieType,
) -> RecommendationRequest:
    return RecommendationRequest(
        player=player,
        target_distance_metres=target_distance_metres,
        wind=wind,
        lie=lie,
    )


def test_exact_match_selects_club_with_full_confidence() -> None:
    """A calm, fairway shot at exactly a club's carry selects that club with confidence 1.0."""
    player = _three_club_player()
    request = _request(
        player,
        target_distance_metres=120.0,
        wind=Wind(speed_mps=0.0, direction=WindDirection.HEADWIND),
        lie=LieType.FAIRWAY,
    )

    result = recommend_club(request)

    assert result.selected_club.name == "8 Iron"
    assert result.playing_distance_metres == pytest.approx(120.0)
    assert result.confidence == pytest.approx(1.0)
    assert len(result.reasons) > 0


def test_headwind_increases_playing_distance_versus_calm() -> None:
    """A headwind must lengthen the playing distance compared to still air."""
    player = _three_club_player()
    calm = _request(
        player,
        target_distance_metres=120.0,
        wind=Wind(speed_mps=0.0, direction=WindDirection.HEADWIND),
        lie=LieType.FAIRWAY,
    )
    headwind = _request(
        player,
        target_distance_metres=120.0,
        wind=Wind(speed_mps=5.0, direction=WindDirection.HEADWIND),
        lie=LieType.FAIRWAY,
    )

    calm_result = recommend_club(calm)
    headwind_result = recommend_club(headwind)

    assert headwind_result.playing_distance_metres > calm_result.playing_distance_metres


def test_tailwind_decreases_playing_distance_versus_calm() -> None:
    """A tailwind must shorten the playing distance compared to still air."""
    player = _three_club_player()
    calm = _request(
        player,
        target_distance_metres=120.0,
        wind=Wind(speed_mps=0.0, direction=WindDirection.TAILWIND),
        lie=LieType.FAIRWAY,
    )
    tailwind = _request(
        player,
        target_distance_metres=120.0,
        wind=Wind(speed_mps=5.0, direction=WindDirection.TAILWIND),
        lie=LieType.FAIRWAY,
    )

    calm_result = recommend_club(calm)
    tailwind_result = recommend_club(tailwind)

    assert tailwind_result.playing_distance_metres < calm_result.playing_distance_metres


def test_crosswind_leaves_playing_distance_unchanged_versus_calm() -> None:
    """A crosswind must not alter the playing distance in the M1 scalar wind model."""
    player = _three_club_player()
    calm = _request(
        player,
        target_distance_metres=120.0,
        wind=Wind(speed_mps=0.0, direction=WindDirection.CROSSWIND),
        lie=LieType.FAIRWAY,
    )
    crosswind = _request(
        player,
        target_distance_metres=120.0,
        wind=Wind(speed_mps=8.0, direction=WindDirection.CROSSWIND),
        lie=LieType.FAIRWAY,
    )

    calm_result = recommend_club(calm)
    crosswind_result = recommend_club(crosswind)

    assert crosswind_result.playing_distance_metres == pytest.approx(
        calm_result.playing_distance_metres
    )


def test_worse_lie_never_decreases_playing_distance() -> None:
    """A bunker lie must never produce a shorter playing distance than a fairway lie."""
    player = _three_club_player()
    fairway = _request(
        player,
        target_distance_metres=120.0,
        wind=Wind(speed_mps=0.0, direction=WindDirection.HEADWIND),
        lie=LieType.FAIRWAY,
    )
    bunker = _request(
        player,
        target_distance_metres=120.0,
        wind=Wind(speed_mps=0.0, direction=WindDirection.HEADWIND),
        lie=LieType.BUNKER,
    )

    fairway_result = recommend_club(fairway)
    bunker_result = recommend_club(bunker)

    assert bunker_result.playing_distance_metres >= fairway_result.playing_distance_metres


def test_lie_adjustment_constants_are_ordered_from_least_to_most_penalising() -> None:
    """The documented lie penalty ordering: tee/fairway <= rough < bunker < recovery."""
    assert LIE_ADJUSTMENT_METRES[LieType.TEE] == pytest.approx(0.0)
    assert LIE_ADJUSTMENT_METRES[LieType.FAIRWAY] == pytest.approx(0.0)
    assert LIE_ADJUSTMENT_METRES[LieType.ROUGH] > 0.0
    assert LIE_ADJUSTMENT_METRES[LieType.BUNKER] > LIE_ADJUSTMENT_METRES[LieType.ROUGH]
    assert LIE_ADJUSTMENT_METRES[LieType.RECOVERY] > LIE_ADJUSTMENT_METRES[LieType.BUNKER]


def test_playing_distance_floors_at_zero_for_strong_tailwind_and_small_target() -> None:
    """Playing distance must never go negative, even with a dominant tailwind adjustment."""
    player = _three_club_player()
    request = _request(
        player,
        target_distance_metres=1.0,
        wind=Wind(speed_mps=1000.0, direction=WindDirection.TAILWIND),
        lie=LieType.FAIRWAY,
    )

    result = recommend_club(request)

    assert result.playing_distance_metres == pytest.approx(0.0)


def test_confidence_strictly_decreases_as_gap_increases() -> None:
    """Confidence must strictly decrease as the winning club's distance gap widens."""
    player = _single_club_player(expected_carry_metres=100.0)
    wind = Wind(speed_mps=0.0, direction=WindDirection.HEADWIND)
    lie = LieType.FAIRWAY

    gap_zero = recommend_club(_request(player, target_distance_metres=100.0, wind=wind, lie=lie))
    gap_small = recommend_club(
        _request(
            player,
            target_distance_metres=100.0 + CONFIDENCE_ZERO_AT_METRES / 4,
            wind=wind,
            lie=lie,
        )
    )
    gap_large = recommend_club(
        _request(
            player,
            target_distance_metres=100.0 + CONFIDENCE_ZERO_AT_METRES / 2,
            wind=wind,
            lie=lie,
        )
    )

    assert gap_zero.confidence == pytest.approx(1.0)
    assert gap_zero.confidence > gap_small.confidence > gap_large.confidence


def test_confidence_is_exactly_zero_at_and_beyond_threshold() -> None:
    """Confidence hits exactly 0.0 at CONFIDENCE_ZERO_AT_METRES and stays there beyond it."""
    player = _single_club_player(expected_carry_metres=100.0)
    wind = Wind(speed_mps=0.0, direction=WindDirection.HEADWIND)

    at_threshold = recommend_club(
        _request(
            player,
            target_distance_metres=100.0 + CONFIDENCE_ZERO_AT_METRES,
            wind=wind,
            lie=LieType.FAIRWAY,
        )
    )
    beyond_threshold = recommend_club(
        _request(
            player,
            target_distance_metres=100.0 + CONFIDENCE_ZERO_AT_METRES * 10,
            wind=wind,
            lie=LieType.FAIRWAY,
        )
    )

    assert at_threshold.confidence == pytest.approx(0.0)
    assert beyond_threshold.confidence == pytest.approx(0.0)


def test_tied_distance_gap_is_broken_by_club_list_order() -> None:
    """When two clubs are equidistant from the playing distance, the first in the list wins."""
    player = Player(
        name="Ada",
        clubs=[
            Club.with_expected_carry(name="Short Club", expected_carry_metres=100.0),
            Club.with_expected_carry(name="Long Club", expected_carry_metres=140.0),
        ],
    )
    request = _request(
        player,
        target_distance_metres=120.0,
        wind=Wind(speed_mps=0.0, direction=WindDirection.HEADWIND),
        lie=LieType.FAIRWAY,
    )

    result = recommend_club(request)

    assert result.selected_club.name == "Short Club"


def test_reasons_cover_adjustment_club_choice_and_placeholder_disclaimer() -> None:
    """Reasons must explain the distance adjustment, the club choice, and the M1 caveat."""
    player = _three_club_player()
    request = _request(
        player,
        target_distance_metres=120.0,
        wind=Wind(speed_mps=5.0, direction=WindDirection.HEADWIND),
        lie=LieType.ROUGH,
    )

    result = recommend_club(request)
    reasons_text = " ".join(result.reasons).lower()

    assert any("wind" in reason.lower() for reason in result.reasons)
    assert any("rough" in reason.lower() or "lie" in reason.lower() for reason in result.reasons)
    assert any(result.selected_club.name.lower() in reason.lower() for reason in result.reasons)
    assert "primitive" in reasons_text or "placeholder" in reasons_text


def test_recommend_club_rejects_non_positive_target_distance() -> None:
    """A zero or negative target distance is not a valid shot request."""
    player = _three_club_player()

    with pytest.raises(ValidationError):
        _request(
            player,
            target_distance_metres=0.0,
            wind=Wind(speed_mps=0.0, direction=WindDirection.HEADWIND),
            lie=LieType.FAIRWAY,
        )


def test_wind_rejects_negative_speed() -> None:
    """A negative wind speed is not physically meaningful."""
    with pytest.raises(ValidationError):
        Wind(speed_mps=-1.0, direction=WindDirection.HEADWIND)
