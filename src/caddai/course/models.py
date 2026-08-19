"""Course, hole, and feature domain models.

See docs/course-engine.md for the full planned design of this subsystem.
Feature geometry here is point-based only (a single `Coordinate` position);
polygon/boundary geometry backed by Shapely is deferred to a later,
separately-scoped task per
docs/adr/0002-gps-local-projection-without-shapely.md.
"""

from enum import StrEnum

from pydantic import BaseModel, Field

from caddai.gps.models import Coordinate


class FeatureType(StrEnum):
    """The kind of course feature a `Feature` represents."""

    TEE = "tee"
    FAIRWAY = "fairway"
    GREEN = "green"
    BUNKER = "bunker"
    WATER = "water"
    OUT_OF_BOUNDS = "out_of_bounds"
    LANDING_AREA = "landing_area"


class Feature(BaseModel):
    """A single course feature at a point position.

    Represented as a point (`position`) for now; polygon/boundary geometry
    is deferred, see the module docstring.
    """

    feature_type: FeatureType
    position: Coordinate


class Hole(BaseModel):
    """A golf hole: its number, par, and ordered play-order features."""

    number: int = Field(gt=0)
    par: int = Field(gt=0)
    features: list[Feature] = Field(min_length=1)


class Course(BaseModel):
    """A golf course composed of holes."""

    name: str = Field(min_length=1)
    holes: list[Hole] = Field(min_length=1)
