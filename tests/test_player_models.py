"""Tests for the player domain model: ``Club``, ``ClubCategory``, and ``Player``.

See GitHub issue #28 for the acceptance criteria covering composing
``Club`` from ``CarryDistribution`` and ``DirectionalDispersion`` rather
than a bare expected-carry scalar.

See GitHub issue #29 for the acceptance criteria covering ``ClubCategory``
and the required ``Club.category`` field: parametrized construction across
every category, rejection of an out-of-enum category string, and the
``with_expected_carry`` category default/override behaviour.
"""

import pytest
from pydantic import ValidationError

from caddai.player.models import Club, ClubCategory, Player
from caddai.statistics import CarryDistribution, DirectionalDispersion


def test_club_constructs_with_valid_data() -> None:
    """A club with a non-empty name and explicit distribution/dispersion round-trips."""
    carry_distribution = CarryDistribution(mean_metres=140.0, stddev_metres=8.5)
    dispersion = DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0)

    club = Club(
        name="7 Iron",
        carry_distribution=carry_distribution,
        dispersion=dispersion,
        category=ClubCategory.IRON,
    )

    assert club.name == "7 Iron"
    assert club.carry_distribution == carry_distribution
    assert club.dispersion == dispersion
    assert club.category == ClubCategory.IRON


def test_club_expected_carry_metres_reflects_carry_distribution_mean() -> None:
    """``expected_carry_metres`` is derived from ``carry_distribution.mean_metres``."""
    club = Club(
        name="7 Iron",
        carry_distribution=CarryDistribution(mean_metres=140.0, stddev_metres=8.5),
        dispersion=DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0),
        category=ClubCategory.IRON,
    )

    assert club.expected_carry_metres == pytest.approx(140.0)


@pytest.mark.parametrize(
    ("stddev_metres", "lateral_stddev_metres", "lateral_bias_metres"),
    [
        (0.0, 0.0, 0.0),
        (8.5, 4.5, -2.0),
        (20.0, 10.0, 5.0),
    ],
)
def test_club_expected_carry_metres_independent_of_dispersion(
    stddev_metres: float, lateral_stddev_metres: float, lateral_bias_metres: float
) -> None:
    """``expected_carry_metres`` depends only on ``mean_metres``, not on any spread values."""
    club = Club(
        name="7 Iron",
        carry_distribution=CarryDistribution(mean_metres=150.0, stddev_metres=stddev_metres),
        dispersion=DirectionalDispersion(
            lateral_stddev_metres=lateral_stddev_metres,
            lateral_bias_metres=lateral_bias_metres,
        ),
        category=ClubCategory.IRON,
    )

    assert club.expected_carry_metres == pytest.approx(150.0)


def test_club_rejects_missing_carry_distribution() -> None:
    """A club without a ``carry_distribution`` is not a valid club."""
    with pytest.raises(ValidationError):
        Club(
            name="7 Iron",
            dispersion=DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0),
            category=ClubCategory.IRON,
        )


def test_club_rejects_missing_dispersion() -> None:
    """A club without a ``dispersion`` is not a valid club."""
    with pytest.raises(ValidationError):
        Club(
            name="7 Iron",
            carry_distribution=CarryDistribution(mean_metres=140.0, stddev_metres=8.5),
            category=ClubCategory.IRON,
        )


def test_club_rejects_bare_scalar_carry_distribution() -> None:
    """Regression guard: the old bare-scalar ``Club`` shape is no longer accepted."""
    with pytest.raises(ValidationError):
        Club(
            name="7 Iron",
            carry_distribution=140.0,
            dispersion=DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0),
            category=ClubCategory.IRON,
        )


def test_club_coerces_nested_dicts_into_models() -> None:
    """Nested dicts for ``carry_distribution``/``dispersion`` are coerced into real models."""
    club = Club(
        name="7 Iron",
        carry_distribution={"mean_metres": 140.0, "stddev_metres": 8.5},
        dispersion={"lateral_stddev_metres": 4.5, "lateral_bias_metres": -2.0},
        category=ClubCategory.IRON,
    )

    assert isinstance(club.carry_distribution, CarryDistribution)
    assert isinstance(club.dispersion, DirectionalDispersion)
    assert club.carry_distribution.mean_metres == pytest.approx(140.0)
    assert club.carry_distribution.stddev_metres == pytest.approx(8.5)
    assert club.dispersion.lateral_stddev_metres == pytest.approx(4.5)
    assert club.dispersion.lateral_bias_metres == pytest.approx(-2.0)


@pytest.mark.parametrize("mean_metres", [0.0, -1.0, -140.0])
def test_club_rejects_invalid_nested_carry_distribution(mean_metres: float) -> None:
    """``CarryDistribution``'s ``gt=0`` constraint bubbles up through ``Club``."""
    with pytest.raises(ValidationError):
        Club(
            name="7 Iron",
            carry_distribution={"mean_metres": mean_metres, "stddev_metres": 8.5},
            dispersion=DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0),
            category=ClubCategory.IRON,
        )


def test_club_rejects_empty_name() -> None:
    """An empty club name violates the non-empty-name invariant, even with valid nested models."""
    with pytest.raises(ValidationError):
        Club(
            name="",
            carry_distribution=CarryDistribution(mean_metres=140.0, stddev_metres=8.5),
            dispersion=DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0),
            category=ClubCategory.IRON,
        )


@pytest.mark.parametrize(
    "category",
    [
        ClubCategory.DRIVER,
        ClubCategory.FAIRWAY_WOOD,
        ClubCategory.HYBRID,
        ClubCategory.IRON,
        ClubCategory.WEDGE,
        ClubCategory.PUTTER,
        ClubCategory.OTHER,
    ],
)
def test_club_category_members_construct_valid_club(category: ClubCategory) -> None:
    """Every ``ClubCategory`` member is a ``str`` subclass and constructs a valid ``Club``."""
    assert isinstance(category, str)
    assert category == category.value

    club = Club(
        name="7 Iron",
        carry_distribution=CarryDistribution(mean_metres=140.0, stddev_metres=8.5),
        dispersion=DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0),
        category=category,
    )

    assert club.category == category


def test_club_rejects_invalid_category_string() -> None:
    """A ``category`` string outside ``ClubCategory``'s values is rejected."""
    with pytest.raises(ValidationError):
        Club(
            name="7 Iron",
            carry_distribution=CarryDistribution(mean_metres=140.0, stddev_metres=8.5),
            dispersion=DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0),
            category="mid-iron",
        )


def test_club_expected_carry_metres_is_read_only() -> None:
    """``expected_carry_metres`` is a derived computed field and cannot be assigned directly."""
    club = Club.with_expected_carry(name="7 Iron", expected_carry_metres=140.0)

    with pytest.raises(AttributeError):
        club.expected_carry_metres = 200.0


def test_club_with_expected_carry_builds_degenerate_distribution_and_dispersion() -> None:
    """The convenience constructor builds a zero-variance, zero-bias club from a bare scalar."""
    club = Club.with_expected_carry(name="7 Iron", expected_carry_metres=140.0)

    assert club.carry_distribution.mean_metres == pytest.approx(140.0)
    assert club.carry_distribution.stddev_metres == pytest.approx(0.0)
    assert club.dispersion.lateral_stddev_metres == pytest.approx(0.0)
    assert club.dispersion.lateral_bias_metres == pytest.approx(0.0)
    assert club.expected_carry_metres == pytest.approx(140.0)


@pytest.mark.parametrize("expected_carry_metres", [0.0, -1.0, -140.0])
def test_club_with_expected_carry_rejects_non_positive_expected_carry(
    expected_carry_metres: float,
) -> None:
    """Zero or negative expected carry distance is physically meaningless."""
    with pytest.raises(ValidationError):
        Club.with_expected_carry(name="7 Iron", expected_carry_metres=expected_carry_metres)


def test_club_with_expected_carry_rejects_empty_name() -> None:
    """An empty club name is rejected via the convenience constructor too."""
    with pytest.raises(ValidationError):
        Club.with_expected_carry(name="", expected_carry_metres=140.0)


def test_club_with_expected_carry_is_deterministic() -> None:
    """Two clubs built from the same arguments are equal — load-bearing for demo determinism."""
    assert Club.with_expected_carry("7 Iron", 140.0) == Club.with_expected_carry("7 Iron", 140.0)


def test_club_with_expected_carry_defaults_category_to_other() -> None:
    """Without an explicit ``category``, the convenience constructor defaults to ``OTHER``."""
    club = Club.with_expected_carry(name="7 Iron", expected_carry_metres=140.0)

    assert club.category == ClubCategory.OTHER


def test_club_with_expected_carry_accepts_explicit_category() -> None:
    """An explicit ``category`` argument overrides the ``ClubCategory.OTHER`` default."""
    club = Club.with_expected_carry(
        name="Driver", expected_carry_metres=230.0, category=ClubCategory.DRIVER
    )

    assert club.category == ClubCategory.DRIVER


def test_player_constructs_with_valid_data() -> None:
    """A player with a non-empty name and at least one club is accepted."""
    clubs = [Club.with_expected_carry(name="7 Iron", expected_carry_metres=140.0)]

    player = Player(name="Ada", clubs=clubs)

    assert player.name == "Ada"
    assert player.clubs == clubs


def test_player_rejects_empty_name() -> None:
    """An empty player name violates the non-empty-name invariant."""
    clubs = [Club.with_expected_carry(name="7 Iron", expected_carry_metres=140.0)]

    with pytest.raises(ValidationError):
        Player(name="", clubs=clubs)


def test_player_rejects_empty_clubs_list() -> None:
    """A player must own at least one club — an empty bag is invalid, not silently accepted."""
    with pytest.raises(ValidationError):
        Player(name="Ada", clubs=[])
