"""Point-to-feature distance queries against course boundary geometry.

See docs/course-engine.md and
[ADR 0004](../../../docs/adr/0004-distance-query-local-frame.md) for the
full design. **Frame-consistency invariant**: every function below
re-projects `player_position` (the shared local-metre-frame origin), the
aim point, and the feature's `boundary` together, fresh, in one place, per
call, via `caddai.gps.projection.to_local`. This frame must never be mixed
with `caddai.course.models._local_polygon`'s per-feature, ad hoc origin
(`boundary[0]`) — that origin exists only for a feature's own, single-
feature centroid/validity computation and has no relationship to a
player's position or an aim direction.
"""

import math

from pydantic import BaseModel
from shapely import set_precision
from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    Point,
    Polygon,
)
from shapely.geometry.base import BaseGeometry

from caddai.course.models import Feature
from caddai.gps.models import Coordinate
from caddai.gps.projection import to_local

# Safety multiple applied to the farthest boundary vertex distance when
# sizing the query line, so it fully crosses the polygon in both directions.
_LINE_LENGTH_SAFETY_MULTIPLE = 3

# Precision grid (metres) the query line and boundary polygon are snapped to
# before intersecting. A boundary vertex reconstructed through a
# to_coordinate/to_local round trip can miss an exact geometric tangency by a
# sub-nanometre amount, which Shapely's exact floating-point intersection
# predicate would otherwise treat as no intersection at all. 1 micrometre is
# far finer than this module's 0.01 m (ADR 0002/0003) and its callers' 0.05 m
# test tolerance, so it has no observable effect on any reported distance.
_INTERSECTION_PRECISION_METRES = 1e-6


class GreenDistances(BaseModel):
    """Signed distances, in metres, from a player to a green's front/centre/back.

    All three are measured along the player->green-centroid line of play; a
    negative value means the player has already passed that point. "Centre"
    is the green polygon's centroid (per ADR 0003), not a pin/flag location.
    """

    front_metres: float
    centre_metres: float
    back_metres: float


def _flatten_intersection_coordinates(geometry: BaseGeometry) -> list[tuple[float, float]]:
    """Flatten any Shapely intersection result type into its component (x, y) coordinates.

    Handles `Point`, `MultiPoint`, `LineString`, `MultiLineString`, and
    `GeometryCollection` (a tangent or edge-overlapping intersection can
    produce any of these), plus an empty result.
    """
    if geometry.is_empty:
        return []
    if isinstance(geometry, Point):
        return [(geometry.x, geometry.y)]
    if isinstance(geometry, LineString):
        return list(geometry.coords)
    if isinstance(geometry, MultiPoint | MultiLineString | GeometryCollection):
        coordinates: list[tuple[float, float]] = []
        for component in geometry.geoms:
            coordinates.extend(_flatten_intersection_coordinates(component))
        return coordinates
    raise TypeError(f"unexpected intersection geometry type: {type(geometry)!r}")


def _signed_distance(
    player_position: Coordinate, aim_point: Coordinate, point: Coordinate
) -> float:
    """Signed distance, in metres, of `point` along the player->aim line of play.

    Projects `player_position` (the shared local-metre-frame origin),
    `aim_point`, and `point` together, fresh, via `to_local` -- see the
    module docstring's frame-consistency invariant. The result is the dot
    product of `point`'s local offset with the unit player->aim direction
    vector: positive ahead of the player in the aim direction, negative
    behind.

    Raises `ValueError` if `player_position == aim_point` (undefined
    direction).
    """
    if player_position == aim_point:
        raise ValueError("player_position and aim_point must not be the same coordinate")

    aim_local = to_local(player_position, aim_point)
    point_local = to_local(player_position, point)

    norm = math.hypot(aim_local.x_metres, aim_local.y_metres)
    unit_x = aim_local.x_metres / norm
    unit_y = aim_local.y_metres / norm

    return point_local.x_metres * unit_x + point_local.y_metres * unit_y


def _signed_line_boundary_crossings(
    player_position: Coordinate, aim_point: Coordinate, boundary: tuple[Coordinate, ...]
) -> list[float]:
    """Signed distances, in metres, of `boundary`'s crossings along the player->aim line.

    Projects `player_position` (the shared local-metre-frame origin),
    `aim_point`, and every `boundary` vertex together, fresh, in this one
    call, via `to_local` -- see the module docstring's frame-consistency
    invariant. Builds a line through the local player point in both
    directions (long enough to fully cross the polygon regardless of which
    side of the player it lies on), intersects it with the boundary
    polygon's exterior, and returns the sorted (ascending) signed distances
    of every resulting crossing point, measured as the dot product of each
    crossing's local offset with the unit player->aim direction vector.

    This only fully agrees with a hand computation for a convex `boundary`;
    a concave ring can yield more than two crossings, for which "nearest"/
    "farthest" (used by the public functions below) is a documented scope
    limitation, not a complete geometric answer.

    Raises `ValueError` if `player_position == aim_point` (undefined
    direction).
    """
    if player_position == aim_point:
        raise ValueError("player_position and aim_point must not be the same coordinate")

    aim_local = to_local(player_position, aim_point)
    boundary_local = [to_local(player_position, vertex) for vertex in boundary]

    aim_distance = math.hypot(aim_local.x_metres, aim_local.y_metres)
    unit_x = aim_local.x_metres / aim_distance
    unit_y = aim_local.y_metres / aim_distance

    max_vertex_distance = max(
        math.hypot(vertex.x_metres, vertex.y_metres) for vertex in boundary_local
    )
    line_length = (max_vertex_distance * _LINE_LENGTH_SAFETY_MULTIPLE) + aim_distance

    line = LineString(
        [
            (-unit_x * line_length, -unit_y * line_length),
            (unit_x * line_length, unit_y * line_length),
        ]
    )
    polygon = Polygon([(vertex.x_metres, vertex.y_metres) for vertex in boundary_local])

    precise_line = set_precision(line, _INTERSECTION_PRECISION_METRES)
    precise_exterior = set_precision(polygon.exterior, _INTERSECTION_PRECISION_METRES)
    intersection = precise_exterior.intersection(precise_line)
    crossing_points = _flatten_intersection_coordinates(intersection)

    signed_distances = [x * unit_x + y * unit_y for x, y in crossing_points]
    return sorted(signed_distances)


def green_front_centre_back_distances(
    player_position: Coordinate, green: Feature
) -> GreenDistances:
    """Signed distances, in metres, from `player_position` to `green`'s front/centre/back.

    The aim point is `green.position` -- the green polygon's own centroid
    (per ADR 0003), **not** a pin/flag location (no such concept exists
    yet). `centre_metres` is the signed distance to that centroid, along
    the same player->centroid line of play used for `front_metres`/
    `back_metres`, so all three numbers are internally consistent within
    one query. `front_metres`/`back_metres` are the nearest/farthest of the
    line's crossings of `green.boundary`; for a tangent line these are
    equal, and this is only a complete answer for a convex `boundary` (see
    `_signed_line_boundary_crossings`).

    Raises `ValueError` if `green.boundary is None`, if
    `player_position == green.position` (undefined direction), or -- as an
    internal-consistency check that should be geometrically impossible for
    valid data, since the aim point is the polygon's own interior centroid
    -- if no boundary crossing is found at all.
    """
    if green.boundary is None:
        raise ValueError("green.boundary must not be None to compute front/centre/back distances")

    aim_point = green.position
    crossings = _signed_line_boundary_crossings(player_position, aim_point, green.boundary)

    if not crossings:
        raise ValueError(
            "no boundary crossing found between player_position and the green's centroid; "
            "this should be geometrically impossible for a valid convex green boundary"
        )

    centre_metres = _signed_distance(player_position, aim_point, aim_point)

    return GreenDistances(
        front_metres=crossings[0], centre_metres=centre_metres, back_metres=crossings[-1]
    )


def hazard_carry_distance(
    player_position: Coordinate, aim_point: Coordinate, hazard: Feature
) -> float | None:
    """Signed carry distance, in metres, to clear `hazard` along the player->aim line of play.

    The carry distance is the farthest of the line's crossings of
    `hazard.boundary` -- the point beyond which the hazard has been fully
    carried. Returns `None` if the line of play never crosses the hazard at
    all (it is not in play for this line). For a tangent line, the single
    crossing found is returned. This is only a complete answer for a convex
    `boundary` (see `_signed_line_boundary_crossings`).

    Raises `ValueError` if `hazard.boundary is None`, or if
    `player_position == aim_point` (undefined direction).
    """
    if hazard.boundary is None:
        raise ValueError("hazard.boundary must not be None to compute a carry distance")

    crossings = _signed_line_boundary_crossings(player_position, aim_point, hazard.boundary)

    if not crossings:
        return None

    return crossings[-1]
