"""Tests for the M2.3 course domain models: ``FeatureType``, ``Feature``, ``Hole``, ``Course``.

See GitHub issue #5 ("M2.3 — Course/hole/hazard domain models") for the
acceptance criteria these tests are derived from: models must validate
required fields (positive `par`, non-empty `holes`/`features` lists), and a
2-hole fixture course must construct successfully.
"""

import pytest
from pydantic import ValidationError

from caddai.course.models import Course, Feature, FeatureType, Hole
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
