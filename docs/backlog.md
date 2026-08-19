# Backlog

> Status: candidate work items and open questions beyond the current
> milestone. Not a commitment or a schedule — see [roadmap.md](roadmap.md)
> for sequencing. Items move here when identified but not yet scheduled.

## Candidate items

- Derive/fit `CarryDistribution`/`DirectionalDispersion` from historical
  `ShotRecord` samples (deferred out of M3 — see #9/#30; M3 uses only
  manually supplied statistical parameters; likely lands around the
  round-history/learning milestone, M6+).
- Player-level strategic tendencies (risk preference, aggressiveness) as a
  distinct model, beyond club-level carry distribution/dispersion/bias
  (deferred out of M3; belongs to later strategy/player-preference work).
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
- Add regression test coverage for a line-of-play exactly overlapping a
  polygon boundary edge in `caddai.course.distance` (feeds M2 follow-up).
- Add regression test coverage directly targeting `caddai.course.distance`'s
  `1e-6` m Shapely precision-snap boundary itself (feeds M2 follow-up).

## Process

- The Orchestrator adds items here when work is identified as valuable but
  out of scope for the current task, per
  `docs/development-workflow.md`.
- Items are promoted out of the backlog into a `docs/plans/` implementation
  plan only when a human confirms the milestone should start.
