"""Tests for the M2.4 GeoJSON course loader in ``caddai.course.geojson``.

See GitHub issue #6 ("M2.4 — Local GeoJSON course fixture parsing") for the
acceptance criteria these tests are derived from: a ``caddai``-specific
GeoJSON ``FeatureCollection`` (top-level ``properties`` with ``name``/
``holes`` metadata, per-feature ``properties`` with ``hole``/
``feature_type``, ``geometry.coordinates`` in ``[longitude, latitude]``
order) must parse into ``Course``/``Hole``/``Feature`` domain models, and
malformed input must raise a clear error rather than being silently
accepted.

These tests assume the loader (not yet implemented at the time this file
was written — see the plan) exposes:

- ``load_course(data: dict[str, object]) -> Course`` — parses an
  already-decoded GeoJSON ``FeatureCollection`` dict.
- ``load_course_from_file(path: Path) -> Course`` — reads and JSON-decodes
  a GeoJSON file, then delegates to ``load_course``.

Fixture: ``tests/fixtures/sample_course.geojson`` is a 2-hole course
("Fixture Links") near central London. Hole 1 is a par 4 with tee/fairway/
green point features; hole 2 is a par 3 with the same three feature types.
Coordinates are distinct, plausible lat/lon values chosen so a
``[longitude, latitude]`` vs ``[latitude, longitude]`` ordering regression
would be caught by the exact-value assertions below (hole 1's tee sits at
latitude 51.5074, longitude -0.1278 — swapped, that longitude would fail
``Coordinate``'s ``[-180, 180]`` range check, but a swap between two
in-range values elsewhere would not raise, hence asserting exact values).

See GitHub issue #22 ("M2.4.5 — Polygon/boundary course geometry and
GeoJSON Polygon support") for the additional acceptance criteria covered
here: ``geometry.type == "Polygon"`` parses into a `Feature.boundary` (with
the duplicated closing vertex dropped) and a centroid `position`; a ring
that isn't closed, has fewer than 4 positions, has zero rings, or has more
than one ring (an interior ring/hole) is rejected; other unsupported
``geometry.type`` values (e.g. ``"LineString"``) are still rejected exactly
as before. The fixture additionally declares a green polygon on hole 1 and
a bunker polygon on hole 2, appended after each hole's existing point
features.
"""

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from caddai.course.geojson import load_course, load_course_from_file
from caddai.course.models import FeatureType
from caddai.gps.models import Coordinate

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_course.geojson"


def _minimal_valid_data() -> dict[str, Any]:
    """A minimal valid single-hole, single-feature FeatureCollection, for mutation in tests."""
    return {
        "type": "FeatureCollection",
        "properties": {
            "name": "Minimal Course",
            "holes": [{"number": 1, "par": 4}],
        },
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-0.1278, 51.5074]},
                "properties": {"hole": 1, "feature_type": "tee"},
            }
        ],
    }


# --- Valid fixture parsing -------------------------------------------------


def test_fixture_course_has_expected_name_and_hole_numbers_and_pars() -> None:
    """The fixture parses into a 2-hole course with the documented name, numbers, and par."""
    course = load_course_from_file(FIXTURE_PATH)

    assert course.name == "Fixture Links"
    assert [hole.number for hole in course.holes] == [1, 2]
    assert [hole.par for hole in course.holes] == [4, 3]


def test_fixture_course_holes_have_expected_feature_counts_and_types() -> None:
    """Each fixture hole has its tee/fairway/green points plus one polygon feature (issue #22)."""
    course = load_course_from_file(FIXTURE_PATH)

    hole_one, hole_two = course.holes

    assert len(hole_one.features) == 4
    assert [feature.feature_type for feature in hole_one.features] == [
        FeatureType.TEE,
        FeatureType.FAIRWAY,
        FeatureType.GREEN,
        FeatureType.GREEN,
    ]
    assert len(hole_two.features) == 4
    assert [feature.feature_type for feature in hole_two.features] == [
        FeatureType.TEE,
        FeatureType.FAIRWAY,
        FeatureType.GREEN,
        FeatureType.BUNKER,
    ]


def test_fixture_hole_one_tee_coordinate_matches_expected_lat_lon() -> None:
    """Hole 1's tee position matches the fixture's [longitude, latitude] coordinates exactly.

    This is the regression test for a `[lon, lat]` vs `[lat, lon]` swap: the
    fixture declares `"coordinates": [-0.1278, 51.5074]`, which must map to
    `Coordinate(latitude=51.5074, longitude=-0.1278)`, not the reverse.
    """
    course = load_course_from_file(FIXTURE_PATH)

    hole_one = course.holes[0]
    tee = hole_one.features[0]

    assert tee.feature_type == FeatureType.TEE
    assert tee.position.latitude == pytest.approx(51.5074)
    assert tee.position.longitude == pytest.approx(-0.1278)


def test_fixture_hole_two_green_coordinate_matches_expected_lat_lon() -> None:
    """Hole 2's green position matches the fixture's [longitude, latitude] coordinates exactly."""
    course = load_course_from_file(FIXTURE_PATH)

    hole_two = course.holes[1]
    green = hole_two.features[2]

    assert green.feature_type == FeatureType.GREEN
    assert green.position.latitude == pytest.approx(51.5150)
    assert green.position.longitude == pytest.approx(-0.1160)


def test_load_course_accepts_already_decoded_dict_matching_fixture() -> None:
    """`load_course` accepts a plain dict (not just a file path) with equivalent content."""
    course = load_course(_minimal_valid_data())

    assert course.name == "Minimal Course"
    assert len(course.holes) == 1
    assert course.holes[0].number == 1
    assert course.holes[0].par == 4


# --- Malformed input ---------------------------------------------------


def test_load_course_rejects_feature_missing_hole_property() -> None:
    """A feature without `properties.hole` cannot be assigned to any hole."""
    data = _minimal_valid_data()
    del data["features"][0]["properties"]["hole"]

    # The implementation may raise a plain ValueError (missing key) or a
    # pydantic ValidationError (if `hole` is validated via an intermediate
    # properties model) — either is an acceptable, non-silent rejection.
    with pytest.raises((ValueError, ValidationError)):
        load_course(data)


def test_load_course_rejects_unrecognized_feature_type() -> None:
    """A feature with a `feature_type` string outside `FeatureType`'s values is rejected."""
    data = _minimal_valid_data()
    data["features"][0]["properties"]["feature_type"] = "clubhouse"

    with pytest.raises(ValidationError):
        load_course(data)


def test_load_course_rejects_feature_referencing_undeclared_hole() -> None:
    """A feature whose `hole` isn't present in the top-level `holes` metadata is rejected."""
    data = _minimal_valid_data()
    data["features"][0]["properties"]["hole"] = 2  # only hole 1 is declared in `properties.holes`

    with pytest.raises(ValueError):
        load_course(data)


def test_load_course_rejects_feature_collection_missing_top_level_properties() -> None:
    """A `FeatureCollection` with no top-level `properties` has no course name/hole metadata."""
    data = _minimal_valid_data()
    del data["properties"]

    with pytest.raises(ValueError):
        load_course(data)


def test_load_course_rejects_linestring_geometry() -> None:
    """A feature with an unsupported `geometry.type` (e.g. `"LineString"`) must be
    rejected (issue #22).

    `"Polygon"` is now a supported geometry type (see the Polygon tests
    below) — this regression test picks a different, still-unsupported
    type to keep equivalent "unsupported geometry.type is rejected" coverage.
    """
    data = _minimal_valid_data()
    data["features"][0]["geometry"] = {
        "type": "LineString",
        "coordinates": [[-0.1278, 51.5074], [-0.1250, 51.5090]],
    }

    with pytest.raises(ValueError):
        load_course(data)


def test_load_course_rejects_self_intersecting_polygon_through_full_loader() -> None:
    """A self-intersecting (bowtie) Polygon ring is rejected end-to-end through
    `load_course` (issue #22).

    `_parse_feature` computes `position = polygon_centroid(boundary)` before
    constructing `Feature(...)`, so this exercises the path where a
    degenerate ring's centroid is computed on unvalidated geometry before
    `Feature`'s own `is_valid`/`area <= 0` validator gets a chance to reject
    it — Shapely's `.centroid` doesn't raise on invalid geometry, it just
    returns a point, so the rejection must still come from `Feature`
    afterward.
    """
    data = _minimal_valid_data()
    data["features"][0]["geometry"] = {
        "type": "Polygon",
        "coordinates": [
            [
                [-0.10, 51.50],
                [-0.09, 51.51],
                [-0.09, 51.50],
                [-0.10, 51.51],
                [-0.10, 51.50],
            ]
        ],
    }
    data["features"][0]["properties"]["feature_type"] = "green"

    with pytest.raises(ValidationError):
        load_course(data)


def test_load_course_parses_valid_polygon_feature_with_expected_boundary_and_centroid() -> None:
    """A well-formed, closed Polygon ring parses into a `Feature.boundary` (closing vertex dropped)
    and a `position` matching its computed centroid (issue #22).

    The expected centroid is hand-computed as the arithmetic mean of the
    triangle's 3 vertices (a triangle's centroid is always the mean of its
    vertices), independently of `polygon_centroid` under test — this catches
    a real bug in `polygon_centroid` that a self-referential expected value
    would not.
    """
    data = _minimal_valid_data()
    data["features"][0]["geometry"] = {
        "type": "Polygon",
        "coordinates": [
            [
                [-0.1000, 51.5000],
                [-0.0990, 51.5000],
                [-0.0990, 51.5010],
                [-0.1000, 51.5000],
            ]
        ],
    }
    data["features"][0]["properties"]["feature_type"] = "green"

    course = load_course(data)
    feature = course.holes[0].features[0]

    expected_boundary = (
        Coordinate(latitude=51.5000, longitude=-0.1000),
        Coordinate(latitude=51.5000, longitude=-0.0990),
        Coordinate(latitude=51.5010, longitude=-0.0990),
    )
    expected_latitude = (51.5000 + 51.5000 + 51.5010) / 3
    expected_longitude = (-0.1000 + -0.0990 + -0.0990) / 3

    assert feature.feature_type == FeatureType.GREEN
    assert feature.boundary == expected_boundary
    assert feature.position.latitude == pytest.approx(expected_latitude)
    assert feature.position.longitude == pytest.approx(expected_longitude)


def test_load_course_rejects_polygon_ring_that_is_not_closed() -> None:
    """A Polygon ring whose first and last positions differ is not a valid
    GeoJSON ring (issue #22).
    """
    data = _minimal_valid_data()
    data["features"][0]["geometry"] = {
        "type": "Polygon",
        "coordinates": [
            [
                [-0.1000, 51.5000],
                [-0.0990, 51.5000],
                [-0.0990, 51.5010],
                [-0.1000, 51.5001],  # not equal to the first position
            ]
        ],
    }

    with pytest.raises(ValueError):
        load_course(data)


def test_load_course_rejects_polygon_ring_with_fewer_than_four_positions() -> None:
    """A closed ring with fewer than 4 positions (fewer than 3 distinct vertices)
    is rejected (issue #22).
    """
    data = _minimal_valid_data()
    data["features"][0]["geometry"] = {
        "type": "Polygon",
        "coordinates": [
            [
                [-0.1000, 51.5000],
                [-0.0990, 51.5000],
                [-0.1000, 51.5000],
            ]
        ],
    }

    with pytest.raises(ValueError):
        load_course(data)


def test_load_course_rejects_polygon_with_zero_rings() -> None:
    """A Polygon geometry with an empty `coordinates` list has no exterior ring
    to parse (issue #22).
    """
    data = _minimal_valid_data()
    data["features"][0]["geometry"] = {"type": "Polygon", "coordinates": []}

    with pytest.raises(ValueError):
        load_course(data)


def test_load_course_rejects_polygon_with_interior_ring() -> None:
    """A Polygon geometry with more than one ring (an interior ring/hole) is an
    explicit non-goal (issue #22).
    """
    data = _minimal_valid_data()
    data["features"][0]["geometry"] = {
        "type": "Polygon",
        "coordinates": [
            [
                [-0.1000, 51.5000],
                [-0.0980, 51.5000],
                [-0.0980, 51.5020],
                [-0.1000, 51.5020],
                [-0.1000, 51.5000],
            ],
            [
                [-0.0995, 51.5005],
                [-0.0990, 51.5005],
                [-0.0990, 51.5010],
                [-0.0995, 51.5005],
            ],
        ],
    }

    with pytest.raises(ValueError):
        load_course(data)


def test_load_course_rejects_duplicate_hole_numbers_in_metadata() -> None:
    """Two `properties.holes` entries sharing the same `number` must be rejected, not silently kept.

    Regression test for a bug where duplicate hole numbers in top-level
    metadata were silently accepted (fix landing in parallel on this branch).
    """
    data = _minimal_valid_data()
    data["properties"]["holes"] = [
        {"number": 1, "par": 4},
        {"number": 1, "par": 5},
    ]

    with pytest.raises(ValueError):
        load_course(data)


def test_load_course_rejects_hole_declared_with_zero_matching_features() -> None:
    """A hole declared in metadata with no matching features fails `Hole.features`'s min_length."""
    data = _minimal_valid_data()
    data["properties"]["holes"] = [
        {"number": 1, "par": 4},
        {"number": 2, "par": 3},
    ]
    # `features` only contains a feature for hole 1; hole 2 has zero matches.

    with pytest.raises(ValidationError):
        load_course(data)


def test_load_course_rejects_empty_top_level_features_list() -> None:
    """An empty top-level `features` list leaves every declared hole with zero features."""
    data = _minimal_valid_data()
    data["features"] = []

    with pytest.raises(ValidationError):
        load_course(data)


# --- Fixture polygon features (issue #22) ----------------------------------


def test_fixture_hole_one_green_polygon_has_expected_boundary_and_type() -> None:
    """The fixture's hole 1 green polygon (added for issue #22) has 4 boundary vertices."""
    course = load_course_from_file(FIXTURE_PATH)

    green_polygon = course.holes[0].features[-1]

    assert green_polygon.feature_type == FeatureType.GREEN
    assert green_polygon.boundary is not None
    assert len(green_polygon.boundary) == 4


def test_fixture_hole_two_bunker_polygon_has_expected_boundary_and_type() -> None:
    """The fixture's hole 2 bunker polygon (added for issue #22) has 3 boundary vertices."""
    course = load_course_from_file(FIXTURE_PATH)

    bunker_polygon = course.holes[1].features[-1]

    assert bunker_polygon.feature_type == FeatureType.BUNKER
    assert bunker_polygon.boundary is not None
    assert len(bunker_polygon.boundary) == 3
