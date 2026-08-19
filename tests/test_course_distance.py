"""Tests for the M2.5 distance-to-feature queries in ``caddai.course.distance``.

See GitHub issue #7 ("M2.5 — Distance-to-feature queries") for the
acceptance criteria these tests are derived from: signed distance to a
green's front/centre/back, and signed carry distance to a hazard, both
computed by projecting `player_position`, the aim point, and the feature's
`boundary` into one common local-metre frame per call (via
`caddai.gps.projection.to_local`, using `player_position` as the shared
origin) -- never reusing `caddai.course.models._local_polygon`'s per-feature
`boundary[0]`-anchored origin for anything involving the player's position.

`caddai.course.distance` does not exist yet at the time this file is
written -- these tests are handed to the Course Engineer to implement
against; the module will fail to collect (`ImportError`) until then.
"""

import math

import pytest
from shapely.geometry import Polygon

from caddai.course.distance import (
    GreenDistances,
    green_front_centre_back_distances,
    hazard_carry_distance,
)
from caddai.course.models import Feature, FeatureType, polygon_centroid
from caddai.gps.models import Coordinate
from caddai.gps.projection import LocalPoint, to_coordinate, to_local

# 5 cm, looser than the 1 cm ADR 0002/0003 tolerance used elsewhere: local-metre
# projection plus a Shapely polygon intersection introduces slightly more
# floating-point slop than a single `to_local`/`to_coordinate` round-trip.
ABS_TOLERANCE_METRES = 0.05

# The M2.4 fixture course's hole 1 green: an axis-aligned square (see
# tests/fixtures/sample_course.geojson), with the duplicated closing vertex
# dropped, matching `Feature.boundary`'s own representation.
HOLE_ONE_GREEN_BOUNDARY = (
    Coordinate(latitude=51.5100, longitude=-0.1225),
    Coordinate(latitude=51.5100, longitude=-0.1215),
    Coordinate(latitude=51.5110, longitude=-0.1215),
    Coordinate(latitude=51.5110, longitude=-0.1225),
)

# The M2.4 fixture course's hole 2 bunker: a triangle (see
# tests/fixtures/sample_course.geojson), closing vertex dropped.
HOLE_TWO_BUNKER_BOUNDARY = (
    Coordinate(latitude=51.5140, longitude=-0.1175),
    Coordinate(latitude=51.5140, longitude=-0.1165),
    Coordinate(latitude=51.5150, longitude=-0.1165),
)


def _unit_vector(player_position: Coordinate, aim_point: Coordinate) -> tuple[float, float]:
    """Unit direction vector from `player_position` toward `aim_point`, in the local frame.

    Uses `to_local` directly (a separate, already-tested primitive) -- this
    is legitimate hand computation, not a call into the module under test.
    """
    aim_local = to_local(player_position, aim_point)
    norm = math.hypot(aim_local.x_metres, aim_local.y_metres)
    return aim_local.x_metres / norm, aim_local.y_metres / norm


def _signed_distance(
    player_position: Coordinate, aim_point: Coordinate, point: Coordinate
) -> float:
    """Hand-computed signed distance of `point` along the player->aim direction.

    Mirrors the vector-projection semantics `distance.py` is expected to
    implement (dot product of `point`'s local offset with the unit
    player->aim direction vector), computed here directly via `to_local`,
    not by calling `green_front_centre_back_distances`/`hazard_carry_distance`.
    """
    unit_x, unit_y = _unit_vector(player_position, aim_point)
    point_local = to_local(player_position, point)
    return point_local.x_metres * unit_x + point_local.y_metres * unit_y


def _point_only_feature() -> Feature:
    """A `Feature` with no `boundary`, for the `boundary is None` `ValueError` tests."""
    return Feature(
        feature_type=FeatureType.GREEN, position=Coordinate(latitude=51.5000, longitude=-0.1000)
    )


# --- Hand-computed happy path (fixture geometry) ----------------------------


def test_green_front_centre_back_distances_matches_hand_computed_values_for_fixture_green() -> None:
    """Hand-computed front/centre/back distances for hole 1's fixture polygon green (issue #7).

    `player_position`'s longitude is chosen to exactly equal the green
    square's centroid longitude (-0.1220, the mean of -0.1225/-0.1215), so
    the line of play is a straight line of constant longitude: front/
    centre/back reduce to a 1-D distance-along-latitude calculation,
    hand-derived directly via `to_local` for the bottom edge (front), the
    green's own centroid (centre), and the top edge (back).
    """
    green_position = polygon_centroid(HOLE_ONE_GREEN_BOUNDARY)
    green = Feature(
        feature_type=FeatureType.GREEN, position=green_position, boundary=HOLE_ONE_GREEN_BOUNDARY
    )
    player_position = Coordinate(latitude=51.5074, longitude=-0.1220)

    expected_front = _signed_distance(
        player_position, green_position, Coordinate(latitude=51.5100, longitude=-0.1220)
    )
    expected_centre = _signed_distance(player_position, green_position, green_position)
    expected_back = _signed_distance(
        player_position, green_position, Coordinate(latitude=51.5110, longitude=-0.1220)
    )

    result = green_front_centre_back_distances(player_position, green)

    assert isinstance(result, GreenDistances)
    assert result.front_metres == pytest.approx(expected_front, abs=ABS_TOLERANCE_METRES)
    assert result.centre_metres == pytest.approx(expected_centre, abs=ABS_TOLERANCE_METRES)
    assert result.back_metres == pytest.approx(expected_back, abs=ABS_TOLERANCE_METRES)


def test_hazard_carry_distance_matches_hand_computed_value_for_fixture_bunker() -> None:
    """Hand-computed carry distance for hole 2's fixture triangle bunker (issue #7).

    `player_position` and `aim_point` share a longitude exactly equal to the
    triangle's centroid longitude (the mean of its 3 corners' longitudes),
    so the line of play is again a straight line of constant longitude.
    The line crosses the triangle's bottom edge (constant-latitude edge)
    and its right-hand slanted edge; the carry distance is the farther
    (larger signed distance) of the two, hand-derived via `to_local`.
    """
    centroid_longitude = (-0.1175 + -0.1165 + -0.1165) / 3
    hazard = Feature(
        feature_type=FeatureType.BUNKER,
        position=polygon_centroid(HOLE_TWO_BUNKER_BOUNDARY),
        boundary=HOLE_TWO_BUNKER_BOUNDARY,
    )
    player_position = Coordinate(latitude=51.5130, longitude=centroid_longitude)
    aim_point = Coordinate(latitude=51.5160, longitude=centroid_longitude)

    # Crossing of the constant-latitude bottom edge (A-B, latitude 51.5140).
    near_crossing = Coordinate(latitude=51.5140, longitude=centroid_longitude)
    # Crossing of the slanted edge C-A: linearly interpolate latitude at
    # `centroid_longitude` between C(-0.1165, 51.5150) and A(-0.1175, 51.5140).
    t = (centroid_longitude - -0.1165) / (-0.1175 - -0.1165)
    far_crossing_latitude = 51.5150 + t * (51.5140 - 51.5150)
    far_crossing = Coordinate(latitude=far_crossing_latitude, longitude=centroid_longitude)

    expected_carry = max(
        _signed_distance(player_position, aim_point, near_crossing),
        _signed_distance(player_position, aim_point, far_crossing),
    )

    result = hazard_carry_distance(player_position, aim_point, hazard)

    assert result is not None
    assert result == pytest.approx(expected_carry, abs=ABS_TOLERANCE_METRES)


# --- Degenerate: already past the feature -----------------------------------


def test_green_front_metres_is_negative_when_player_already_past_that_edge() -> None:
    """Front distance goes negative once the player has already crossed that edge (issue #7).

    Deviation from a literal "player already past the green" reading of
    issue #7: for `green_front_centre_back_distances`, the aim point is
    always `green.position` -- the boundary's own centroid, which for a
    convex polygon is always strictly interior. `centre_metres` is always
    `|aim - player|` (positive whenever player != aim), and for a convex
    ring the two boundary crossings always bracket that centre distance
    (one nearer, one farther) -- so `back_metres` can never be negative for
    this function, only `front_metres` can, once the player has moved past
    the near edge (e.g. onto the green itself). This test demonstrates that
    achievable case; see
    `test_hazard_carry_distance_is_negative_when_player_already_past_hazard`
    below for a genuinely fully-negative "already past the whole feature"
    case, which requires a free (non-interior-constrained) aim point.
    """
    boundary = (
        Coordinate(latitude=51.5000, longitude=-0.1000),
        Coordinate(latitude=51.5000, longitude=-0.0990),
        Coordinate(latitude=51.5010, longitude=-0.0990),
        Coordinate(latitude=51.5010, longitude=-0.1000),
    )
    green_position = polygon_centroid(boundary)
    green = Feature(feature_type=FeatureType.GREEN, position=green_position, boundary=boundary)
    # Between the centroid latitude (~51.5005) and the back edge (51.5010):
    # already past the front edge, not yet past the back edge.
    player_position = Coordinate(latitude=51.5008, longitude=-0.0995)

    expected_front = _signed_distance(
        player_position, green_position, Coordinate(latitude=51.5010, longitude=-0.0995)
    )
    expected_back = _signed_distance(
        player_position, green_position, Coordinate(latitude=51.5000, longitude=-0.0995)
    )

    result = green_front_centre_back_distances(player_position, green)

    assert result.front_metres < 0
    assert result.back_metres > 0
    assert result.front_metres == pytest.approx(expected_front, abs=ABS_TOLERANCE_METRES)
    assert result.back_metres == pytest.approx(expected_back, abs=ABS_TOLERANCE_METRES)


def test_hazard_carry_distance_is_negative_when_player_already_past_hazard() -> None:
    """`hazard_carry_distance` is negative when the hazard is already behind the player (issue #7).

    Unlike the green query, `hazard_carry_distance`'s `aim_point` is a free
    parameter independent of the hazard's own position, so a hazard can
    genuinely lie entirely on the negative (already-passed) side of the
    line of play -- the fully-negative "already past" scenario issue #7
    describes, made concrete here for the hazard function.
    """
    boundary = (
        Coordinate(latitude=51.5300, longitude=-0.1600),
        Coordinate(latitude=51.5300, longitude=-0.1590),
        Coordinate(latitude=51.5310, longitude=-0.1590),
        Coordinate(latitude=51.5310, longitude=-0.1600),
    )
    hazard = Feature(
        feature_type=FeatureType.BUNKER, position=polygon_centroid(boundary), boundary=boundary
    )
    # Player has already walked past the hazard, still aiming further away from it.
    player_position = Coordinate(latitude=51.5320, longitude=-0.1595)
    aim_point = Coordinate(latitude=51.5330, longitude=-0.1595)

    expected_carry = max(
        _signed_distance(
            player_position, aim_point, Coordinate(latitude=51.5300, longitude=-0.1595)
        ),
        _signed_distance(
            player_position, aim_point, Coordinate(latitude=51.5310, longitude=-0.1595)
        ),
    )

    result = hazard_carry_distance(player_position, aim_point, hazard)

    assert result is not None
    assert result < 0
    assert result == pytest.approx(expected_carry, abs=ABS_TOLERANCE_METRES)


def test_green_front_metres_is_approximately_zero_when_player_is_on_boundary_edge() -> None:
    """Near signed distance is ~0 (not exact-zero) when the player stands on an edge (issue #7).

    `player_position` is the exact midpoint of the square's bottom edge.
    Asserted with `pytest.approx(0.0, ...)` rather than an exact `0.0`
    comparison, since floating-point tangency after a fresh projection is
    not guaranteed bit-exact.
    """
    boundary = (
        Coordinate(latitude=51.6000, longitude=-0.2000),
        Coordinate(latitude=51.6000, longitude=-0.1990),
        Coordinate(latitude=51.6010, longitude=-0.1990),
        Coordinate(latitude=51.6010, longitude=-0.2000),
    )
    green_position = polygon_centroid(boundary)
    green = Feature(feature_type=FeatureType.GREEN, position=green_position, boundary=boundary)
    player_position = Coordinate(latitude=51.6000, longitude=-0.1995)  # midpoint of the bottom edge

    result = green_front_centre_back_distances(player_position, green)

    assert result.front_metres == pytest.approx(0.0, abs=ABS_TOLERANCE_METRES)
    assert result.back_metres > 0


# --- Hazard miss / exactly-one-crossing (tangent) ---------------------------


def test_hazard_carry_distance_returns_none_when_line_of_play_misses_hazard() -> None:
    """`hazard_carry_distance` returns `None` when the aim direction never crosses the hazard
    (issue #7).
    """
    boundary = (
        Coordinate(latitude=51.7000, longitude=-0.3000),
        Coordinate(latitude=51.7000, longitude=-0.2990),
        Coordinate(latitude=51.7010, longitude=-0.2990),
        Coordinate(latitude=51.7010, longitude=-0.3000),
    )
    hazard = Feature(
        feature_type=FeatureType.BUNKER, position=polygon_centroid(boundary), boundary=boundary
    )
    player_position = Coordinate(latitude=51.6900, longitude=-0.2995)
    # Due east of the player, same latitude: this line never reaches the
    # hazard's latitude band (51.7000-51.7010) at all.
    aim_point = Coordinate(latitude=51.6900, longitude=-0.2900)

    result = hazard_carry_distance(player_position, aim_point, hazard)

    assert result is None


def test_hazard_carry_distance_returns_single_value_for_tangent_line_of_play() -> None:
    """`hazard_carry_distance` returns one signed distance for a line that grazes a vertex
    (issue #7).

    Constructed directly in the local-metre frame anchored at
    `player_position` (via `to_coordinate`), then converted to real
    `Coordinate`s, so the tangency is exact rather than approximated: the
    line through `player_position` and `aim_point` passes through corner
    `A` of the square (a supporting line at that vertex) while the other
    three corners lie strictly off it and strictly on one side, so the
    line touches the polygon's boundary at exactly one point.

    This uses `hazard_carry_distance` rather than
    `green_front_centre_back_distances`: the green query's aim point is
    always the green's own (necessarily interior, for a convex boundary)
    centroid, so a line from the player to it can never be tangent -- it
    must always enter the polygon's interior. `hazard_carry_distance`'s
    `aim_point` is a free parameter, so true tangency is only constructible
    there; issue #7 anticipates this ("a single carry distance") as an
    equally valid way to exercise the exactly-one-crossing case.
    """
    player_position = Coordinate(latitude=51.5000, longitude=-0.1000)
    aim_point = to_coordinate(player_position, LocalPoint(x_metres=-10.0, y_metres=10.0))
    corner_a = to_coordinate(player_position, LocalPoint(x_metres=-50.0, y_metres=50.0))
    corner_b = to_coordinate(player_position, LocalPoint(x_metres=-40.0, y_metres=50.0))
    corner_c = to_coordinate(player_position, LocalPoint(x_metres=-40.0, y_metres=60.0))
    corner_d = to_coordinate(player_position, LocalPoint(x_metres=-50.0, y_metres=60.0))
    boundary = (corner_a, corner_b, corner_c, corner_d)
    hazard = Feature(
        feature_type=FeatureType.BUNKER, position=polygon_centroid(boundary), boundary=boundary
    )

    expected_tangent_distance = _signed_distance(player_position, aim_point, corner_a)

    result = hazard_carry_distance(player_position, aim_point, hazard)

    assert result is not None
    assert result == pytest.approx(expected_tangent_distance, abs=ABS_TOLERANCE_METRES)


# --- Invalid input -----------------------------------------------------------


def test_green_front_centre_back_distances_raises_value_error_when_boundary_is_none() -> None:
    """`green_front_centre_back_distances` raises `ValueError` when `green.boundary` is `None`
    (issue #7).
    """
    player_position = Coordinate(latitude=51.4900, longitude=-0.1000)

    with pytest.raises(ValueError):
        green_front_centre_back_distances(player_position, _point_only_feature())


def test_hazard_carry_distance_raises_value_error_when_boundary_is_none() -> None:
    """`hazard_carry_distance` raises `ValueError` when `hazard.boundary is None` (issue #7)."""
    player_position = Coordinate(latitude=51.4900, longitude=-0.1000)
    aim_point = Coordinate(latitude=51.4950, longitude=-0.1000)

    with pytest.raises(ValueError):
        hazard_carry_distance(player_position, aim_point, _point_only_feature())


def test_green_front_centre_back_distances_raises_value_error_when_player_equals_green() -> None:
    """`green_front_centre_back_distances` raises `ValueError` for a degenerate direction
    (issue #7).
    """
    boundary = (
        Coordinate(latitude=51.5400, longitude=-0.1700),
        Coordinate(latitude=51.5400, longitude=-0.1690),
        Coordinate(latitude=51.5410, longitude=-0.1690),
        Coordinate(latitude=51.5410, longitude=-0.1700),
    )
    green_position = polygon_centroid(boundary)
    green = Feature(feature_type=FeatureType.GREEN, position=green_position, boundary=boundary)

    with pytest.raises(ValueError):
        green_front_centre_back_distances(green_position, green)


def test_hazard_carry_distance_raises_value_error_when_player_equals_aim_point() -> None:
    """`hazard_carry_distance` raises `ValueError` for a degenerate direction (issue #7)."""
    boundary = (
        Coordinate(latitude=51.5400, longitude=-0.1700),
        Coordinate(latitude=51.5400, longitude=-0.1690),
        Coordinate(latitude=51.5410, longitude=-0.1690),
        Coordinate(latitude=51.5410, longitude=-0.1700),
    )
    hazard = Feature(
        feature_type=FeatureType.BUNKER, position=polygon_centroid(boundary), boundary=boundary
    )
    player_position = Coordinate(latitude=51.5300, longitude=-0.1700)

    with pytest.raises(ValueError):
        hazard_carry_distance(player_position, player_position, hazard)


# --- Frame-mixing regression -------------------------------------------------


def test_green_front_centre_back_distances_is_independent_of_boundary_vertex_rotation() -> None:
    """Regression test for coordinate-frame consistency across a rotated boundary tuple (issue #7).

    This is the key regression test for the M2.5 coordinate-frame-
    consistency requirement: `feature` and `rotated_feature` describe the
    exact same polygon ring, just starting at a different vertex (a
    rotation of the same 4-tuple), each with its own correspondingly
    recomputed `position`. Querying the same `player_position` against
    both must give the same front/centre/back distances.

    A naive implementation that reused a `boundary[0]`-anchored local
    projection internally (e.g. mixing in
    `caddai.course.models._local_polygon`'s per-feature, ad hoc origin)
    instead of re-projecting fresh from `player_position` for every query,
    would be sensitive to which vertex happens to be `boundary[0]` -- and
    would fail this test, since `feature.boundary[0]` and
    `rotated_feature.boundary[0]` differ.
    """
    corner_a = Coordinate(latitude=51.5200, longitude=-0.1500)
    corner_b = Coordinate(latitude=51.5200, longitude=-0.1490)
    corner_c = Coordinate(latitude=51.5210, longitude=-0.1490)
    corner_d = Coordinate(latitude=51.5210, longitude=-0.1500)
    boundary = (corner_a, corner_b, corner_c, corner_d)
    rotated_boundary = (corner_c, corner_d, corner_a, corner_b)

    feature = Feature(
        feature_type=FeatureType.GREEN, position=polygon_centroid(boundary), boundary=boundary
    )
    rotated_feature = Feature(
        feature_type=FeatureType.GREEN,
        position=polygon_centroid(rotated_boundary),
        boundary=rotated_boundary,
    )
    player_position = Coordinate(latitude=51.5180, longitude=-0.1495)

    result = green_front_centre_back_distances(player_position, feature)
    rotated_result = green_front_centre_back_distances(player_position, rotated_feature)

    assert result.front_metres == pytest.approx(
        rotated_result.front_metres, abs=ABS_TOLERANCE_METRES
    )
    assert result.centre_metres == pytest.approx(
        rotated_result.centre_metres, abs=ABS_TOLERANCE_METRES
    )
    assert result.back_metres == pytest.approx(rotated_result.back_metres, abs=ABS_TOLERANCE_METRES)


# --- Fixture geometry sanity check -------------------------------------------


def test_fixture_green_and_bunker_boundaries_are_convex() -> None:
    """Hole 1's green and hole 2's bunker fixture polygons are convex (issue #7).

    The nearest/farthest-crossing simplification in `distance.py` (front =
    smallest signed crossing, back/carry = largest signed crossing) only
    agrees with a full hand computation when the polygon is convex -- a
    concave ring can produce more than 2 crossings, for which "nearest"/
    "farthest" is an explicit, documented scope limitation rather than a
    complete geometric answer. This test guards the assumption the
    hand-computed tests above rely on.
    """
    green_polygon = Polygon(
        [(coordinate.longitude, coordinate.latitude) for coordinate in HOLE_ONE_GREEN_BOUNDARY]
    )
    bunker_polygon = Polygon(
        [(coordinate.longitude, coordinate.latitude) for coordinate in HOLE_TWO_BUNKER_BOUNDARY]
    )

    assert green_polygon.equals(green_polygon.convex_hull)
    assert bunker_polygon.equals(bunker_polygon.convex_hull)
