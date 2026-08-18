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

from caddai.strategy.demo import build_demo_request, main
from caddai.strategy.recommend import recommend_club


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
