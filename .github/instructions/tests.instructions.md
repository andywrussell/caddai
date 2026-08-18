---
applyTo: "tests/**/*.py"
---

# Test conventions

- Write behaviour-based tests: assert on observable inputs/outputs and
  invariants, not on internal implementation details. A test should still
  pass after a valid internal refactor.
- Cover boundary and edge cases explicitly: empty inputs, zero/negative
  distances, extreme wind or elevation values, degenerate geometry (zero-area
  polygons, coincident points), out-of-range GPS coordinates.
- Cover invalid input: tests must show what happens when data violates domain
  assumptions (e.g. negative carry distance, malformed GeoJSON) — reject or
  handle it explicitly, don't silently accept nonsense.
- Every bug fix ships with a regression test that fails before the fix and
  passes after it. Reference the bug/issue in the test name or docstring.
- Tests must be deterministic. When a stochastic algorithm (Monte Carlo
  simulation, dispersion sampling) is introduced, tests must fix and record an
  explicit random seed so failures are reproducible.
- Do not write tests that merely instantiate an object or call a function
  with no meaningful assertion. Every test asserts something a reader would
  care about if it broke.
- Enforce architecture invariants with tests where practical (for example, a
  test that `caddai.strategy` and `caddai.simulation` modules do not import
  `caddai.llm`, `caddai.api`, `caddai.cli`, or UI packages).
- Prefer plain `assert` with pytest; use `pytest.raises` for expected error
  paths and `pytest.approx` for floating-point comparisons.
