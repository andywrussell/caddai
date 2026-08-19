# Roadmap

> Status: milestone sequencing for planned work. **M0**, **M1**, and **M2**
> are complete. Milestones are directional, not date-committed.

- **M0 — Agent development platform and repository foundation** *(complete)*
  Repository structure, documentation set, VS Code multi-agent development
  team, quality gates, `uv`-managed `pyproject.toml`, minimal `caddai`
  package skeleton. No golf logic.

- **M1 — Core golf domain model and simple deterministic recommendation
  vertical slice** *(complete)*
  Minimal domain types (`Player`/`Club` in `caddai.player`; `Wind`/`LieType`/
  `RecommendationRequest`/`RecommendationResult` in `caddai.strategy`) and a
  single trivial end-to-end deterministic recommendation path
  (`recommend_club`), to prove the architecture works before building
  subsystem depth. See
  [docs/plans/m1-core-domain-vertical-slice.plan.md](plans/m1-core-domain-vertical-slice.plan.md).
  A follow-up developer tooling addition (M1.1, issue #16) added a runnable
  demo command, `uv run python -m caddai.strategy.demo`, exercising this
  path end to end.

- **M2 — Course geometry and local GeoJSON course representation**
  *(complete)*
  `course`/`gps` subsystems: GPS coordinate and great-circle primitives
  (M2.1, issue #3), course-local planar projection (M2.2, issue #4, see
  [ADR 0002](adr/0002-gps-local-projection-without-shapely.md)),
  course/hole/feature domain models (M2.3, issue #5), GeoJSON fixture
  parsing (M2.4, issue #6), polygon/boundary geometry (M2.4.5, issue #22,
  see [ADR 0003](adr/0003-course-boundary-geometry.md)), and
  point-to-feature distance queries (M2.5, issue #7, see
  [ADR 0004](adr/0004-distance-query-local-frame.md)). Full subsystem
  design, data format, and known limitations:
  [docs/course-engine.md](course-engine.md).

- **M3 — Player model, clubs and shot dispersion**
  `player`/`statistics` subsystems: carry distribution model (M3.1, issue
  #26), directional dispersion model (M3.2, issue #27) — adopting a
  permanent lateral-offset sign convention (negative left, zero on-line,
  positive right of the intended target line, independent of handedness),
  evolving `Club`/`Player` to carry these instead of a bare scalar (M3.3,
  issue #28), club identity/category (M3.4, issue #29), a manually entered
  performance-history data model (M3.5, issue #30), a richer developer demo
  (M3.7, issue #31), and a documentation/status update (M3.8, issue #32).
  Player tendencies are represented for M3 by carry distribution +
  directional dispersion + systematic lateral bias — no separate
  player-tendency model. Deriving/fitting distributions from historical
  `ShotRecord` samples is explicitly deferred to a future round-history/
  learning milestone (see [docs/backlog.md](backlog.md)); M3 uses only
  manually supplied statistical parameters. Tracking issue: #9.

- **M4 — Candidate-shot generation and Monte Carlo simulation**
  `simulation` subsystem: shot candidate generation, seeded Monte Carlo
  outcome simulation against course + player models.

- **M5 — Expected-value / expected-strokes strategy model**
  `strategy` subsystem: club/target selection driven by expected strokes and
  risk, producing a structured deterministic recommendation.

- **M6 — Round tracking and decision journal**
  Recording situation, recommendation, rationale, player decision, shot
  outcome, resulting lie/position (see
  [decision-journal.md](decision-journal.md)). No storage technology
  selected yet — requires an ADR when this milestone starts.

- **M7 — GPS/mobile application integration**
  Live GPS position feeding the engine; mobile/UI integration. Requires
  human decision on target platform (`AGENTS.md` escalation rules).

- **M8 — LLM caddie communication layer**
  An LLM explains the deterministic recommendation in natural, caddie-style
  language. Deliberately last among functional milestones — see
  [adr/0001-deterministic-strategy-engine.md](adr/0001-deterministic-strategy-engine.md).
  Requires human approval to select an LLM provider.

- **M9 — On-device inference research**
  Exploratory research into on-device inference for the M8 explanation
  layer (not the decision engine). Not committed scope.

LLM integration is deliberately kept late: the deterministic engine must be
correct and trustworthy on its own before any natural-language layer is
added on top of it.
