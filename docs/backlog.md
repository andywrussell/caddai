# Backlog

> Status: candidate work items and open questions beyond the current
> milestone. Not a commitment or a schedule — see [roadmap.md](roadmap.md)
> for sequencing. Items move here when identified but not yet scheduled.

## Candidate items

- Define the GeoJSON `properties` schema for course features (feeds M2).
- Define the parametric form of carry/dispersion distributions (feeds M3).
- Decide the expected-strokes model / baseline data source used by
  `strategy` (feeds M5; likely needs an ADR if it requires external
  strokes-gained reference data).
- Decide the decision-journal storage technology (feeds M6; requires ADR +
  human approval — database selection is an escalation trigger).
- Decide the target mobile/GPS platform and integration approach (feeds M7;
  requires human decision).
- Decide the LLM provider and integration approach for the explanation layer
  (feeds M8; requires human approval — LLM provider selection is an
  escalation trigger).
- Investigate on-device inference feasibility for the M8 explanation layer
  (feeds M9; research only, not committed scope).

## Process

- The Orchestrator adds items here when work is identified as valuable but
  out of scope for the current task, per
  `docs/development-workflow.md`.
- Items are promoted out of the backlog into a `docs/plans/` implementation
  plan only when a human confirms the milestone should start.
