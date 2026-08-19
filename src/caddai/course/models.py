"""Course, hole, and feature domain models.

See docs/course-engine.md for the full planned design of this subsystem.
A `Feature` always has a representative point `position`, and may
additionally carry a `boundary`: a single exterior polygon ring (e.g. for a
green or a bunker), see [ADR 0003](../../../docs/adr/0003-course-boundary-geometry.md).
Interior rings (holes) are not supported. When `boundary` is present,
`position` is enforced to equal the polygon's centroid, computed via
`polygon_centroid`; this is a convenient representative point only — it is
not guaranteed to lie inside a concave/non-convex polygon, and it is not a
substitute for front/centre/back distance semantics, which is M2.5's job.
"""

import math
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, model_validator
from shapely.geometry import Polygon

from caddai.gps.models import Coordinate
from caddai.gps.projection import LocalPoint, to_coordinate, to_local


class FeatureType(StrEnum):
    """The kind of course feature a `Feature` represents."""

    TEE = "tee"
    FAIRWAY = "fairway"
    GREEN = "green"
    BUNKER = "bunker"
    WATER = "water"
    OUT_OF_BOUNDS = "out_of_bounds"
    LANDING_AREA = "landing_area"


def _local_polygon(boundary: tuple[Coordinate, ...]) -> tuple[Polygon, Coordinate]:
    """Project `boundary` to a local-metre `Polygon`, using `boundary[0]` as origin.

    Returns the projected `Polygon` alongside the `origin` used, so callers
    that need both a geometric check and a centroid can project once and
    reuse the result. This local-metre representation is transient and used
    only within this module — it is not persisted or exposed anywhere.
    """
    origin = boundary[0]
    local_points = [to_local(origin, vertex) for vertex in boundary]
    polygon = Polygon([(point.x_metres, point.y_metres) for point in local_points])
    return polygon, origin


def polygon_centroid(boundary: tuple[Coordinate, ...]) -> Coordinate:
    """Compute the centroid of a polygon boundary ring, as a `Coordinate`.

    `boundary`'s vertices are projected to local metres via
    `caddai.gps.projection.to_local`, using `boundary[0]` as an ad hoc,
    transient local-projection origin; a `shapely.geometry.Polygon` is
    built from those local points; its centroid is unprojected back to a
    `Coordinate` via `caddai.gps.projection.to_coordinate`, relative to the
    same origin.

    This local-metre representation is transient and used only for this
    computation — it is not persisted or exposed anywhere. A shared
    course-/hole-level local-projection origin is intentionally deferred to
    M2.5, which knows what shared frame its distance queries need.
    """
    polygon, origin = _local_polygon(boundary)
    centroid = polygon.centroid
    return to_coordinate(origin, LocalPoint(x_metres=centroid.x, y_metres=centroid.y))


class Feature(BaseModel):
    """A single course feature, with a representative point `position`.

    `boundary`, if present, is a single exterior polygon ring (distinct
    vertices, no duplicated closing vertex) — see the module docstring for
    scope and the `position`-as-centroid invariant, which is enforced by
    this model's own validator regardless of how the `Feature` is
    constructed.
    """

    feature_type: FeatureType
    position: Coordinate
    boundary: tuple[Coordinate, ...] | None = Field(default=None, min_length=3)

    @model_validator(mode="after")
    def _validate_boundary(self) -> Self:
        """Reject an invalid/degenerate `boundary`, or a `position` that isn't its centroid."""
        if self.boundary is None:
            return self

        polygon, origin = _local_polygon(self.boundary)

        if not polygon.is_valid or polygon.area <= 0:
            raise ValueError(
                "Feature.boundary must be a simple (non-self-intersecting), "
                "non-degenerate polygon ring with positive area"
            )

        centroid = polygon.centroid
        expected_centroid = to_coordinate(
            origin, LocalPoint(x_metres=centroid.x, y_metres=centroid.y)
        )
        position_local = to_local(origin, self.position)
        expected_centroid_local = to_local(origin, expected_centroid)
        mismatch_metres = math.hypot(
            position_local.x_metres - expected_centroid_local.x_metres,
            position_local.y_metres - expected_centroid_local.y_metres,
        )
        if mismatch_metres > 0.01:
            raise ValueError(
                f"Feature.position must equal Feature.boundary's centroid, but is "
                f"{mismatch_metres:.4f} metres away from it"
            )

        return self


class Hole(BaseModel):
    """A golf hole: its number, par, and ordered play-order features."""

    number: int = Field(gt=0)
    par: int = Field(gt=0)
    features: list[Feature] = Field(min_length=1)


class Course(BaseModel):
    """A golf course composed of holes."""

    name: str = Field(min_length=1)
    holes: list[Hole] = Field(min_length=1)
