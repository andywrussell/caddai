"""Tests for the developer recommendation demo in ``caddai.strategy.demo``.

See GitHub issue #16 ("M1.1 — Add developer recommendation demo") for the
acceptance criteria these tests are derived from.

These tests assume `demo.py` exposes:

- `build_demo_request() -> RecommendationRequest` — builds the fixed,
  deterministic demo scenario (no randomness, no interactive input).
- `main() -> None` — calls the real `recommend_club()` on that scenario and
  prints a human-readable recommendation to stdout.

If the Strategy Engineer chooses different names, this file's imports must
be updated to match (see the QA report for this assumption).
"""

import re

import pytest

from caddai.player import Club, ClubCategory, Player
from caddai.statistics import CarryDistribution, DirectionalDispersion
from caddai.strategy.demo import build_demo_request, main
from caddai.strategy.models import LieType, RecommendationRequest, Wind, WindDirection
from caddai.strategy.recommend import recommend_club

_PLAYER_MODEL_CONTEXT_HEADER = "Player-model context"


def _lines_matching(output: str, *keywords: str) -> list[str]:
    """Return output lines that contain every keyword (case-insensitive)."""
    lowered_keywords = [keyword.lower() for keyword in keywords]
    return [
        line
        for line in output.splitlines()
        if all(keyword in line.lower() for keyword in lowered_keywords)
    ]


def _decimals_in(lines: list[str]) -> list[float]:
    """Extract every signed decimal number found across the given lines."""
    return [float(match) for line in lines for match in re.findall(r"-?\d+\.\d+", line)]


def _player_model_context_text(output: str) -> str:
    """Return only the output text after the "Player-model context" header.

    Scoping M3.7 assertions to this remainder ensures a test can only pass
    because of the new player-model-context section, not because of a
    coincidental substring match in pre-existing output (e.g. the club name
    line or the `Reasons:` text).
    """
    _, separator, remainder = output.partition(_PLAYER_MODEL_CONTEXT_HEADER)
    assert separator, "Expected output to contain a 'Player-model context' header"
    return remainder


def test_build_demo_request_is_deterministic() -> None:
    """The fixed demo scenario must be identical across calls: no randomness, no input."""
    first = build_demo_request()
    second = build_demo_request()

    assert first == second


def test_main_produces_non_empty_output(capsys: pytest.CaptureFixture[str]) -> None:
    """Baseline smoke test: running the demo must produce non-empty stdout output."""
    main()

    output = capsys.readouterr().out

    assert output.strip() != ""


def test_main_prints_the_club_selected_by_the_real_recommend_club(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The printed club name must match what the real recommend_club() selects for the scenario."""
    expected = recommend_club(build_demo_request())

    main()

    output = capsys.readouterr().out

    assert expected.selected_club.name in output


def test_main_prints_a_playing_distance_matching_the_real_recommend_club(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The printed playing distance must match the real computed value, not a hardcoded figure."""
    expected = recommend_club(build_demo_request())

    main()

    output = capsys.readouterr().out
    printed_decimals = [float(match) for match in re.findall(r"-?\d+\.\d+", output)]

    assert any(
        value == pytest.approx(expected.playing_distance_metres, abs=0.05)
        for value in printed_decimals
    )


def test_main_prints_a_confidence_matching_the_real_recommend_club(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The printed confidence must match the real value, shown as a fraction or a percentage."""
    expected = recommend_club(build_demo_request())

    main()

    output = capsys.readouterr().out
    printed_decimals = [float(match) for match in re.findall(r"-?\d+\.\d+", output)]
    printed_percentages = [float(match) for match in re.findall(r"(\d+(?:\.\d+)?)\s*%", output)]

    matches_as_fraction = any(
        value == pytest.approx(expected.confidence, abs=0.01) for value in printed_decimals
    )
    matches_as_percentage = any(
        value == pytest.approx(expected.confidence * 100, abs=1.0) for value in printed_percentages
    )

    assert matches_as_fraction or matches_as_percentage


def test_main_prints_at_least_one_real_reason(capsys: pytest.CaptureFixture[str]) -> None:
    """The demo must print at least one of the real recommend_club() reasons, not invented text."""
    expected = recommend_club(build_demo_request())

    main()

    output = capsys.readouterr().out

    assert any(reason in output for reason in expected.reasons)


# ---------------------------------------------------------------------------
# M3.7 (GitHub issue #31): richer player-model context in the demo output.
#
# These tests assert against the real `Club`/`CarryDistribution`/
# `DirectionalDispersion` fields exposed via `recommend_club(build_demo_request())`,
# never hardcoded numbers. They will fail until the Strategy Engineer extends
# `demo.py`'s `main()` per docs/plans/m3.7-demo-player-model.plan.md.
#
# Label-wording assumption (flagged as ambiguity for the Strategy Engineer):
# because the exact wording of the new output lines isn't specified yet, the
# line-based matching below requires each new line to contain at least these
# keywords, so the implementation must use wording containing them:
#   - an "expected carry" line: contains "carry" but NOT "variability"/"stddev"
#   - a "carry variability" line: contains "variability" or "stddev", but NOT
#     "lateral"/"dispersion"
#   - a "lateral dispersion" line: contains "lateral" AND ("dispersion" or
#     "stddev"), but NOT "bias"
#   - a "lateral bias" line: contains "bias"
#   - sign legibility: for a negative bias, the bias line must contain "left"
#     or an explicit "-" sign; for a positive bias, it must contain "right" or
#     an explicit "+" sign (a bare unsigned number is not sufficient).
# If `demo.py` uses substantially different wording, these tests (and this
# comment) must be updated to match.
# ---------------------------------------------------------------------------


def test_main_prints_selected_club_category(capsys: pytest.CaptureFixture[str]) -> None:
    """The printed output must show the real selected club's category (issue #31)."""
    expected = recommend_club(build_demo_request())

    main()

    output = capsys.readouterr().out
    context = _player_model_context_text(output)

    assert expected.selected_club.category.value.lower() in context.lower()


def test_main_prints_expected_carry_metres_for_selected_club(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The output must show the selected club's expected_carry_metres, distinct from stddev."""
    expected = recommend_club(build_demo_request())

    main()

    output = capsys.readouterr().out
    context = _player_model_context_text(output)
    carry_lines = [
        line
        for line in _lines_matching(context, "carry")
        if "variability" not in line.lower() and "stddev" not in line.lower()
    ]
    values = _decimals_in(carry_lines)

    assert any(
        value == pytest.approx(expected.selected_club.expected_carry_metres, abs=0.05)
        for value in values
    ), "Expected a line mentioning 'carry' (not variability/stddev) with the club's expected carry"


def test_main_prints_carry_variability_matching_stddev(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The output must show the selected club's carry_distribution.stddev_metres (issue #31)."""
    expected = recommend_club(build_demo_request())

    main()

    output = capsys.readouterr().out
    context = _player_model_context_text(output)
    variability_lines = [
        line
        for line in context.splitlines()
        if ("variability" in line.lower() or "stddev" in line.lower())
        and "lateral" not in line.lower()
        and "dispersion" not in line.lower()
    ]
    values = _decimals_in(variability_lines)

    assert any(
        value == pytest.approx(expected.selected_club.carry_distribution.stddev_metres, abs=0.05)
        for value in values
    ), "Expected a carry-variability line (excl. lateral dispersion) with the club's carry stddev"


def test_main_prints_lateral_dispersion_matching_lateral_stddev(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The output must show the selected club's dispersion.lateral_stddev_metres (issue #31)."""
    expected = recommend_club(build_demo_request())

    main()

    output = capsys.readouterr().out
    context = _player_model_context_text(output)
    dispersion_lines = [
        line
        for line in context.splitlines()
        if "lateral" in line.lower()
        and ("dispersion" in line.lower() or "stddev" in line.lower())
        and "bias" not in line.lower()
    ]
    values = _decimals_in(dispersion_lines)

    assert any(
        value == pytest.approx(expected.selected_club.dispersion.lateral_stddev_metres, abs=0.05)
        for value in values
    ), "Expected a lateral-dispersion line (not the bias line) with the club's lateral stddev"


def test_main_prints_lateral_bias_value_and_legible_sign(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The output must show lateral_bias_metres with a legible left/right sign (issue #31)."""
    expected = recommend_club(build_demo_request())
    bias = expected.selected_club.dispersion.lateral_bias_metres

    main()

    output = capsys.readouterr().out
    context = _player_model_context_text(output)
    bias_lines = [line for line in context.splitlines() if "bias" in line.lower()]
    combined = " ".join(bias_lines).lower()
    values = _decimals_in(bias_lines)

    assert any(
        value == pytest.approx(bias, abs=0.05) or value == pytest.approx(abs(bias), abs=0.05)
        for value in values
    ), "Expected a 'bias' line containing the club's lateral_bias_metres value"

    if bias < 0:
        assert "left" in combined or any(
            value == pytest.approx(bias, abs=0.05) for value in values
        ), "Negative lateral_bias_metres must be legible as 'left' text or an explicit '-' sign"
    elif bias > 0:
        plus_signed = re.findall(r"\+(\d+\.\d+)", combined)
        assert "right" in combined or any(
            float(match) == pytest.approx(bias, abs=0.05) for match in plus_signed
        ), "Positive lateral_bias_metres must be legible as 'right' text or an explicit '+' sign"
    else:
        pytest.skip(
            "Selected club's lateral_bias_metres is exactly zero for this demo scenario; "
            "sign legibility is not applicable"
        )


def test_main_prints_on_line_label_for_zero_lateral_bias(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A club with an exactly-zero lateral_bias_metres must print an "on-line" label."""
    zero_bias_request = RecommendationRequest(
        player=Player(
            name="Zero Bias Golfer",
            clubs=[
                Club(
                    name="7 Iron",
                    carry_distribution=CarryDistribution(mean_metres=145.0, stddev_metres=4.5),
                    dispersion=DirectionalDispersion(
                        lateral_stddev_metres=6.0, lateral_bias_metres=0.0
                    ),
                    category=ClubCategory.IRON,
                ),
            ],
        ),
        target_distance_metres=145.0,
        wind=Wind(speed_mps=0.0, direction=WindDirection.HEADWIND),
        lie=LieType.FAIRWAY,
    )
    monkeypatch.setattr("caddai.strategy.demo.build_demo_request", lambda: zero_bias_request)

    main()

    output = capsys.readouterr().out
    context = _player_model_context_text(output)
    bias_lines = [line for line in context.splitlines() if "bias" in line.lower()]

    assert any("on-line" in line.lower() for line in bias_lines)
