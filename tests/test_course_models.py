"""Tests for the M2.3 course domain models: ``FeatureType``, ``Feature``, ``Hole``, ``Course``.

See GitHub issue #5 ("M2.3 — Course/hole/hazard domain models") for the
acceptance criteria these tests are derived from: models must validate
required fields (positive `par`, non-empty `holes`/`features` lists), and a
2-hole fixture course must construct successfully.

See GitHub issue #22 ("M2.4.5 — Polygon/boundary course geometry and GeoJSON
Polygon support") for the additional acceptance criteria covered here:
`Feature.boundary` accepts a valid exterior polygon ring whose centroid
matches `position`, and rejects too-few vertices, a mismatched `position`,
or a self-intersecting/degenerate ring — while `Feature` without `boundary`
remains fully backward compatible.
"""

import pytest
from pydantic import ValidationError

from caddai.course.models import Course, Feature, FeatureType, Hole, polygon_centroid
from caddai.gps.models import Coordinate


def _feature(feature_type: FeatureType, latitude: float = 0.0, longitude: float = 0.0) -> Feature:
    position = Coordinate(latitude=latitude, longitude=longitude)
    return Feature(feature_type=feature_type, position=position)


@pytest.mark.parametrize(
    "feature_type",
    [
        FeatureType.TEE,
        FeatureType.FAIRWAY,
        FeatureType.GREEN,
        FeatureType.BUNKER,
        FeatureType.WATER,
        FeatureType.OUT_OF_BOUNDS,
        FeatureType.LANDING_AREA,
    ],
)
def test_feature_type_members_have_expected_string_values(feature_type: FeatureType) -> None:
    """Every `FeatureType` member is a `str` subclass and constructs a valid `Feature`."""
    assert isinstance(feature_type, str)
    assert feature_type == feature_type.value

    feature = _feature(feature_type)

    assert feature.feature_type == feature_type


def test_feature_constructs_with_valid_data() -> None:
    """A feature with a valid type and position is accepted."""
    position = Coordinate(latitude=51.5074, longitude=-0.1278)

    feature = Feature(feature_type=FeatureType.TEE, position=position)

    assert feature.feature_type == FeatureType.TEE
    assert feature.position == position


def _square_boundary() -> tuple[Coordinate, ...]:
    """A small, axis-aligned square ring: 4 distinct vertices, no duplicated closing vertex."""
    return (
        Coordinate(latitude=51.5000, longitude=-0.1000),
        Coordinate(latitude=51.5000, longitude=-0.0990),
        Coordinate(latitude=51.5010, longitude=-0.0990),
        Coordinate(latitude=51.5010, longitude=-0.1000),
    )


_BOWTIE_BOUNDARY = (
    Coordinate(latitude=51.5000, longitude=-0.1000),
    Coordinate(latitude=51.5010, longitude=-0.0990),
    Coordinate(latitude=51.5010, longitude=-0.1000),
    Coordinate(latitude=51.5000, longitude=-0.0990),
)
"""A self-intersecting (bowtie) quadrilateral ring: edges A-B and C-D cross."""


def test_feature_accepts_valid_boundary_with_matching_centroid_position() -> None:
    """A `Feature` accepts a simple, non-degenerate `boundary` with its exact
    centroid `position` (issue #22).

    The expected centroid is hand-computed as the arithmetic mean of the
    square's 4 corners (a parallelogram's centroid is the average of all its
    corners), independently of `polygon_centroid` under test — this catches a
    real bug in `polygon_centroid` (wrong Shapely property, swapped x/y, wrong
    origin) that a self-referential expected value would not.
    """
    boundary = _square_boundary()
    position = Coordinate(latitude=51.5005, longitude=-0.0995)

    feature = Feature(feature_type=FeatureType.GREEN, position=position, boundary=boundary)

    assert feature.boundary == boundary
    assert feature.position.latitude == pytest.approx(position.latitude)
    assert feature.position.longitude == pytest.approx(position.longitude)

    # Secondary cross-check: also matches `polygon_centroid`'s own output.
    computed_centroid = polygon_centroid(boundary)
    assert feature.position.latitude == pytest.approx(computed_centroid.latitude)
    assert feature.position.longitude == pytest.approx(computed_centroid.longitude)


def test_feature_rejects_boundary_with_fewer_than_three_vertices() -> None:
    """A `boundary` with only 2 vertices violates the ring's `min_length=3`
    constraint (issue #22).
    """
    boundary = (
        Coordinate(latitude=51.5000, longitude=-0.1000),
        Coordinate(latitude=51.5000, longitude=-0.0990),
    )

    with pytest.raises(ValidationError):
        Feature(
            feature_type=FeatureType.GREEN,
            position=Coordinate(latitude=51.5000, longitude=-0.0995),
            boundary=boundary,
        )


def test_feature_rejects_position_not_matching_boundary_centroid() -> None:
    """A `position` that isn't `boundary`'s centroid (here, one of its own
    vertices) is rejected (issue #22).
    """
    boundary = _square_boundary()

    with pytest.raises(ValidationError):
        Feature(feature_type=FeatureType.GREEN, position=boundary[0], boundary=boundary)


def test_feature_rejects_degenerate_collinear_boundary() -> None:
    """A `boundary` of three collinear points has zero area and is rejected (issue #22)."""
    boundary = (
        Coordinate(latitude=51.5000, longitude=-0.1000),
        Coordinate(latitude=51.5000, longitude=-0.0995),
        Coordinate(latitude=51.5000, longitude=-0.0990),
    )

    with pytest.raises(ValidationError):
        Feature(
            feature_type=FeatureType.GREEN,
            position=Coordinate(latitude=51.5000, longitude=-0.0995),
            boundary=boundary,
        )


def test_feature_rejects_self_intersecting_bowtie_boundary() -> None:
    """A self-intersecting (bowtie) quadrilateral ring is geometrically invalid
    and rejected (issue #22).
    """
    with pytest.raises(ValidationError):
        Feature(
            feature_type=FeatureType.GREEN,
            position=Coordinate(latitude=51.5005, longitude=-0.0995),
            boundary=_BOWTIE_BOUNDARY,
        )


def test_feature_rejects_boundary_with_coincident_duplicate_vertex() -> None:
    """A `boundary` with a duplicate/coincident vertex pair among its 4
    vertices collapses toward a degenerate triangle with a zero-length edge
    and is rejected, regardless of `position` (issue #22; see
    tests.instructions.md's "coincident points" degenerate-geometry
    edge-case guidance).
    """
    boundary = (
        Coordinate(latitude=51.5000, longitude=-0.1000),
        Coordinate(latitude=51.5000, longitude=-0.1000),  # duplicate of the first vertex
        Coordinate(latitude=51.5010, longitude=-0.0990),
        Coordinate(latitude=51.5010, longitude=-0.1000),
    )

    with pytest.raises(ValidationError):
        Feature(
            feature_type=FeatureType.GREEN,
            position=Coordinate(latitude=51.5005, longitude=-0.0995),
            boundary=boundary,
        )


def test_feature_without_boundary_behaves_exactly_as_before() -> None:
    """Regression: a `Feature` with `boundary=None` (the default) constructs
    exactly as pre-issue #22.
    """
    position = Coordinate(latitude=51.5074, longitude=-0.1278)

    feature = Feature(feature_type=FeatureType.TEE, position=position)

    assert feature.feature_type == FeatureType.TEE
    assert feature.position == position
    assert feature.boundary is None


def test_hole_constructs_with_valid_data() -> None:
    """A hole with a positive number, positive par, and at least one feature is accepted."""
    features = [_feature(FeatureType.TEE), _feature(FeatureType.GREEN)]

    hole = Hole(number=1, par=4, features=features)

    assert hole.number == 1
    assert hole.par == 4
    assert hole.features == features


def test_course_constructs_with_valid_data() -> None:
    """A course with a non-empty name and at least one hole is accepted."""
    hole = Hole(number=1, par=4, features=[_feature(FeatureType.TEE)])

    course = Course(name="Test Links", holes=[hole])

    assert course.name == "Test Links"
    assert course.holes == [hole]


def test_two_hole_fixture_course_constructs_successfully() -> None:
    """A 2-hole fixture course, each hole with tee/fairway/green features, constructs (issue #5)."""
    hole_one = Hole(
        number=1,
        par=4,
        features=[
            _feature(FeatureType.TEE, latitude=51.000, longitude=-0.100),
            _feature(FeatureType.FAIRWAY, latitude=51.001, longitude=-0.101),
            _feature(FeatureType.GREEN, latitude=51.002, longitude=-0.102),
        ],
    )
    hole_two = Hole(
        number=2,
        par=3,
        features=[
            _feature(FeatureType.TEE, latitude=51.003, longitude=-0.103),
            _feature(FeatureType.FAIRWAY, latitude=51.004, longitude=-0.104),
            _feature(FeatureType.GREEN, latitude=51.005, longitude=-0.105),
        ],
    )

    course = Course(name="Fixture Links", holes=[hole_one, hole_two])

    assert [hole.number for hole in course.holes] == [1, 2]
    assert all(len(hole.features) == 3 for hole in course.holes)


@pytest.mark.parametrize("par", [0, -1, -4])
def test_hole_rejects_non_positive_par(par: int) -> None:
    """Zero or negative par is not a valid hole definition."""
    with pytest.raises(ValidationError):
        Hole(number=1, par=par, features=[_feature(FeatureType.TEE)])


@pytest.mark.parametrize("number", [0, -1, -18])
def test_hole_rejects_non_positive_number(number: int) -> None:
    """Zero or negative hole numbers are not valid — hole numbering starts at 1."""
    with pytest.raises(ValidationError):
        Hole(number=number, par=4, features=[_feature(FeatureType.TEE)])


def test_hole_rejects_empty_features_list() -> None:
    """A hole must have at least one feature — an empty feature list is invalid."""
    with pytest.raises(ValidationError):
        Hole(number=1, par=4, features=[])


def test_course_rejects_empty_holes_list() -> None:
    """A course must have at least one hole — an empty holes list is invalid."""
    with pytest.raises(ValidationError):
        Course(name="Empty Course", holes=[])


def test_course_rejects_empty_name() -> None:
    """An empty course name violates the non-empty-name invariant."""
    hole = Hole(number=1, par=4, features=[_feature(FeatureType.TEE)])

    with pytest.raises(ValidationError):
        Course(name="", holes=[hole])
