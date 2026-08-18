"""Great-circle distance and bearing calculations between GPS coordinates.

See docs/course-engine.md for the planned design of this subsystem.
"""

import math

from caddai.gps.models import Coordinate

# Mean Earth radius in metres (IUGG mean radius), used as the sphere radius
# for the haversine approximation. This treats the Earth as a perfect sphere,
# so results differ slightly (well under 0.5%) from ellipsoidal models.
EARTH_RADIUS_METRES: float = 6_371_000.0


def haversine_distance_metres(origin: Coordinate, destination: Coordinate) -> float:
    """Great-circle distance in metres between two coordinates.

    Uses the haversine formula with a mean Earth radius of 6,371,000 metres,
    treating the Earth as a sphere rather than an ellipsoid.
    """
    origin_latitude_radians = math.radians(origin.latitude)
    destination_latitude_radians = math.radians(destination.latitude)
    delta_latitude_radians = math.radians(destination.latitude - origin.latitude)
    delta_longitude_radians = math.radians(destination.longitude - origin.longitude)

    a = (
        math.sin(delta_latitude_radians / 2.0) ** 2
        + math.cos(origin_latitude_radians)
        * math.cos(destination_latitude_radians)
        * math.sin(delta_longitude_radians / 2.0) ** 2
    )
    # atan2 avoids a math domain error from asin if rounding pushes a above 1.0.
    central_angle_radians = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return EARTH_RADIUS_METRES * central_angle_radians


def initial_bearing_degrees(origin: Coordinate, destination: Coordinate) -> float:
    """Initial (forward) great-circle bearing in degrees from origin to destination.

    Clockwise from true north, normalized to the half-open range [0, 360).
    Identical origin/destination coordinates return a bearing of 0.0 degrees.
    """
    origin_latitude_radians = math.radians(origin.latitude)
    destination_latitude_radians = math.radians(destination.latitude)
    delta_longitude_radians = math.radians(destination.longitude - origin.longitude)

    bearing_numerator = math.sin(delta_longitude_radians) * math.cos(destination_latitude_radians)
    bearing_denominator = math.cos(origin_latitude_radians) * math.sin(
        destination_latitude_radians
    ) - (
        math.sin(origin_latitude_radians)
        * math.cos(destination_latitude_radians)
        * math.cos(delta_longitude_radians)
    )
    bearing_radians = math.atan2(bearing_numerator, bearing_denominator)

    return math.degrees(bearing_radians) % 360.0
