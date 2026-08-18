"""GPS coordinate domain model.

See docs/course-engine.md for the planned design of this subsystem.
"""

from pydantic import BaseModel, Field


class Coordinate(BaseModel):
    """A geographic coordinate expressed in decimal degrees, WGS 84 convention.

    `latitude` is in the inclusive range [-90, 90] degrees (positive north).
    `longitude` is in the inclusive range [-180, 180] degrees (positive east).
    """

    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
