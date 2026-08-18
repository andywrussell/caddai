"""Tests for the M2.2 course-local planar coordinate projection.

See GitHub issue #4 ("M2.2 — Course-local planar coordinate projection") for
the acceptance criteria these tests are derived from: a local
equirectangular/tangent-plane approximation around a fixed origin
``Coordinate``, using the closed-form affine map

    x_metres = R * radians(lon - lon0) * cos(radians(lat0))
    y_metres = R * radians(lat - lat0)

and its algebraic inverse, where ``R`` is the mean Earth radius already
established in ``caddai.gps.distance`` (``EARTH_RADIUS_METRES``). The
origin's latitude scale factor (``cos(lat0)``) is fixed from the origin
only, making the map exact and simple to invert. This is a small-area
approximation, not a general-purpose geodesic projection, and is only
expected to be accurate for points within roughly a 2 km radius of the
origin -- general geodesic accuracy far from the origin is explicitly out
of scope.

Reference values below are derived independently of the projection module
under test:

- A point due north of the origin (same longitude) has ``x_metres == 0.0``
  exactly (the longitude delta is zero), and ``y_metres`` equal to the exact
  great-circle arc length along a meridian, ``R * radians(delta_latitude)``
  -- the same exact-arc-length reasoning already used as an independent
  check in ``tests/test_gps_distance.py``.
- A point due east of the origin (same latitude) has ``y_metres == 0.0``
  exactly, and ``x_metres`` equal to that same arc length scaled by
  ``cos(radians(lat0))``. For an origin latitude of 45 degrees, this scale
  factor is the well-known exact value ``sqrt(2) / 2``, computed here
  without calling ``math.cos`` to keep the reference independent of the
  implementation.
- Round-trips are verified via ``haversine_distance_metres`` (already tested
  in M2.1), not by re-deriving the projection formula, so the check does not
  depend on trusting the same code path being tested.

Assumed public API of ``caddai.gps.projection`` (Course Engineer's exact
implementation choice, confirmed here so the tests below have something
concrete to import):

    class LocalPoint:
        x_metres: float
        y_metres: float

    def to_local(origin: Coordinate, point: Coordinate) -> LocalPoint: ...
    def to_coordinate(origin: Coordinate, point: LocalPoint) -> Coordinate: ...
"""

import math

import pytest

from caddai.gps.distance import EARTH_RADIUS_METRES, haversine_distance_metres
from caddai.gps.models import Coordinate
from caddai.gps.projection import LocalPoint, to_coordinate, to_local

# Small offset (in degrees) used for the hand-verifiable north/east reference
# points below -- small enough to stay well within the documented 2 km
# small-area-approximation range.
OFFSET_DEGREES: float = 0.001

# Exact great-circle arc length for OFFSET_DEGREES of latitude/longitude at
# the equator or along any meridian: radius * angle in radians. Identical
# reasoning to the meridian/equator exact-arc-length tests in
# tests/test_gps_distance.py.
EXPECTED_ARC_METRES: float = EARTH_RADIUS_METRES * math.radians(OFFSET_DEGREES)

# cos(45 degrees), the exact closed-form value, computed without calling
# math.cos so the reference is independent of the implementation under test.
COS_45_DEGREES: float = math.sqrt(2.0) / 2.0


def test_origin_projects_to_zero_zero() -> None:
    """The origin itself is always the planar coordinate (0.0, 0.0)."""
    origin = Coordinate(latitude=45.0, longitude=-100.0)

    local = to_local(origin, origin)

    assert local.x_metres == pytest.approx(0.0, abs=1e-9)
    assert local.y_metres == pytest.approx(0.0, abs=1e-9)


def test_point_due_north_of_origin_matches_exact_meridian_arc_length() -> None:
    """A point due north (same longitude) has x=0 and y = exact meridian arc length."""
    origin = Coordinate(latitude=45.0, longitude=-100.0)
    north_point = Coordinate(latitude=45.0 + OFFSET_DEGREES, longitude=-100.0)

    local = to_local(origin, north_point)

    assert local.x_metres == pytest.approx(0.0, abs=1e-9)
    assert local.y_metres == pytest.approx(EXPECTED_ARC_METRES, rel=1e-9)


def test_point_due_east_of_origin_matches_arc_length_scaled_by_cosine() -> None:
    """A point due east (same latitude) has y=0 and x = arc length * cos(lat0)."""
    origin = Coordinate(latitude=45.0, longitude=-100.0)
    east_point = Coordinate(latitude=45.0, longitude=-100.0 + OFFSET_DEGREES)

    local = to_local(origin, east_point)

    assert local.y_metres == pytest.approx(0.0, abs=1e-9)
    assert local.x_metres == pytest.approx(EXPECTED_ARC_METRES * COS_45_DEGREES, rel=1e-9)


def test_equatorial_origin_scale_factor_is_one() -> None:
    """At lat0=0 the degenerate-but-valid cos(lat0) scale factor is exactly 1.

    A point due east of an equatorial origin therefore has the same
    x_metres as the unscaled meridian arc length -- the cosine scale factor
    drops out entirely, unlike the lat0=45 case above.
    """
    origin = Coordinate(latitude=0.0, longitude=0.0)
    east_point = Coordinate(latitude=0.0, longitude=OFFSET_DEGREES)

    local = to_local(origin, east_point)

    assert local.y_metres == pytest.approx(0.0, abs=1e-9)
    assert local.x_metres == pytest.approx(EXPECTED_ARC_METRES, rel=1e-9)


@pytest.mark.parametrize("polar_latitude", [90.0, -90.0], ids=["north-pole", "south-pole"])
def test_to_local_raises_value_error_for_polar_origin(polar_latitude: float) -> None:
    """A polar origin (latitude = +-90) makes cos(lat0) exactly 0, which is
    undefined for the inverse map -- to_local must raise a clear ValueError
    rather than let a later ZeroDivisionError leak out of to_coordinate.
    """
    origin = Coordinate(latitude=polar_latitude, longitude=0.0)
    point = Coordinate(latitude=45.0, longitude=10.0)

    with pytest.raises(ValueError, match=r"(?i)polar|pole|90|undefined"):
        to_local(origin, point)


@pytest.mark.parametrize("polar_latitude", [90.0, -90.0], ids=["north-pole", "south-pole"])
def test_to_coordinate_raises_value_error_for_polar_origin(polar_latitude: float) -> None:
    """Same polar-origin guard as to_local, but for the inverse direction,
    where the undefined cos(lat0) term appears in a division rather than a
    multiplication.
    """
    origin = Coordinate(latitude=polar_latitude, longitude=0.0)
    point = LocalPoint(x_metres=100.0, y_metres=100.0)

    with pytest.raises(ValueError, match=r"(?i)polar|pole|90|undefined"):
        to_coordinate(origin, point)


def test_local_point_at_planar_origin_unprojects_to_the_origin_coordinate() -> None:
    """to_coordinate at the planar origin (0, 0) always recovers the origin coordinate itself."""
    origin = Coordinate(latitude=45.0, longitude=-100.0)

    recovered = to_coordinate(origin, LocalPoint(x_metres=0.0, y_metres=0.0))

    assert recovered.latitude == pytest.approx(origin.latitude, abs=1e-9)
    assert recovered.longitude == pytest.approx(origin.longitude, abs=1e-9)


@pytest.mark.parametrize(
    ("origin", "point"),
    [
        (
            Coordinate(latitude=45.0, longitude=-100.0),
            Coordinate(latitude=45.0, longitude=-100.0),
        ),
        (
            Coordinate(latitude=45.0, longitude=-100.0),
            Coordinate(latitude=45.012, longitude=-100.018),
        ),
        (
            Coordinate(latitude=0.0, longitude=0.0),
            Coordinate(latitude=0.015, longitude=0.015),
        ),
    ],
    ids=["origin-itself", "point-within-2km-radius", "equatorial-origin-point-within-2km"],
)
def test_round_trip_recovers_original_coordinate_within_one_centimetre(
    origin: Coordinate, point: Coordinate
) -> None:
    """to_coordinate(origin, to_local(origin, point)) recovers point within 1cm.

    Verified via haversine_distance_metres (already tested in M2.1) between
    the original and recovered point, rather than by comparing raw
    latitude/longitude fields directly -- an independent check that reuses a
    different, already-trusted code path.
    """
    local = to_local(origin, point)

    recovered = to_coordinate(origin, local)

    round_trip_error_metres = haversine_distance_metres(point, recovered)
    assert round_trip_error_metres <= 0.01


def test_planar_distance_approximates_haversine_distance_for_course_sized_points() -> None:
    """Euclidean distance between two projected points matches haversine distance closely.

    Both points are within ~400m of the origin -- course-sized offsets, well
    inside the documented small-area-approximation range -- so the planar
    approximation should track the true great-circle distance to within a
    small documented percentage tolerance (0.1%).
    """
    origin = Coordinate(latitude=45.0, longitude=-100.0)
    point_a = Coordinate(latitude=45.0015, longitude=-100.0020)
    point_b = Coordinate(latitude=45.0035, longitude=-100.0010)

    local_a = to_local(origin, point_a)
    local_b = to_local(origin, point_b)
    planar_distance_metres = math.hypot(
        local_b.x_metres - local_a.x_metres, local_b.y_metres - local_a.y_metres
    )

    haversine_distance = haversine_distance_metres(point_a, point_b)

    assert planar_distance_metres == pytest.approx(haversine_distance, rel=1e-3)


def test_planar_distance_approximates_haversine_distance_near_2km_validity_radius() -> None:
    """The approximation still tracks haversine distance near the documented
    ~2 km validity radius, with a looser (but still small) tolerance than the
    course-sized (~400m) case above.

    Both points are ~1.7-1.9 km from the origin -- near the edge of the
    documented small-area-approximation range, rather than the ~200-400m
    course-sized offsets above. Measured independently against this test
    (uv run pytest, see PR discussion for issue #4): the relative error here
    is ~0.021%, versus ~0.0005% for the ~400m case, confirming the
    equirectangular approximation's error grows with distance from the
    origin as expected. 0.5% leaves a comfortable margin above that measured
    value while still catching a materially broken approximation.
    """
    origin = Coordinate(latitude=45.0, longitude=-100.0)
    point_a = Coordinate(latitude=45.013, longitude=-100.015)
    point_b = Coordinate(latitude=45.011, longitude=-99.985)

    local_a = to_local(origin, point_a)
    local_b = to_local(origin, point_b)
    planar_distance_metres = math.hypot(
        local_b.x_metres - local_a.x_metres, local_b.y_metres - local_a.y_metres
    )

    haversine_distance = haversine_distance_metres(point_a, point_b)

    assert planar_distance_metres == pytest.approx(haversine_distance, rel=5e-3)
