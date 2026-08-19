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
"""

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from caddai.course.geojson import load_course, load_course_from_file
from caddai.course.models import FeatureType

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
    """Each fixture hole has exactly the tee/fairway/green features declared in the file."""
    course = load_course_from_file(FIXTURE_PATH)

    expected_types = [FeatureType.TEE, FeatureType.FAIRWAY, FeatureType.GREEN]
    for hole in course.holes:
        assert len(hole.features) == 3
        assert [feature.feature_type for feature in hole.features] == expected_types


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


def test_load_course_rejects_non_point_geometry() -> None:
    """A feature with `geometry.type` other than `"Point"` is not supported and must be rejected."""
    data = _minimal_valid_data()
    data["features"][0]["geometry"] = {
        "type": "Polygon",
        "coordinates": [
            [[-0.1278, 51.5074], [-0.1250, 51.5090], [-0.1220, 51.5105], [-0.1278, 51.5074]]
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
