# Roadmap

> Status: milestone sequencing for planned work. **M0**, **M1**, and **M2**
> are complete. Milestones are directional, not date-committed. **M4.0** and
> **M5.5** are numbered insertions (architecture/research spikes, not
> functional milestones) chosen to avoid renumbering later milestones; M4.0
> precedes the rest of M4 the same way M5.5 precedes M6, and neither implies
> a fractional level of completeness. See [docs/prfaq.md](prfaq.md) for the
> long-term product vision this sequencing works towards.

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

- **M4.0 — Research and define the CaddAI probabilistic golfer model
  (research spike)**
  Architecture/research milestone, not implementation — must be resolved
  before the rest of M4 is detailed or implemented, the same way the M5.5
  spike precedes M6 without itself being a functional milestone.
  Investigates credible existing golf research and legally usable public
  data that could support an initial CaddAI population model of the shots a
  golfer of a given ability is likely to produce, including (where evidence
  exists): the relationship between handicap/ability and shot dispersion;
  carry variability and lateral dispersion by skill level; variability by
  club/club category; systematic miss patterns and carry/lateral-miss
  correlation; frequency and magnitude of severe/outlier shots; shot-shape
  behaviour; lie, wind, and elevation/air-density/temperature effects; and
  competitive-pressure or other contextual effects. For each candidate
  factor, M4.0 must distinguish effects with good enough evidence for an
  initial model, plausible effects that should merely be represented for
  future learning, and effects deferred for weak evidence or low
  implementation value — it must not assume every listed factor should be
  implemented. It explicitly evaluates whether public/legitimately reusable
  datasets (e.g. published R&A/USGA research, academic golf-performance
  datasets, publicly available launch-monitor datasets) can fit all or part
  of an initial population model — considering available variables, sample
  size, player-ability information, clubs represented, raw-observation vs.
  aggregate-only availability, representativeness/bias, and licensing/
  permitted use — without assuming access to proprietary datasets (ShotLink,
  Arccos, Golfmetrics, commercial TrackMan data, etc.); where raw data is
  insufficient, it defines how published aggregate statistics can still
  provide evidence-based priors or fitted/interpolated relationships,
  introducing a statistical or ML population model only where justified, not
  for sophistication's own sake. It defines conceptually how onboarding
  information (handicap index, self-reported per-club carry, normal shot
  shape, common miss direction) should personalise the population model into
  an initial per-golfer model — including which properties are primarily
  golfer-reported versus population-inferred. It evaluates the initial
  probabilistic representation (independent Gaussian, correlated/
  multivariate, heavy-tailed, mixture-of-normal-and-severe-miss, empirical,
  or another appropriately simple representation) and determines whether
  M3's `CarryDistribution`/`DirectionalDispersion` remain sufficient
  primitives or a higher-level `PlayerShotDistribution` abstraction is
  needed — if adopted, it must live in `player`/`statistics` (consumed by
  `simulation`), preserving the existing dependency direction. It defines
  the future-compatible mechanism (Bayesian updating, hierarchical/empirical
  Bayes, shrinkage, robust incremental statistics — evaluated conceptually,
  not implemented here) by which population priors progressively yield to
  observed `ShotRecord` data as personal history accumulates, so that
  `simulation` ultimately depends on a `PlayerShotDistribution`-style
  contract regardless of whether its parameters came from population
  priors, onboarding, statistical personalisation, or a future ML model, and
  determines whether implementing that learning mechanism belongs in M4 or
  a later milestone. It separates human shot-production uncertainty from
  environmental transformation, preferring deterministic/physical modelling
  for effects (e.g. wind, elevation, air density) that are adequately
  understood physically over learning an opaque relationship without
  sufficient data; competitive pressure must not receive an arbitrary
  generic penalty unless research supports a defensible implementation. Any
  distributional-modelling library beyond NumPy/Pydantic (e.g. `scipy`)
  identified as necessary is a new-dependency decision requiring an ADR and
  human approval (`AGENTS.md` §9/§13), not assumed here. Any selected
  population-model data must resolve to locally embeddable parameters,
  never a runtime network dependency on the active-round critical path
  (`AGENTS.md` §2.2). Findings feed a separate future task that creates the
  detailed M4 implementation backlog; adopting a new shared `player`/
  `statistics` abstraction or a new dependency identified here requires its
  own ADR before M4 implementation begins. Tracking issue: #10 (title/scope
  to be updated to M4.0/M4 once this redefinition is merged).

- **M4 — Probabilistic golfer modelling & shot outcome simulation**
  Builds on M4.0's conclusions. `player`/`statistics`/`simulation`
  subsystems, covering four concerns kept clearly separate: (1)
  **population/player modelling** — what shots a golfer of a given ability
  is likely to produce, evidence-based per M4.0; (2) **personalisation** —
  how a golfer's onboarding information (handicap, self-reported carry,
  shot shape, common miss) transforms the population model into an initial
  per-golfer model, with population assumptions progressively yielding
  influence to observed `ShotRecord` data as sufficient high-quality
  personal history accumulates; (3) **context/environment** — how lie,
  wind, and elevation transform a player's shot-production uncertainty into
  a resulting outcome distribution; and (4) **shot-outcome simulation** —
  generating possible outcomes for a candidate shot from the resulting
  model. Seeded Monte Carlo remains an acceptable initial sampling
  technique for (4), but it is not the domain abstraction: the model must
  not be locked to one probability distribution, deterministic seeded
  testing must remain possible, and future simulation/evaluation techniques
  must be able to operate on the same player shot model. Candidate-shot
  generation for a given situation remains part of this subsystem grouping.
  Expected-value/expected-strokes optimisation and shot/target selection
  remain M5, unchanged in purpose — M4 provides the probabilistic outcomes
  that strategy layer consumes. Detailed M4 implementation issues are
  deliberately not created until this redefinition has been reviewed; a
  separate future Orchestrator/Architect task uses M4.0's conclusions and
  this milestone description to generate that backlog.

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
