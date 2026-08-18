"""GPS subsystem: coordinate representation and great-circle calculations.

See docs/course-engine.md for the full planned design.
"""

from caddai.gps.distance import haversine_distance_metres, initial_bearing_degrees
from caddai.gps.models import Coordinate

__all__ = [
    "Coordinate",
    "haversine_distance_metres",
    "initial_bearing_degrees",
]
