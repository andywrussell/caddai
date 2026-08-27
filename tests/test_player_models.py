"""Tests for the player domain model: ``Club``, ``ClubCategory``, and ``Player``.

See GitHub issue #28 for the acceptance criteria covering composing
``Club`` from ``CarryDistribution`` and ``DirectionalDispersion`` rather
than a bare expected-carry scalar.

See GitHub issue #29 for the acceptance criteria covering ``ClubCategory``
and the required ``Club.category`` field: parametrized construction across
every category, rejection of an out-of-enum category string, and the
``with_expected_carry`` category default/override behaviour.

See GitHub issue #30 for the acceptance criteria covering ``ShotRecord``
and ``Player.shot_history``: a data-model-only, manually entered, observed
shot outcome, with no derivation/fitting of ``CarryDistribution``/
``DirectionalDispersion`` from history.

See GitHub issue #38 ("M3.x — Enforce finite values in statistical domain
models") for the acceptance criteria covering nested-validation
propagation: a non-finite value in a ``Club``'s nested
``carry_distribution``/``dispersion`` fields must raise ``ValidationError``
through ``Club``, not just when constructing the nested model directly.

See also GitHub issue #43 ("M3.x — Reject non-finite ``ShotRecord``
measurements") for the acceptance criteria covering ``ShotRecord`` directly:
``final_downrange_metres`` and ``lateral_offset_metres`` must reject NaN and
+/-infinity, since ``+inf`` otherwise satisfies both ``final_downrange_metres``'s
``ge=0`` constraint and ``lateral_offset_metres``'s unconstrained sign.

See GitHub issue #50 ("M4.2 — `PopulationPrior` population parameter
model") for the acceptance criteria covering the ``ClubCategory`` migration
from ``caddai.player`` to ``caddai.statistics``: the canonical definition
moved to ``caddai.statistics.models`` (statistics must remain a leaf
module), but every existing import path and serialized ``StrEnum`` value
is preserved via a re-export from ``caddai.player``.

See GitHub issue #52 ("M4.4 — `ShotRecord` provenance and
measurement-quality fields") for the acceptance criteria covering the
evidence-only ``ShotRecord`` shape: ``final_downrange_metres`` (required,
renamed from ``achieved_carry_metres`` via an intermediate
``total_distance_metres``), the new optional ``observed_carry_metres``
(null-paired with ``observed_carry_measurement``), and per-quantity
``ShotMeasurementMetadata`` (``source``/``quality``) on
``endpoint_measurement`` (renamed from ``total_distance_measurement``,
covering both ``final_downrange_metres`` and ``lateral_offset_metres`` as
one shared final-position observation) and ``observed_carry_measurement``
rather than record-level flat fields. ``ShotMeasurementSource`` members are
``LAUNCH_MONITOR``/``GPS_DEVICE``/``MANUAL``/``UNKNOWN`` (renamed from
``MEASURED``/``GPS_ESTIMATE``/``MANUAL_ESTIMATE``/``UNKNOWN``). No
cross-field carry<=downrange consistency check is enforced — ``ShotRecord``
records evidence, not physics consistency.
"""

import pytest
from pydantic import ValidationError

import caddai.player as player_package
import caddai.player.models as player_models_module
import caddai.statistics as statistics_package
import caddai.statistics.models as statistics_models_module
from caddai.player.models import (
    Club,
    ClubCategory,
    Player,
    ShotMeasurementMetadata,
    ShotMeasurementQuality,
    ShotMeasurementSource,
    ShotRecord,
)
from caddai.statistics import CarryDistribution, DirectionalDispersion


def test_club_constructs_with_valid_data() -> None:
    """A club with a non-empty name and explicit distribution/dispersion round-trips."""
    carry_distribution = CarryDistribution(mean_metres=140.0, stddev_metres=8.5)
    dispersion = DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0)

    club = Club(
        name="7 Iron",
        carry_distribution=carry_distribution,
        dispersion=dispersion,
        category=ClubCategory.IRON,
    )

    assert club.name == "7 Iron"
    assert club.carry_distribution == carry_distribution
    assert club.dispersion == dispersion
    assert club.category == ClubCategory.IRON


def test_club_expected_carry_metres_reflects_carry_distribution_mean() -> None:
    """``expected_carry_metres`` is derived from ``carry_distribution.mean_metres``."""
    club = Club(
        name="7 Iron",
        carry_distribution=CarryDistribution(mean_metres=140.0, stddev_metres=8.5),
        dispersion=DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0),
        category=ClubCategory.IRON,
    )

    assert club.expected_carry_metres == pytest.approx(140.0)


@pytest.mark.parametrize(
    ("stddev_metres", "lateral_stddev_metres", "lateral_bias_metres"),
    [
        (0.0, 0.0, 0.0),
        (8.5, 4.5, -2.0),
        (20.0, 10.0, 5.0),
    ],
)
def test_club_expected_carry_metres_independent_of_dispersion(
    stddev_metres: float, lateral_stddev_metres: float, lateral_bias_metres: float
) -> None:
    """``expected_carry_metres`` depends only on ``mean_metres``, not on any spread values."""
    club = Club(
        name="7 Iron",
        carry_distribution=CarryDistribution(mean_metres=150.0, stddev_metres=stddev_metres),
        dispersion=DirectionalDispersion(
            lateral_stddev_metres=lateral_stddev_metres,
            lateral_bias_metres=lateral_bias_metres,
        ),
        category=ClubCategory.IRON,
    )

    assert club.expected_carry_metres == pytest.approx(150.0)


def test_club_rejects_missing_carry_distribution() -> None:
    """A club without a ``carry_distribution`` is not a valid club."""
    with pytest.raises(ValidationError):
        Club(
            name="7 Iron",
            dispersion=DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0),
            category=ClubCategory.IRON,
        )


def test_club_rejects_missing_dispersion() -> None:
    """A club without a ``dispersion`` is not a valid club."""
    with pytest.raises(ValidationError):
        Club(
            name="7 Iron",
            carry_distribution=CarryDistribution(mean_metres=140.0, stddev_metres=8.5),
            category=ClubCategory.IRON,
        )


def test_club_rejects_bare_scalar_carry_distribution() -> None:
    """Regression guard: the old bare-scalar ``Club`` shape is no longer accepted."""
    with pytest.raises(ValidationError):
        Club(
            name="7 Iron",
            carry_distribution=140.0,
            dispersion=DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0),
            category=ClubCategory.IRON,
        )


def test_club_coerces_nested_dicts_into_models() -> None:
    """Nested dicts for ``carry_distribution``/``dispersion`` are coerced into real models."""
    club = Club(
        name="7 Iron",
        carry_distribution={"mean_metres": 140.0, "stddev_metres": 8.5},
        dispersion={"lateral_stddev_metres": 4.5, "lateral_bias_metres": -2.0},
        category=ClubCategory.IRON,
    )

    assert isinstance(club.carry_distribution, CarryDistribution)
    assert isinstance(club.dispersion, DirectionalDispersion)
    assert club.carry_distribution.mean_metres == pytest.approx(140.0)
    assert club.carry_distribution.stddev_metres == pytest.approx(8.5)
    assert club.dispersion.lateral_stddev_metres == pytest.approx(4.5)
    assert club.dispersion.lateral_bias_metres == pytest.approx(-2.0)


@pytest.mark.parametrize("mean_metres", [0.0, -1.0, -140.0])
def test_club_rejects_invalid_nested_carry_distribution(mean_metres: float) -> None:
    """``CarryDistribution``'s ``gt=0`` constraint bubbles up through ``Club``."""
    with pytest.raises(ValidationError):
        Club(
            name="7 Iron",
            carry_distribution={"mean_metres": mean_metres, "stddev_metres": 8.5},
            dispersion=DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0),
            category=ClubCategory.IRON,
        )


@pytest.mark.parametrize("mean_metres", [float("nan"), float("inf"), float("-inf")])
def test_club_rejects_non_finite_nested_carry_distribution_mean(mean_metres: float) -> None:
    """Issue #38: a non-finite nested ``carry_distribution.mean_metres`` raises through ``Club``."""
    with pytest.raises(ValidationError):
        Club(
            name="7 Iron",
            carry_distribution={"mean_metres": mean_metres, "stddev_metres": 1.0},
            dispersion=DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0),
            category=ClubCategory.IRON,
        )


@pytest.mark.parametrize("stddev_metres", [float("nan"), float("inf"), float("-inf")])
def test_club_rejects_non_finite_nested_carry_distribution_stddev(stddev_metres: float) -> None:
    """Issue #38: a non-finite nested ``carry_distribution.stddev_metres`` raises via ``Club``."""
    with pytest.raises(ValidationError):
        Club(
            name="7 Iron",
            carry_distribution={"mean_metres": 140.0, "stddev_metres": stddev_metres},
            dispersion=DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0),
            category=ClubCategory.IRON,
        )


@pytest.mark.parametrize("lateral_stddev_metres", [float("nan"), float("inf"), float("-inf")])
def test_club_rejects_non_finite_nested_dispersion_lateral_stddev(
    lateral_stddev_metres: float,
) -> None:
    """Issue #38: a non-finite nested ``dispersion.lateral_stddev_metres`` raises via ``Club``."""
    with pytest.raises(ValidationError):
        Club(
            name="7 Iron",
            carry_distribution=CarryDistribution(mean_metres=140.0, stddev_metres=8.5),
            dispersion={
                "lateral_stddev_metres": lateral_stddev_metres,
                "lateral_bias_metres": -2.0,
            },
            category=ClubCategory.IRON,
        )


@pytest.mark.parametrize("lateral_bias_metres", [float("nan"), float("inf"), float("-inf")])
def test_club_rejects_non_finite_nested_dispersion_lateral_bias(
    lateral_bias_metres: float,
) -> None:
    """Issue #38: a non-finite nested ``dispersion.lateral_bias_metres`` raises through ``Club``."""
    with pytest.raises(ValidationError):
        Club(
            name="7 Iron",
            carry_distribution=CarryDistribution(mean_metres=140.0, stddev_metres=8.5),
            dispersion={"lateral_stddev_metres": 4.5, "lateral_bias_metres": lateral_bias_metres},
            category=ClubCategory.IRON,
        )


def test_club_rejects_empty_name() -> None:
    """An empty club name violates the non-empty-name invariant, even with valid nested models."""
    with pytest.raises(ValidationError):
        Club(
            name="",
            carry_distribution=CarryDistribution(mean_metres=140.0, stddev_metres=8.5),
            dispersion=DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0),
            category=ClubCategory.IRON,
        )


@pytest.mark.parametrize(
    "category",
    [
        ClubCategory.DRIVER,
        ClubCategory.FAIRWAY_WOOD,
        ClubCategory.HYBRID,
        ClubCategory.IRON,
        ClubCategory.WEDGE,
        ClubCategory.PUTTER,
        ClubCategory.OTHER,
    ],
)
def test_club_category_members_construct_valid_club(category: ClubCategory) -> None:
    """Every ``ClubCategory`` member is a ``str`` subclass and constructs a valid ``Club``."""
    assert isinstance(category, str)
    assert category == category.value

    club = Club(
        name="7 Iron",
        carry_distribution=CarryDistribution(mean_metres=140.0, stddev_metres=8.5),
        dispersion=DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0),
        category=category,
    )

    assert club.category == category


def test_club_rejects_invalid_category_string() -> None:
    """A ``category`` string outside ``ClubCategory``'s values is rejected."""
    with pytest.raises(ValidationError):
        Club(
            name="7 Iron",
            carry_distribution=CarryDistribution(mean_metres=140.0, stddev_metres=8.5),
            dispersion=DirectionalDispersion(lateral_stddev_metres=4.5, lateral_bias_metres=-2.0),
            category="mid-iron",
        )


def test_club_expected_carry_metres_is_read_only() -> None:
    """``expected_carry_metres`` is a derived computed field and cannot be assigned directly."""
    club = Club.with_expected_carry(name="7 Iron", expected_carry_metres=140.0)

    with pytest.raises(AttributeError):
        club.expected_carry_metres = 200.0


def test_club_with_expected_carry_builds_degenerate_distribution_and_dispersion() -> None:
    """The convenience constructor builds a zero-variance, zero-bias club from a bare scalar."""
    club = Club.with_expected_carry(name="7 Iron", expected_carry_metres=140.0)

    assert club.carry_distribution.mean_metres == pytest.approx(140.0)
    assert club.carry_distribution.stddev_metres == pytest.approx(0.0)
    assert club.dispersion.lateral_stddev_metres == pytest.approx(0.0)
    assert club.dispersion.lateral_bias_metres == pytest.approx(0.0)
    assert club.expected_carry_metres == pytest.approx(140.0)


@pytest.mark.parametrize("expected_carry_metres", [0.0, -1.0, -140.0])
def test_club_with_expected_carry_rejects_non_positive_expected_carry(
    expected_carry_metres: float,
) -> None:
    """Zero or negative expected carry distance is physically meaningless."""
    with pytest.raises(ValidationError):
        Club.with_expected_carry(name="7 Iron", expected_carry_metres=expected_carry_metres)


def test_club_with_expected_carry_rejects_empty_name() -> None:
    """An empty club name is rejected via the convenience constructor too."""
    with pytest.raises(ValidationError):
        Club.with_expected_carry(name="", expected_carry_metres=140.0)


def test_club_with_expected_carry_is_deterministic() -> None:
    """Two clubs built from the same arguments are equal — load-bearing for demo determinism."""
    assert Club.with_expected_carry("7 Iron", 140.0) == Club.with_expected_carry("7 Iron", 140.0)


def test_club_with_expected_carry_defaults_category_to_other() -> None:
    """Without an explicit ``category``, the convenience constructor defaults to ``OTHER``."""
    club = Club.with_expected_carry(name="7 Iron", expected_carry_metres=140.0)

    assert club.category == ClubCategory.OTHER


def test_club_with_expected_carry_accepts_explicit_category() -> None:
    """An explicit ``category`` argument overrides the ``ClubCategory.OTHER`` default."""
    club = Club.with_expected_carry(
        name="Driver", expected_carry_metres=230.0, category=ClubCategory.DRIVER
    )

    assert club.category == ClubCategory.DRIVER


def test_player_constructs_with_valid_data() -> None:
    """A player with a non-empty name and at least one club is accepted."""
    clubs = [Club.with_expected_carry(name="7 Iron", expected_carry_metres=140.0)]

    player = Player(name="Ada", clubs=clubs)

    assert player.name == "Ada"
    assert player.clubs == clubs


def test_player_rejects_empty_name() -> None:
    """An empty player name violates the non-empty-name invariant."""
    clubs = [Club.with_expected_carry(name="7 Iron", expected_carry_metres=140.0)]

    with pytest.raises(ValidationError):
        Player(name="", clubs=clubs)


def test_player_rejects_empty_clubs_list() -> None:
    """A player must own at least one club — an empty bag is invalid, not silently accepted."""
    with pytest.raises(ValidationError):
        Player(name="Ada", clubs=[])


def test_shot_record_constructs_with_only_required_fields() -> None:
    """Only ``club_name``/``final_downrange_metres``/``lateral_offset_metres`` are required.

    ``observed_carry_metres``/``observed_carry_measurement`` default to ``None`` (true carry
    is latent and rarely observed) and ``endpoint_measurement`` defaults to an
    ``UNKNOWN``/``UNKNOWN`` ``ShotMeasurementMetadata()``.
    """
    shot_record = ShotRecord(
        club_name="7 Iron", final_downrange_metres=142.5, lateral_offset_metres=-3.0
    )

    assert shot_record.club_name == "7 Iron"
    assert shot_record.final_downrange_metres == pytest.approx(142.5)
    assert shot_record.lateral_offset_metres == pytest.approx(-3.0)
    assert shot_record.observed_carry_metres is None
    assert shot_record.observed_carry_measurement is None
    assert shot_record.endpoint_measurement == ShotMeasurementMetadata()
    assert shot_record.notes is None


def test_shot_record_notes_defaults_to_none() -> None:
    """Omitting ``notes`` gives ``None``."""
    shot_record = ShotRecord(
        club_name="7 Iron", final_downrange_metres=142.5, lateral_offset_metres=-3.0
    )

    assert shot_record.notes is None


def test_shot_record_notes_accepts_explicit_string() -> None:
    """An explicit ``notes`` string round-trips."""
    shot_record = ShotRecord(
        club_name="7 Iron",
        final_downrange_metres=142.5,
        lateral_offset_metres=-3.0,
        notes="wet rough",
    )

    assert shot_record.notes == "wet rough"


@pytest.mark.parametrize("lateral_offset_metres", [-15.5, 0.0, 12.0])
def test_shot_record_accepts_negative_zero_and_positive_lateral_offset(
    lateral_offset_metres: float,
) -> None:
    """Negative (left), zero (on-line), and positive (right) offsets are all accepted."""
    shot_record = ShotRecord(
        club_name="7 Iron",
        final_downrange_metres=142.5,
        lateral_offset_metres=lateral_offset_metres,
    )

    assert shot_record.lateral_offset_metres == pytest.approx(lateral_offset_metres)


def test_shot_record_rejects_missing_lateral_offset_metres() -> None:
    """A shot record without a ``lateral_offset_metres`` is not valid — it has no default."""
    with pytest.raises(ValidationError):
        ShotRecord(club_name="7 Iron", final_downrange_metres=142.5)  # type: ignore[call-arg]


@pytest.mark.parametrize("lateral_offset_metres", [float("nan"), float("inf"), float("-inf")])
def test_shot_record_rejects_non_finite_lateral_offset_metres(
    lateral_offset_metres: float,
) -> None:
    """Issue #43: lateral offset is unconstrained in sign but must still be finite."""
    with pytest.raises(ValidationError):
        ShotRecord(
            club_name="7 Iron",
            final_downrange_metres=142.5,
            lateral_offset_metres=lateral_offset_metres,
        )


def test_shot_record_final_downrange_metres_accepts_zero() -> None:
    """``0.0`` is accepted — a whiffed/topped shot, unlike ``CarryDistribution.mean_metres``."""
    shot_record = ShotRecord(
        club_name="7 Iron", final_downrange_metres=0.0, lateral_offset_metres=0.0
    )

    assert shot_record.final_downrange_metres == pytest.approx(0.0)


@pytest.mark.parametrize("final_downrange_metres", [-0.1, -1.0, -140.0])
def test_shot_record_rejects_negative_final_downrange_metres(final_downrange_metres: float) -> None:
    """A negative downrange distance is physically meaningless."""
    with pytest.raises(ValidationError):
        ShotRecord(
            club_name="7 Iron",
            final_downrange_metres=final_downrange_metres,
            lateral_offset_metres=0.0,
        )


def test_shot_record_rejects_missing_final_downrange_metres() -> None:
    """A shot record without a ``final_downrange_metres`` is not valid — always observable."""
    with pytest.raises(ValidationError):
        ShotRecord(club_name="7 Iron", lateral_offset_metres=-3.0)  # type: ignore[call-arg]


@pytest.mark.parametrize("final_downrange_metres", [float("nan"), float("inf"), float("-inf")])
def test_shot_record_rejects_non_finite_final_downrange_metres(
    final_downrange_metres: float,
) -> None:
    """Issue #43: NaN/+inf/-inf are rejected even though ``+inf`` satisfies ``ge=0``."""
    with pytest.raises(ValidationError):
        ShotRecord(
            club_name="7 Iron",
            final_downrange_metres=final_downrange_metres,
            lateral_offset_metres=0.0,
        )


def test_shot_record_rejects_empty_club_name() -> None:
    """An empty club name violates the non-empty-name invariant, consistent with ``Club.name``."""
    with pytest.raises(ValidationError):
        ShotRecord(club_name="", final_downrange_metres=142.5, lateral_offset_metres=-3.0)


def test_shot_record_rejects_missing_club_name() -> None:
    """A shot record without a ``club_name`` is not valid."""
    with pytest.raises(ValidationError):
        ShotRecord(  # type: ignore[call-arg]
            final_downrange_metres=142.5, lateral_offset_metres=-3.0
        )


# --- observed_carry_metres optionality and null-pairing (issue #52) --------------


def test_shot_record_observed_carry_metres_absent_by_default() -> None:
    """``observed_carry_metres`` is ``None`` by default — the common on-course case."""
    shot_record = ShotRecord(
        club_name="7 Iron", final_downrange_metres=142.5, lateral_offset_metres=-3.0
    )

    assert shot_record.observed_carry_metres is None
    assert shot_record.observed_carry_measurement is None


def test_shot_record_observed_carry_metres_explicit_none_is_valid() -> None:
    """Explicitly passing ``observed_carry_metres=None`` is equivalent to omitting it."""
    shot_record = ShotRecord(
        club_name="7 Iron",
        final_downrange_metres=142.5,
        lateral_offset_metres=-3.0,
        observed_carry_metres=None,
        observed_carry_measurement=None,
    )

    assert shot_record.observed_carry_metres is None
    assert shot_record.observed_carry_measurement is None


def test_shot_record_observed_carry_metres_accepts_genuine_value_with_metadata() -> None:
    """A genuine positive ``observed_carry_metres`` is valid alongside its metadata."""
    shot_record = ShotRecord(
        club_name="7 Iron",
        final_downrange_metres=142.5,
        lateral_offset_metres=-3.0,
        observed_carry_metres=138.0,
        observed_carry_measurement=ShotMeasurementMetadata(
            source=ShotMeasurementSource.LAUNCH_MONITOR, quality=ShotMeasurementQuality.HIGH
        ),
    )

    assert shot_record.observed_carry_metres == pytest.approx(138.0)
    assert shot_record.observed_carry_measurement == ShotMeasurementMetadata(
        source=ShotMeasurementSource.LAUNCH_MONITOR, quality=ShotMeasurementQuality.HIGH
    )


def test_shot_record_observed_carry_metres_accepts_zero_with_metadata() -> None:
    """``0.0`` observed carry (e.g. a whiffed/topped shot) is accepted when metadata is supplied."""
    shot_record = ShotRecord(
        club_name="7 Iron",
        final_downrange_metres=0.0,
        lateral_offset_metres=0.0,
        observed_carry_metres=0.0,
        observed_carry_measurement=ShotMeasurementMetadata(),
    )

    assert shot_record.observed_carry_metres == pytest.approx(0.0)


@pytest.mark.parametrize("observed_carry_metres", [-0.1, -1.0, -140.0])
def test_shot_record_rejects_negative_observed_carry_metres(observed_carry_metres: float) -> None:
    """A negative observed carry distance is physically meaningless."""
    with pytest.raises(ValidationError):
        ShotRecord(
            club_name="7 Iron",
            final_downrange_metres=142.5,
            lateral_offset_metres=-3.0,
            observed_carry_metres=observed_carry_metres,
            observed_carry_measurement=ShotMeasurementMetadata(),
        )


@pytest.mark.parametrize("observed_carry_metres", [float("nan"), float("inf"), float("-inf")])
def test_shot_record_rejects_non_finite_observed_carry_metres(
    observed_carry_metres: float,
) -> None:
    """NaN/+inf/-inf are rejected for ``observed_carry_metres`` when present, as for the other
    distance fields."""
    with pytest.raises(ValidationError):
        ShotRecord(
            club_name="7 Iron",
            final_downrange_metres=142.5,
            lateral_offset_metres=-3.0,
            observed_carry_metres=observed_carry_metres,
            observed_carry_measurement=ShotMeasurementMetadata(),
        )


def test_shot_record_rejects_observed_carry_metres_without_measurement() -> None:
    """Setting ``observed_carry_metres`` without ``observed_carry_measurement`` is invalid —
    the null-pairing invariant."""
    with pytest.raises(ValidationError):
        ShotRecord(
            club_name="7 Iron",
            final_downrange_metres=142.5,
            lateral_offset_metres=-3.0,
            observed_carry_metres=138.0,
        )


def test_shot_record_rejects_observed_carry_measurement_without_metres() -> None:
    """Setting ``observed_carry_measurement`` without ``observed_carry_metres`` is invalid —
    a metadata object describing a value that doesn't exist is meaningless."""
    with pytest.raises(ValidationError):
        ShotRecord(
            club_name="7 Iron",
            final_downrange_metres=142.5,
            lateral_offset_metres=-3.0,
            observed_carry_measurement=ShotMeasurementMetadata(),
        )


def test_shot_record_accepts_observed_carry_greater_than_final_downrange() -> None:
    """No carry<=downrange consistency check is enforced — evidence from independent instruments
    may legitimately disagree, and this is not physics-consistency validated."""
    shot_record = ShotRecord(
        club_name="7 Iron",
        final_downrange_metres=100.0,
        lateral_offset_metres=0.0,
        observed_carry_metres=150.0,
        observed_carry_measurement=ShotMeasurementMetadata(),
    )

    assert shot_record.observed_carry_metres == pytest.approx(150.0)
    assert shot_record.final_downrange_metres == pytest.approx(100.0)


def test_shot_record_putter_has_no_carry_without_structural_pressure() -> None:
    """A putt (no meaningful carry concept) constructs validly with ``observed_carry_metres=None``
    — the shape doesn't force a carry value onto every club/shot."""
    shot_record = ShotRecord(
        club_name="Putter", final_downrange_metres=8.0, lateral_offset_metres=0.1
    )

    assert shot_record.observed_carry_metres is None
    assert shot_record.observed_carry_measurement is None


# --- ShotMeasurementMetadata (issue #52) -----------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        ShotMeasurementSource.LAUNCH_MONITOR,
        ShotMeasurementSource.GPS_DEVICE,
        ShotMeasurementSource.MANUAL,
        ShotMeasurementSource.UNKNOWN,
    ],
)
def test_shot_record_endpoint_measurement_accepts_every_source_member(
    source: ShotMeasurementSource,
) -> None:
    """Every ``ShotMeasurementSource`` member round-trips through ``endpoint_measurement``."""
    shot_record = ShotRecord(
        club_name="7 Iron",
        final_downrange_metres=142.5,
        lateral_offset_metres=-3.0,
        endpoint_measurement=ShotMeasurementMetadata(source=source),
    )

    assert shot_record.endpoint_measurement.source == source


@pytest.mark.parametrize(
    "quality",
    [
        ShotMeasurementQuality.UNKNOWN,
        ShotMeasurementQuality.LOW,
        ShotMeasurementQuality.MODERATE,
        ShotMeasurementQuality.HIGH,
    ],
)
def test_shot_record_endpoint_measurement_accepts_every_quality_member(
    quality: ShotMeasurementQuality,
) -> None:
    """Every quality member round-trips through ``endpoint_measurement``."""
    shot_record = ShotRecord(
        club_name="7 Iron",
        final_downrange_metres=142.5,
        lateral_offset_metres=-3.0,
        endpoint_measurement=ShotMeasurementMetadata(quality=quality),
    )

    assert shot_record.endpoint_measurement.quality == quality


@pytest.mark.parametrize(
    "source",
    [
        ShotMeasurementSource.LAUNCH_MONITOR,
        ShotMeasurementSource.GPS_DEVICE,
        ShotMeasurementSource.MANUAL,
        ShotMeasurementSource.UNKNOWN,
    ],
)
def test_shot_record_observed_carry_measurement_accepts_every_source_member(
    source: ShotMeasurementSource,
) -> None:
    """Every ``ShotMeasurementSource`` member round-trips through ``observed_carry_measurement``."""
    shot_record = ShotRecord(
        club_name="7 Iron",
        final_downrange_metres=142.5,
        lateral_offset_metres=-3.0,
        observed_carry_metres=138.0,
        observed_carry_measurement=ShotMeasurementMetadata(source=source),
    )

    assert shot_record.observed_carry_measurement is not None
    assert shot_record.observed_carry_measurement.source == source


@pytest.mark.parametrize(
    "quality",
    [
        ShotMeasurementQuality.UNKNOWN,
        ShotMeasurementQuality.LOW,
        ShotMeasurementQuality.MODERATE,
        ShotMeasurementQuality.HIGH,
    ],
)
def test_shot_record_observed_carry_measurement_accepts_every_quality_member(
    quality: ShotMeasurementQuality,
) -> None:
    """Every quality member round-trips through ``observed_carry_measurement``."""
    shot_record = ShotRecord(
        club_name="7 Iron",
        final_downrange_metres=142.5,
        lateral_offset_metres=-3.0,
        observed_carry_metres=138.0,
        observed_carry_measurement=ShotMeasurementMetadata(quality=quality),
    )

    assert shot_record.observed_carry_measurement is not None
    assert shot_record.observed_carry_measurement.quality == quality


def test_shot_measurement_metadata_rejects_invalid_source_string() -> None:
    """A ``source`` string outside ``ShotMeasurementSource``'s values is rejected."""
    with pytest.raises(ValidationError):
        ShotMeasurementMetadata(source="radar")  # type: ignore[arg-type]


def test_shot_measurement_metadata_rejects_invalid_quality_string() -> None:
    """A ``quality`` string outside ``ShotMeasurementQuality``'s values is rejected."""
    with pytest.raises(ValidationError):
        ShotMeasurementMetadata(quality="excellent")  # type: ignore[arg-type]


def test_shot_record_rejects_invalid_endpoint_measurement_source_string() -> None:
    """An invalid ``source`` nested under ``endpoint_measurement`` raises through
    ``ShotRecord``, not just when constructing ``ShotMeasurementMetadata`` directly."""
    with pytest.raises(ValidationError):
        ShotRecord(
            club_name="7 Iron",
            final_downrange_metres=142.5,
            lateral_offset_metres=-3.0,
            endpoint_measurement={"source": "radar"},
        )


def test_shot_record_rejects_invalid_endpoint_measurement_quality_string() -> None:
    """An invalid ``quality`` nested under ``endpoint_measurement`` raises through
    ``ShotRecord``."""
    with pytest.raises(ValidationError):
        ShotRecord(
            club_name="7 Iron",
            final_downrange_metres=142.5,
            lateral_offset_metres=-3.0,
            endpoint_measurement={"quality": "excellent"},
        )


def test_shot_measurement_metadata_source_and_quality_are_independent() -> None:
    """``LAUNCH_MONITOR``+``LOW`` and ``UNKNOWN``+``HIGH`` both construct validly — quality is never
    derived from source."""
    measured_but_low_quality = ShotMeasurementMetadata(
        source=ShotMeasurementSource.LAUNCH_MONITOR, quality=ShotMeasurementQuality.LOW
    )
    unknown_source_but_high_quality = ShotMeasurementMetadata(
        source=ShotMeasurementSource.UNKNOWN, quality=ShotMeasurementQuality.HIGH
    )

    assert measured_but_low_quality.source == ShotMeasurementSource.LAUNCH_MONITOR
    assert measured_but_low_quality.quality == ShotMeasurementQuality.LOW
    assert unknown_source_but_high_quality.source == ShotMeasurementSource.UNKNOWN
    assert unknown_source_but_high_quality.quality == ShotMeasurementQuality.HIGH


def test_shot_record_endpoint_and_observed_carry_measurement_are_independent() -> None:
    """The two quantities' metadata are genuinely independent, not shared/record-level: a
    GPS-estimated downrange distance can coexist with an absent observed carry, and a fully
    ``LAUNCH_MONITOR``/``HIGH`` record has both set to the same values only because both were
    explicitly given that way."""
    gps_total_only = ShotRecord(
        club_name="7 Iron",
        final_downrange_metres=142.5,
        lateral_offset_metres=-3.0,
        endpoint_measurement=ShotMeasurementMetadata(
            source=ShotMeasurementSource.GPS_DEVICE, quality=ShotMeasurementQuality.MODERATE
        ),
        observed_carry_metres=None,
        observed_carry_measurement=None,
    )
    fully_measured = ShotRecord(
        club_name="7 Iron",
        final_downrange_metres=142.5,
        lateral_offset_metres=-3.0,
        endpoint_measurement=ShotMeasurementMetadata(
            source=ShotMeasurementSource.LAUNCH_MONITOR, quality=ShotMeasurementQuality.HIGH
        ),
        observed_carry_metres=138.0,
        observed_carry_measurement=ShotMeasurementMetadata(
            source=ShotMeasurementSource.LAUNCH_MONITOR, quality=ShotMeasurementQuality.HIGH
        ),
    )

    assert gps_total_only.endpoint_measurement.source == ShotMeasurementSource.GPS_DEVICE
    assert gps_total_only.observed_carry_measurement is None
    assert fully_measured.endpoint_measurement.source == ShotMeasurementSource.LAUNCH_MONITOR
    assert fully_measured.observed_carry_measurement is not None
    assert fully_measured.observed_carry_measurement.source == ShotMeasurementSource.LAUNCH_MONITOR


@pytest.mark.parametrize(
    ("endpoint_source", "observed_carry_source"),
    [
        (ShotMeasurementSource.GPS_DEVICE, ShotMeasurementSource.LAUNCH_MONITOR),
        (ShotMeasurementSource.MANUAL, ShotMeasurementSource.UNKNOWN),
    ],
)
def test_shot_record_metadata_per_quantity_differs_independently(
    endpoint_source: ShotMeasurementSource, observed_carry_source: ShotMeasurementSource
) -> None:
    """Setting a different ``source`` per quantity on the same record round-trips independently,
    confirming the metadata is not shared/record-level."""
    shot_record = ShotRecord(
        club_name="7 Iron",
        final_downrange_metres=142.5,
        lateral_offset_metres=-3.0,
        endpoint_measurement=ShotMeasurementMetadata(source=endpoint_source),
        observed_carry_metres=138.0,
        observed_carry_measurement=ShotMeasurementMetadata(source=observed_carry_source),
    )

    assert shot_record.endpoint_measurement.source == endpoint_source
    assert shot_record.observed_carry_measurement is not None
    assert shot_record.observed_carry_measurement.source == observed_carry_source


def test_shot_record_accepts_large_final_downrange_and_lateral_offset() -> None:
    """A large but genuine ``final_downrange_metres``/``lateral_offset_metres`` still constructs —
    no implicit outlier/severe-miss rejection."""
    shot_record = ShotRecord(
        club_name="Driver", final_downrange_metres=350.0, lateral_offset_metres=-80.0
    )

    assert shot_record.final_downrange_metres == pytest.approx(350.0)
    assert shot_record.lateral_offset_metres == pytest.approx(-80.0)


def test_shot_record_accepts_large_observed_carry_metres() -> None:
    """A large but genuine ``observed_carry_metres`` still constructs with matching metadata."""
    shot_record = ShotRecord(
        club_name="Driver",
        final_downrange_metres=350.0,
        lateral_offset_metres=-80.0,
        observed_carry_metres=310.0,
        observed_carry_measurement=ShotMeasurementMetadata(
            source=ShotMeasurementSource.LAUNCH_MONITOR, quality=ShotMeasurementQuality.HIGH
        ),
    )

    assert shot_record.observed_carry_metres == pytest.approx(310.0)


def test_shot_record_model_dump_with_all_defaults() -> None:
    """``model_dump()`` for an all-defaults record includes every field, with
    ``observed_carry_metres``/``observed_carry_measurement`` as ``None`` and
    ``endpoint_measurement`` as a nested ``UNKNOWN``/``UNKNOWN`` dict."""
    shot_record = ShotRecord(
        club_name="7 Iron", final_downrange_metres=142.5, lateral_offset_metres=-3.0
    )

    dumped = shot_record.model_dump()

    assert dumped["final_downrange_metres"] == pytest.approx(142.5)
    assert dumped["lateral_offset_metres"] == pytest.approx(-3.0)
    assert dumped["observed_carry_metres"] is None
    assert dumped["endpoint_measurement"] == {"source": "unknown", "quality": "unknown"}
    assert dumped["observed_carry_measurement"] is None
    assert dumped["notes"] is None


def test_shot_record_model_dump_fully_populated() -> None:
    """``model_dump()`` for a fully populated record serializes both metadata submodels and
    ``observed_carry_metres`` correctly."""
    shot_record = ShotRecord(
        club_name="7 Iron",
        final_downrange_metres=142.5,
        lateral_offset_metres=-3.0,
        observed_carry_metres=138.0,
        endpoint_measurement=ShotMeasurementMetadata(
            source=ShotMeasurementSource.GPS_DEVICE, quality=ShotMeasurementQuality.MODERATE
        ),
        observed_carry_measurement=ShotMeasurementMetadata(
            source=ShotMeasurementSource.LAUNCH_MONITOR, quality=ShotMeasurementQuality.HIGH
        ),
        notes="firm fairway, into wind",
    )

    dumped = shot_record.model_dump()

    assert dumped["final_downrange_metres"] == pytest.approx(142.5)
    assert dumped["lateral_offset_metres"] == pytest.approx(-3.0)
    assert dumped["observed_carry_metres"] == pytest.approx(138.0)
    assert dumped["endpoint_measurement"] == {"source": "gps_device", "quality": "moderate"}
    assert dumped["observed_carry_measurement"] == {"source": "launch_monitor", "quality": "high"}
    assert dumped["notes"] == "firm fairway, into wind"


# --- Player.shot_history (issue #52) ---------------------------------------------


def test_player_shot_history_defaults_to_empty_list() -> None:
    """A player built without ``shot_history`` has an empty list, not a required field."""
    clubs = [Club.with_expected_carry(name="7 Iron", expected_carry_metres=140.0)]

    player = Player(name="Ada", clubs=clubs)

    assert player.shot_history == []


def test_player_shot_history_accepts_constructed_shot_records_and_preserves_order() -> None:
    """``Player.shot_history`` preserves the given list order."""
    clubs = [Club.with_expected_carry(name="7 Iron", expected_carry_metres=140.0)]
    shot_history = [
        ShotRecord(club_name="7 Iron", final_downrange_metres=138.0, lateral_offset_metres=-2.0),
        ShotRecord(club_name="7 Iron", final_downrange_metres=141.0, lateral_offset_metres=1.5),
        ShotRecord(club_name="7 Iron", final_downrange_metres=144.0, lateral_offset_metres=0.0),
    ]

    player = Player(name="Ada", clubs=clubs, shot_history=shot_history)

    assert player.shot_history == shot_history


def test_player_shot_history_coerces_nested_dicts_into_shot_records() -> None:
    """Nested dicts for ``shot_history`` entries are coerced into real ``ShotRecord`` models."""
    clubs = [Club.with_expected_carry(name="7 Iron", expected_carry_metres=140.0)]

    player = Player(
        name="Ada",
        clubs=clubs,
        shot_history=[
            {"club_name": "7 Iron", "final_downrange_metres": 138.0, "lateral_offset_metres": -2.0}
        ],
    )

    assert isinstance(player.shot_history[0], ShotRecord)
    assert player.shot_history[0].club_name == "7 Iron"
    assert player.shot_history[0].final_downrange_metres == pytest.approx(138.0)
    assert player.shot_history[0].lateral_offset_metres == pytest.approx(-2.0)


# --- ClubCategory migration (issue #50) ----------------------------------------


def test_club_category_is_the_same_object_across_every_import_path() -> None:
    """``ClubCategory`` is one canonical enum, re-exported (not redefined) by every module."""
    assert player_package.ClubCategory is ClubCategory
    assert player_models_module.ClubCategory is ClubCategory
    assert statistics_package.ClubCategory is ClubCategory
    assert statistics_models_module.ClubCategory is ClubCategory


@pytest.mark.parametrize(
    ("category", "expected_value"),
    [
        (ClubCategory.DRIVER, "driver"),
        (ClubCategory.FAIRWAY_WOOD, "fairway_wood"),
        (ClubCategory.HYBRID, "hybrid"),
        (ClubCategory.IRON, "iron"),
        (ClubCategory.WEDGE, "wedge"),
        (ClubCategory.PUTTER, "putter"),
        (ClubCategory.OTHER, "other"),
    ],
)
def test_club_category_serialized_values_are_unchanged_by_the_migration(
    category: ClubCategory, expected_value: str
) -> None:
    """Regression guard: the migration to ``caddai.statistics`` must not change any
    member's serialized string value — existing persisted/serialized data must remain valid."""
    assert category.value == expected_value


def test_player_shot_history_independent_of_clubs() -> None:
    """``clubs`` and ``shot_history`` impose no constraints on each other.

    A populated ``clubs`` with empty ``shot_history`` and the reverse both
    construct validly — ``club_name`` on a ``ShotRecord`` is not looked up
    or cross-referenced against ``Player.clubs``.
    """
    clubs = [Club.with_expected_carry(name="7 Iron", expected_carry_metres=140.0)]
    shot_history = [
        ShotRecord(club_name="Driver", final_downrange_metres=210.0, lateral_offset_metres=5.0)
    ]

    player_with_empty_history = Player(name="Ada", clubs=clubs, shot_history=[])
    player_with_history_only = Player(name="Ada", clubs=clubs, shot_history=shot_history)

    assert player_with_empty_history.shot_history == []
    assert player_with_history_only.shot_history == shot_history
