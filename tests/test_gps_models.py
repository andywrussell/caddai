"""Tests for the M2.1 GPS coordinate model: ``Coordinate``.

See GitHub issue #3 ("M2.1 — GPS coordinate & distance primitives") for the
acceptance criteria these tests are derived from: latitude must validate to
[-90, 90] degrees and longitude to [-180, 180] degrees, both inclusive.
"""

import pytest
from pydantic import ValidationError

from caddai.gps.models import Coordinate


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (0.0, 0.0),
        (51.5074, -0.1278),
        (-33.8688, 151.2093),
        (90.0, 180.0),
        (-90.0, -180.0),
        (90.0, 0.0),
        (-90.0, 0.0),
        (0.0, 180.0),
        (0.0, -180.0),
    ],
    ids=[
        "origin",
        "typical-northern-hemisphere",
        "typical-southern-hemisphere",
        "north-pole-antimeridian",
        "south-pole-antimeridian-negative",
        "north-pole-prime-meridian",
        "south-pole-prime-meridian",
        "equator-antimeridian",
        "equator-antimeridian-negative",
    ],
)
def test_coordinate_accepts_valid_and_boundary_values(latitude: float, longitude: float) -> None:
    """Latitude in [-90, 90] and longitude in [-180, 180], including the boundaries, are valid."""
    coordinate = Coordinate(latitude=latitude, longitude=longitude)

    assert coordinate.latitude == pytest.approx(latitude)
    assert coordinate.longitude == pytest.approx(longitude)


@pytest.mark.parametrize("latitude", [90.0000001, 91.0, 180.0, 1000.0])
def test_coordinate_rejects_latitude_above_90(latitude: float) -> None:
    """Latitude greater than 90 degrees is not a valid geographic coordinate."""
    with pytest.raises(ValidationError):
        Coordinate(latitude=latitude, longitude=0.0)


@pytest.mark.parametrize("latitude", [-90.0000001, -91.0, -180.0, -1000.0])
def test_coordinate_rejects_latitude_below_negative_90(latitude: float) -> None:
    """Latitude less than -90 degrees is not a valid geographic coordinate."""
    with pytest.raises(ValidationError):
        Coordinate(latitude=latitude, longitude=0.0)


@pytest.mark.parametrize("longitude", [180.0000001, 181.0, 360.0, 1000.0])
def test_coordinate_rejects_longitude_above_180(longitude: float) -> None:
    """Longitude greater than 180 degrees is not a valid geographic coordinate."""
    with pytest.raises(ValidationError):
        Coordinate(latitude=0.0, longitude=longitude)


@pytest.mark.parametrize("longitude", [-180.0000001, -181.0, -360.0, -1000.0])
def test_coordinate_rejects_longitude_below_negative_180(longitude: float) -> None:
    """Longitude less than -180 degrees is not a valid geographic coordinate."""
    with pytest.raises(ValidationError):
        Coordinate(latitude=0.0, longitude=longitude)
