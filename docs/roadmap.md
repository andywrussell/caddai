# Roadmap

> Status: milestone sequencing for planned work. **M0** and **M1** are
> complete. Milestones are directional, not date-committed.

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
  `course`/`gps` subsystems: holes, fairways, greens, hazards, landing areas,
  distance calculations, local GeoJSON parsing.

- **M3 — Player model, clubs and shot dispersion**
  `player`/`statistics` subsystems: players, clubs, carry distributions,
  directional bias, performance history.

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
