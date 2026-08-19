# Roadmap

> Status: milestone sequencing for planned work. **M0**, **M1**, and **M2**
> are complete. Milestones are directional, not date-committed. **M5.5** is
> a numbered insertion between M5 and M6 (an architecture/research spike,
> not a functional milestone) chosen to avoid renumbering M6–M9; it does not
> imply a fractional level of completeness.

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

- **M5.5 — Runtime & Offline Architecture (research spike)**
  Architecture/research milestone, not implementation. Once `strategy`/
  `simulation` are mature enough to benchmark (post-M5), evaluate how to
  satisfy the offline-first active-round principle (`AGENTS.md` §2.2, see
  [ADR 0005](adr/0005-offline-first-active-round-architecture.md)) for a
  real mobile deployment, before committing to a full mobile runtime
  architecture (M7). Scope: mobile runtime options; whether/how the Python
  CaddAI core can execute locally on-device; packaging/embedding Python on
  mobile; whether native/Rust/C++ components are needed for performance or
  packaging; local persistence options (feeds the M6 decision-journal
  storage ADR); a course-package format for locally cached course data;
  offline/online synchronisation strategy; where cloud API boundaries sit
  for connectivity-enhanced features; authentication approach; computational
  requirements (CPU/memory usage, shot-simulation latency, battery
  implications); local/on-device LLM feasibility (informs M9); and expected
  system behaviour when connectivity is lost mid-round. Findings should
  produce the specific ADRs later milestones need (M6 storage, M7 mobile
  runtime, M9 on-device inference) rather than making those technology
  choices itself — this spike deliberately does not select a mobile
  framework, database, or cloud provider.

- **M6 — Round tracking and decision journal**
  Recording situation, recommendation, rationale, player decision, shot
  outcome, resulting lie/position (see
  [decision-journal.md](decision-journal.md)). No storage technology
  selected yet — requires an ADR when this milestone starts. Recording a
  decision/outcome is active-round core functionality (`AGENTS.md` §2.2): the
  write path must work locally; any remote sync of round history is
  connectivity-enhanced, not a prerequisite.

- **M7 — GPS/mobile application integration**
  Live GPS position feeding the engine; mobile/UI integration. Requires
  human decision on target platform (`AGENTS.md` escalation rules). Builds
  on the M5.5 research spike's findings; positioning must remain an
  active-round core capability per `AGENTS.md` §2.2 regardless of platform.

- **M8 — LLM caddie communication layer**
  An LLM explains the deterministic recommendation in natural, caddie-style
  language. Deliberately last among functional milestones — see
  [adr/0001-deterministic-strategy-engine.md](adr/0001-deterministic-strategy-engine.md).
  Requires human approval to select an LLM provider. If the LLM is
  cloud-based, unreachability must degrade to the structured deterministic
  recommendation, never withhold a recommendation (`AGENTS.md` §2.2, see
  [ADR 0005](adr/0005-offline-first-active-round-architecture.md)).

- **M9 — On-device inference research**
  Exploratory research into on-device inference for the M8 explanation
  layer (not the decision engine). Not committed scope. The offline-first
  active-round principle (`AGENTS.md` §2.2) does not require pulling this
  forward: a cloud-only M8 that degrades gracefully to the structured
  recommendation when unreachable already satisfies that principle.

- **M10 — Mobile software prototype (real-round validation)**
  A software-only mobile prototype, built on the M7 GPS/mobile integration
  (and, if landed, the M8 LLM explanation layer), run on existing consumer
  mobile devices per the M5.5 research spike's runtime findings — no
  dedicated hardware. Purpose: prove CaddAI can actually be used during
  real, on-course rounds before any dedicated hardware is designed. Field
  validates the deterministic recommendation and offline-first active-round
  behaviour (`AGENTS.md` §2.2) under real conditions (real GPS signal
  quality, real battery drain, real between-shot workflow). Its findings —
  not assumptions made now — are the evidence base for whether dedicated
  hardware (M11) is worth building, and for that milestone's actual sensor,
  compute, UX, latency, and battery requirements.

- **M11 — Hardware / on-device intelligence research**
  Exploratory research into dedicated CaddAI hardware and on-device
  sensing, deliberately sequenced after M10: dedicated hardware must not be
  committed to until the M10 mobile software prototype has been used in
  real rounds and its actual sensor, compute, UX, latency, and battery
  requirements are understood from that experience. Candidate hardware
  inputs include camera-based lie assessment, GNSS location,
  elevation/barometric data, IMU, compass, other environmental sensors, and
  microphone/voice input. Any hardware/sensor system explored here must
  produce canonical CaddAI domain inputs, never golf strategy logic of its
  own — e.g. camera/manual input -> `Lie`, GNSS -> `Position`,
  barometer/course data -> elevation, weather/manual/sensor -> `Wind` —
  leaving the deterministic `strategy`/`simulation` engine ([ADR
  0001](adr/0001-deterministic-strategy-engine.md)) as the sole source of
  golf decisions. Not committed scope; a real hardware/sensor adapter
  design is the trigger for a future ADR (or ADR 0001 amendment) naming
  hardware/sensor input adapters as a module category, per `AGENTS.md` §13.

LLM integration is deliberately kept late: the deterministic engine must be
correct and trustworthy on its own before any natural-language layer is
added on top of it. Dedicated hardware is deliberately kept later still —
not committed to until the M10 mobile software prototype has proven the
experience holds up in real rounds.
