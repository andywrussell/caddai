"""Tests for the M1 player domain model: ``Club`` and ``Player``.

See docs/plans/m1-core-domain-vertical-slice.plan.md Task 1 for the
acceptance criteria these tests are derived from.
"""

import pytest
from pydantic import ValidationError

from caddai.player.models import Club, Player


def test_club_constructs_with_valid_data() -> None:
    """A club with a non-empty name and positive carry is accepted."""
    club = Club(name="7 Iron", expected_carry_metres=140.0)

    assert club.name == "7 Iron"
    assert club.expected_carry_metres == pytest.approx(140.0)


def test_club_rejects_empty_name() -> None:
    """An empty club name violates the non-empty-name invariant."""
    with pytest.raises(ValidationError):
        Club(name="", expected_carry_metres=140.0)


@pytest.mark.parametrize("expected_carry_metres", [0.0, -1.0, -140.0])
def test_club_rejects_non_positive_expected_carry(expected_carry_metres: float) -> None:
    """Zero or negative expected carry distance is physically meaningless."""
    with pytest.raises(ValidationError):
        Club(name="7 Iron", expected_carry_metres=expected_carry_metres)


def test_player_constructs_with_valid_data() -> None:
    """A player with a non-empty name and at least one club is accepted."""
    clubs = [Club(name="7 Iron", expected_carry_metres=140.0)]

    player = Player(name="Ada", clubs=clubs)

    assert player.name == "Ada"
    assert player.clubs == clubs


def test_player_rejects_empty_name() -> None:
    """An empty player name violates the non-empty-name invariant."""
    clubs = [Club(name="7 Iron", expected_carry_metres=140.0)]

    with pytest.raises(ValidationError):
        Player(name="", clubs=clubs)


def test_player_rejects_empty_clubs_list() -> None:
    """A player must own at least one club — an empty bag is invalid, not silently accepted."""
    with pytest.raises(ValidationError):
        Player(name="Ada", clubs=[])
