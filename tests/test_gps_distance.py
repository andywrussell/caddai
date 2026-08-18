"""Tests for the M2.1 GPS distance and bearing functions in ``caddai.gps.distance``.

See GitHub issue #3 ("M2.1 — GPS coordinate & distance primitives") for the
acceptance criteria these tests are derived from.

Reference values use the standard haversine formula with the documented mean
Earth-radius approximation of 6,371,000 metres (Architect guidance for this
issue). Distances along the equator or a single meridian are exact
great-circle arcs (``radius * central_angle_radians``) regardless of the
haversine formula, so they double as an independently-derived reference,
not merely a re-run of the implementation under test. Well-known city-pair
distances are included as an additional cross-check against widely
published approximate figures (e.g. London-Paris ~344 km), with a looser
tolerance since published figures vary slightly by source coordinates and
Earth-radius model.

Bearing is the initial (forward) compass bearing in degrees, clockwise from
true north, normalized to [0, 360), for the great-circle path from origin to
destination (not a rhumb line). Reference cases below use points on the
equator or a single meridian, where the great-circle path coincides exactly
with the parallel or meridian, making the expected bearing unambiguous
(0/90/180/270 degrees) without relying on an approximation.
"""

import math

import pytest

from caddai.gps.distance import haversine_distance_metres, initial_bearing_degrees
from caddai.gps.models import Coordinate

EARTH_RADIUS_METRES: float = 6_371_000.0

# Central angle for the reference pairs below: 10 degrees of latitude or
# longitude, expressed in radians for the exact arc-length formula.
TEN_DEGREES_ARC_METRES: float = EARTH_RADIUS_METRES * math.radians(10.0)


def test_ten_degrees_along_equator_matches_exact_arc_length() -> None:
    """Distance along the equator equals radius * angle, an exact great-circle case."""
    origin = Coordinate(latitude=0.0, longitude=0.0)
    destination = Coordinate(latitude=0.0, longitude=10.0)

    distance_metres = haversine_distance_metres(origin, destination)

    assert distance_metres == pytest.approx(TEN_DEGREES_ARC_METRES, rel=1e-6)


def test_ten_degrees_along_meridian_matches_exact_arc_length() -> None:
    """Distance along a meridian equals radius * angle, an exact great-circle case."""
    origin = Coordinate(latitude=0.0, longitude=0.0)
    destination = Coordinate(latitude=10.0, longitude=0.0)

    distance_metres = haversine_distance_metres(origin, destination)

    assert distance_metres == pytest.approx(TEN_DEGREES_ARC_METRES, rel=1e-6)


def test_distance_between_identical_coordinates_is_zero() -> None:
    """Two identical points are zero metres apart."""
    point = Coordinate(latitude=51.5074, longitude=-0.1278)

    assert haversine_distance_metres(point, point) == pytest.approx(0.0, abs=1e-6)


def test_distance_is_symmetric() -> None:
    """Distance from A to B equals distance from B to A."""
    london = Coordinate(latitude=51.5074, longitude=-0.1278)
    paris = Coordinate(latitude=48.8566, longitude=2.3522)

    forward = haversine_distance_metres(london, paris)
    backward = haversine_distance_metres(paris, london)

    assert forward == pytest.approx(backward)


@pytest.mark.parametrize(
    ("origin", "destination", "expected_metres"),
    [
        (
            Coordinate(latitude=51.5074, longitude=-0.1278),
            Coordinate(latitude=48.8566, longitude=2.3522),
            343_556.06,
        ),
        (
            Coordinate(latitude=40.7128, longitude=-74.0060),
            Coordinate(latitude=34.0522, longitude=-118.2437),
            3_935_746.25,
        ),
        (
            Coordinate(latitude=-33.8688, longitude=151.2093),
            Coordinate(latitude=-37.8136, longitude=144.9631),
            713_427.48,
        ),
    ],
    ids=["london-to-paris", "new-york-to-los-angeles", "sydney-to-melbourne"],
)
def test_known_city_pair_distances_match_haversine_reference(
    origin: Coordinate, destination: Coordinate, expected_metres: float
) -> None:
    """Known city-pair distances (~344 km, ~3,936 km, ~713 km) match within 0.1%."""
    distance_metres = haversine_distance_metres(origin, destination)

    assert distance_metres == pytest.approx(expected_metres, rel=1e-3)


def test_bearing_due_east_along_equator_is_90_degrees() -> None:
    """Moving east along the equator has an initial bearing of exactly 90 degrees."""
    origin = Coordinate(latitude=0.0, longitude=0.0)
    destination = Coordinate(latitude=0.0, longitude=10.0)

    assert initial_bearing_degrees(origin, destination) == pytest.approx(90.0)


def test_bearing_due_west_along_equator_is_270_degrees() -> None:
    """Moving west along the equator has an initial bearing of exactly 270 degrees."""
    origin = Coordinate(latitude=0.0, longitude=10.0)
    destination = Coordinate(latitude=0.0, longitude=0.0)

    assert initial_bearing_degrees(origin, destination) == pytest.approx(270.0)


def test_bearing_due_north_along_meridian_is_0_degrees() -> None:
    """Moving north along a meridian has an initial bearing of exactly 0 degrees."""
    origin = Coordinate(latitude=0.0, longitude=0.0)
    destination = Coordinate(latitude=10.0, longitude=0.0)

    assert initial_bearing_degrees(origin, destination) == pytest.approx(0.0, abs=1e-6)


def test_bearing_due_south_along_meridian_is_180_degrees() -> None:
    """Moving south along a meridian has an initial bearing of exactly 180 degrees."""
    origin = Coordinate(latitude=10.0, longitude=0.0)
    destination = Coordinate(latitude=0.0, longitude=0.0)

    assert initial_bearing_degrees(origin, destination) == pytest.approx(180.0)


def test_bearing_reverses_by_180_degrees_along_equator() -> None:
    """The reverse equatorial leg's initial bearing is exactly 180 degrees away."""
    a = Coordinate(latitude=0.0, longitude=0.0)
    b = Coordinate(latitude=0.0, longitude=10.0)

    forward = initial_bearing_degrees(a, b)
    backward = initial_bearing_degrees(b, a)

    assert (backward - forward) % 360.0 == pytest.approx(180.0)


@pytest.mark.parametrize(
    ("origin", "destination"),
    [
        (
            Coordinate(latitude=51.5074, longitude=-0.1278),
            Coordinate(latitude=48.8566, longitude=2.3522),
        ),
        (
            Coordinate(latitude=-33.8688, longitude=151.2093),
            Coordinate(latitude=-37.8136, longitude=144.9631),
        ),
        (
            Coordinate(latitude=0.0, longitude=0.0),
            Coordinate(latitude=0.0, longitude=-10.0),
        ),
    ],
    ids=["london-to-paris", "sydney-to-melbourne", "equator-westward-negative-longitude"],
)
def test_bearing_is_normalized_to_0_360_degrees(
    origin: Coordinate, destination: Coordinate
) -> None:
    """Bearing is always normalized to the half-open range [0, 360) degrees."""
    bearing_degrees = initial_bearing_degrees(origin, destination)

    assert 0.0 <= bearing_degrees < 360.0
