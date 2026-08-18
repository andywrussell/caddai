"""Course-local planar coordinate projection.

See docs/course-engine.md for the planned design of this subsystem, and
docs/adr/0002-gps-local-projection-without-shapely.md for why this module
uses plain trigonometry rather than Shapely.
"""

import math

from pydantic import BaseModel

from caddai.gps.distance import EARTH_RADIUS_METRES
from caddai.gps.models import Coordinate


class LocalPoint(BaseModel):
    """A planar point in metres, relative to a fixed origin `Coordinate`.

    `x_metres` is the eastward offset from the origin; `y_metres` is the
    northward offset from the origin.
    """

    x_metres: float
    y_metres: float


def _latitude_scale(origin_latitude: float) -> float:
    """Return `cos(radians(origin_latitude))`, guarding against a polar origin.

    Raises `ValueError` if `origin_latitude` is exactly ±90 degrees, where
    the small-area tangent-plane approximation is undefined (longitude
    lines converge to a point at the pole).
    """
    if abs(origin_latitude) == 90.0:
        raise ValueError(
            "gps.projection is undefined for a polar origin (latitude "
            "\u00b190\u00b0): the small-area tangent-plane approximation breaks "
            "down at the poles."
        )
    return math.cos(math.radians(origin_latitude))


def to_local(origin: Coordinate, point: Coordinate) -> LocalPoint:
    """Project `point` onto the local tangent plane centred on `origin`.

    This is a small-area equirectangular/tangent-plane approximation, valid
    only within roughly a 2 km radius of `origin` -- it is not a
    general-purpose geodesic projection. The origin's latitude scale factor
    (`cos(radians(origin.latitude))`) is fixed once from `origin` alone, so
    round-trips through `to_coordinate` are exact algebraic inverses and
    recover the original coordinate to within 0.01 metres (1 cm) within that
    range.

    Raises `ValueError` if `origin.latitude` is exactly ±90 degrees (a polar
    origin), for which this projection is undefined.
    """
    latitude_scale = _latitude_scale(origin.latitude)
    x_metres = (
        EARTH_RADIUS_METRES * math.radians(point.longitude - origin.longitude) * latitude_scale
    )
    y_metres = EARTH_RADIUS_METRES * math.radians(point.latitude - origin.latitude)

    return LocalPoint(x_metres=x_metres, y_metres=y_metres)


def to_coordinate(origin: Coordinate, point: LocalPoint) -> Coordinate:
    """Unproject a local planar `point` back to a `Coordinate` relative to `origin`.

    Algebraic inverse of `to_local`, using the same fixed origin latitude
    scale factor. This is a small-area approximation, valid only within
    roughly a 2 km radius of `origin`, and recovers coordinates round-tripped
    through `to_local` to within 0.01 metres (1 cm) within that range.

    Raises `ValueError` if `origin.latitude` is exactly ±90 degrees (a polar
    origin), for which this projection is undefined.
    """
    latitude_scale = _latitude_scale(origin.latitude)
    latitude = origin.latitude + math.degrees(point.y_metres / EARTH_RADIUS_METRES)
    longitude = origin.longitude + math.degrees(
        point.x_metres / (EARTH_RADIUS_METRES * latitude_scale)
    )

    return Coordinate(latitude=latitude, longitude=longitude)
