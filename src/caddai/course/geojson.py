"""Parsing of local GeoJSON course fixtures into `caddai.course.models` objects.

See docs/course-engine.md for the documented GeoJSON schema. Coordinate
extraction is plain dict access, not `shapely.geometry.shape` — no geometric
operation is performed here, matching the precedent of
docs/adr/0002-gps-local-projection-without-shapely.md.
"""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from caddai.course.models import Course, Feature, FeatureType, Hole
from caddai.gps.models import Coordinate


class _HoleMetadata(BaseModel):
    """Top-level per-hole metadata: hole number and par (single source of truth)."""

    number: int = Field(gt=0)
    par: int = Field(gt=0)


class _CourseProperties(BaseModel):
    """Top-level `FeatureCollection.properties`: course name and per-hole metadata."""

    name: str = Field(min_length=1)
    holes: list[_HoleMetadata] = Field(min_length=1)


class _FeatureProperties(BaseModel):
    """Per-feature `Feature.properties`: which hole it belongs to and its type."""

    hole: int
    feature_type: FeatureType


def load_course(data: dict[str, object]) -> Course:
    """Parse an already-decoded GeoJSON `FeatureCollection` dict into a `Course`.

    Raises `ValueError` for structural problems (missing top-level
    `properties`, wrong `type` discriminators, unsupported `geometry.type`, or
    a feature referencing a hole number absent from the top-level `holes`
    metadata), and `pydantic.ValidationError` for field-level problems (e.g.
    an unrecognized `feature_type`).
    """
    if data.get("type") != "FeatureCollection":
        raise ValueError(
            f"expected top-level 'type' to be 'FeatureCollection', got {data.get('type')!r}"
        )

    raw_properties = data.get("properties")
    if raw_properties is None:
        raise ValueError("FeatureCollection is missing the top-level 'properties' block")

    course_properties = _CourseProperties.model_validate(raw_properties)

    seen_hole_numbers: set[int] = set()
    for hole_metadata in course_properties.holes:
        if hole_metadata.number in seen_hole_numbers:
            raise ValueError(
                f"duplicate hole number {hole_metadata.number} in top-level "
                "'properties.holes' metadata"
            )
        seen_hole_numbers.add(hole_metadata.number)

    hole_metadata_by_number = {hole.number: hole for hole in course_properties.holes}

    raw_features = data.get("features")
    if not isinstance(raw_features, list):
        raise ValueError("FeatureCollection is missing a 'features' list")

    features_by_hole: dict[int, list[Feature]] = {number: [] for number in hole_metadata_by_number}
    for index, raw_feature in enumerate(raw_features):
        feature, hole_number = _parse_feature(raw_feature, index)
        if hole_number not in hole_metadata_by_number:
            raise ValueError(
                f"feature at index {index} references hole {hole_number}, which is not "
                "declared in the top-level 'properties.holes' metadata"
            )
        features_by_hole[hole_number].append(feature)

    holes = [
        Hole(
            number=hole_metadata.number,
            par=hole_metadata.par,
            features=features_by_hole[hole_metadata.number],
        )
        for hole_metadata in course_properties.holes
    ]

    return Course(name=course_properties.name, holes=holes)


def load_course_from_file(path: Path) -> Course:
    """Read and JSON-decode a GeoJSON course fixture file, then parse it via `load_course`."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return load_course(data)


def _parse_feature(raw_feature: object, index: int) -> tuple[Feature, int]:
    """Parse a single GeoJSON `Feature` entry into a `Feature` and its declared hole number."""
    if not isinstance(raw_feature, dict):
        raise ValueError(f"feature at index {index} is not a JSON object")

    if raw_feature.get("type") != "Feature":
        raise ValueError(
            f"feature at index {index} has 'type' {raw_feature.get('type')!r}, expected 'Feature'"
        )

    geometry: Any = raw_feature.get("geometry")
    if not isinstance(geometry, dict):
        raise ValueError(f"feature at index {index} is missing a 'geometry' object")

    if geometry.get("type") != "Point":
        raise ValueError(
            f"feature at index {index} has unsupported geometry.type "
            f"{geometry.get('type')!r}; only 'Point' is supported"
        )

    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        raise ValueError(f"feature at index {index} has invalid Point 'coordinates'")

    position = Coordinate(latitude=coordinates[1], longitude=coordinates[0])

    properties = _FeatureProperties.model_validate(raw_feature.get("properties"))

    return Feature(feature_type=properties.feature_type, position=position), properties.hole
