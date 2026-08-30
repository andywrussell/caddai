# Roadmap

> Status: milestone sequencing for planned work. **M0**, **M1**, and **M2**
> are complete. Milestones are directional, not date-committed. **M4.0** and
> **M5.5** are numbered insertions (architecture/research spikes, not
> functional milestones) chosen to avoid renumbering later milestones; M4.0
> precedes the rest of M4 the same way M5.5 precedes M6, and neither implies
> a fractional level of completeness. See [docs/prfaq.md](prfaq.md) for the
> long-term product vision this sequencing works towards.
> Status: milestone sequencing for planned work. **M0**, **M1**, **M2**, and
> **M3** are complete. Milestones are directional, not date-committed.
> **M5.5** is
> a numbered insertion between M5 and M6 (an architecture/research spike,
> not a functional milestone) chosen to avoid renumbering M6–M9; it does not
> imply a fractional level of completeness. See [docs/prfaq.md](prfaq.md)
> for the long-term product vision this sequencing works towards.

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

- **M3 — Player model, clubs and shot dispersion** *(complete)*
  `player`/`statistics` subsystems: carry distribution model (M3.1, issue
  #26), directional dispersion model (M3.2, issue #27) — adopting a
  permanent lateral-offset sign convention (negative left, zero on-line,
  positive right of the intended target line, independent of handedness),
  evolving `Club`/`Player` to carry these instead of a bare scalar (M3.3,
  issue #28), club identity/category (M3.4, issue #29), a manually entered
  performance-history data model (M3.5, issue #30), a richer developer demo
  (M3.7, issue #31), finite-value hardening of `CarryDistribution`/
  `DirectionalDispersion`/`ShotRecord` (issues #38 and #43), and a
  documentation/status update (M3.8, issue #32). Player tendencies are
  represented for M3 by carry distribution + directional dispersion +
  systematic lateral bias — no separate player-tendency model. Deriving/
  fitting distributions from historical `ShotRecord` samples is explicitly
  deferred to a future round-history/learning milestone (see
  [docs/backlog.md](backlog.md)); M3 uses only manually supplied
  statistical parameters. Tracking issue: #9.

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

> Pre-mobile architecture scope has grown materially since M4 was defined
> (M5.5's runtime/offline, monitoring/evaluation, Rules-of-Golf, and now
> synthetic-validation scope). After M4 closeout, the project pauses before
> detailed M5 implementation planning to jointly reassess M5+ milestones —
> M5's golf-state/value/strategy scope, the round/decision model, the
> synthetic validation requirement above, real-world evaluation, a possible
> Rust production core, the mobile/Flutter boundary, cloud/API architecture,
> course packaging/distribution, Rules-of-Golf conformance, DevOps/release
> engineering, multi-repository structure, and agentic/multi-repo
> development-harness considerations — together, rather than planning M5 in
> isolation. This note does not restructure the milestone roadmap or assign
> final milestone numbers or repository names; it precedes, and may refine,
> the M5 planning pass described below.

- **M5 — Expected-value / expected-strokes strategy model**
  `strategy` subsystem: club/target selection driven by expected strokes and
  risk, producing a structured deterministic recommendation. The
  candidate-shot outcome/scoring information M4's simulation produces must
  be carried through in a distribution-aware form — e.g. outcome/scoring
  distribution, upside/downside probability, tail/penalty probability —
  rather than each candidate being reduced immediately to a single scalar
  expected-strokes value. Initial M5 behaviour may still rank candidates by
  expected strokes/expected-strokes-gained as its objective. Risk
  preference (e.g. a general preference for conservative play) and
  strategic situation (e.g. needing a birdie given current round state) are
  a distinct concern from the underlying player/shot probability model,
  which must not change when the strategic objective changes. The concrete
  utility/risk-preference formula, risk-aversion parameterisation, and any
  scoring-policy implementation (risk-sensitive ranking, aggressive/
  conservative preference, target-score/handicap objectives, protecting a
  score, match-play objectives) are explicitly deferred to the M5
  planning/architecture pass after M4 closes, not specified here.

  M5 planning scope must make explicit that **expected strokes** and
  **Strokes Gained** are the common value framework for evaluating a
  candidate shot's resulting golf states — not one possible objective among
  several unrelated ones. Conceptually: a golf state has an expected number
  of strokes to hole out from it; a candidate shot produces a distribution
  of resulting golf states; for each resulting state, strokes gained =
  (expected strokes from the current state) − (1 stroke taken + expected
  strokes from the resulting state). A candidate shot therefore has both an
  expected Strokes Gained value and a distribution of possible Strokes
  Gained outcomes. Consistent with the distribution-aware requirement
  above, CaddAI must not collapse a candidate shot to a single scalar
  expected-Strokes-Gained value — the full probabilistic outcome
  distribution must remain available for risk-sensitive and goal-sensitive
  decisions. No expected-strokes model, data source, or formula
  implementation is specified here; this is value-framework naming, not a
  specification.

  Strokes Gained matters because it gives CaddAI one common value scale for
  comparing golf actions and resulting states that would otherwise be hard
  to compare directly — tee shots, approaches, recovery shots, short game,
  and (once supported) putting — supporting, over time: ranking candidate
  shots; explaining a recommendation's value; comparing a golfer's actual
  decision against CaddAI's recommendation; identifying where strokes are
  gained or lost; and evaluating strategy quality across different shot
  types. It also gives the distribution-aware risk/reward requirement above
  a concrete unit: conceptually, simulated candidate shot -> course-relative
  outcome -> resulting golf state -> expected-strokes model -> Strokes
  Gained distribution, from which CaddAI should eventually be able to
  reason about expected Strokes Gained, the probability of strongly
  positive outcomes, the probability of losing strokes, downside/tail risk,
  penalty/catastrophic risk, and scoring probabilities — the exact summary
  statistics are not defined here unless already required by the M5 issue.

  Highest expected Strokes Gained is an important baseline strategy
  objective, but it is not necessarily the final recommendation in every
  situation: the same candidate-shot outcome distributions may be evaluated
  under different objectives depending on strategic situation, e.g.
  maximising expected value/minimising expected strokes in normal stroke
  play; accepting a slightly lower expected Strokes Gained to materially
  reduce catastrophic risk when protecting a score; accepting greater
  downside where it materially increases the probability of a needed
  birdie/net-birdie outcome; or, in a future match-play/competition
  context, optimising probability of winning/halving the relevant contest
  rather than mean Strokes Gained alone. None of these policies are
  implemented here.

  This requires keeping three concepts conceptually separate through the M5
  planning pass: (1) the **physical outcome model** (`PlayerShotDistribution`,
  environment, course geometry, hazards/terrain), unchanged by any of this;
  (2) the **value model** (expected strokes, Strokes Gained); and (3) the
  **strategic objective** (gross/net scoring context, handicap strokes,
  Stroke Index, round state, risk preference, competition objective —
  elaborated immediately below). Course Rating, Slope Rating, and Stroke
  Index must not alter intrinsic shot physics or `PlayerShotDistribution`;
  they may change what outcome is strategically desirable, never how the
  ball actually flies. The intended conceptual M5+ pipeline is: candidate
  shot -> probabilistic shot outcomes -> course-relative classification ->
  resulting golf states -> expected-strokes model -> Strokes Gained
  distribution -> expected value + upside/downside/tail information + WHS/
  round scoring context + risk/strategic objective -> recommendation. No
  concrete implementation types are locked in by this description.

  M5 planning scope must also explicitly cover World Handicap System
  (WHS)-aware scoring context: a golfer's strategic objective can depend on
  Handicap Index, selected tee set, tee-specific Course Rating and Slope
  Rating, hole par, Stroke Index/handicap-stroke allocation, and the
  golfer's current gross/net scoring position in the round — not only
  physical shot risk and expected strokes. This is a distinct concern that
  must layer on top of, and must never contaminate, the underlying physical
  shot-outcome probability model (`PlayerShotDistribution`, club, distance,
  lie, course geometry, hazards, environment, terrain/rollout): Course
  Rating, Slope Rating, and Stroke Index are handicap/scoring-context
  inputs to the strategy objective, not physical-difficulty inputs, and
  must never directly alter intrinsic shot dispersion or physics. Stroke
  Index in particular governs handicap-stroke allocation (and therefore
  gross/net scoring context) — it is not a physical 1-18 hole-difficulty
  score; CaddAI's own simulation/course model remains the sole source of a
  hole's actual physical risk. Conceptually, this extends the
  candidate-shot -> simulated-outcome -> course-relative-outcome ->
  golf-state -> expected-strokes/scoring-distribution pipeline with an
  additional WHS/round-scoring-context input feeding the strategy
  objective, alongside risk preference and strategic situation — e.g. a
  golfer receiving a handicap stroke may treat a gross bogey as a net par;
  protecting a net score may make a conservative shot rational; needing a
  net birdie late in a round may make a higher-variance option
  strategically preferable despite worse mean expected strokes; and a
  future match-play/competition objective may optimise probability of an
  outcome rather than mean expected strokes. The M5 planning/architecture
  pass must jointly resolve, rather than design as unrelated features:
  course-relative outcome mapping, canonical course/tee-data requirements
  (at minimum: tee-set identity, tee-specific Course Rating and Slope
  Rating, and per-hole par and Stroke Index — Course Rating and Slope
  Rating are tee-specific and must not be treated as course-global
  constants), Course Rating/Slope/Stroke Index representation, a
  handicap/scoring-domain boundary for WHS-derived arithmetic (Course
  Handicap/Playing Handicap calculations, including any jurisdiction-
  specific handling, e.g. GB&I/Scotland) kept separate from `strategy`'s
  deterministic decision logic, the definition of a golf "state" for
  expected-strokes purposes, the expected-strokes model and its data
  source, Strokes Gained semantics, how resulting-state uncertainty becomes
  a Strokes Gained distribution, treatment of penalties/OB/hazards in that
  model, putting/state coverage limitations, risk/reward summary metrics,
  the expected-Strokes-Gained baseline strategy objective, goal-sensitive/
  risk-sensitive ranking on top of it, distribution-aware risk/reward
  evaluation, goal-sensitive strategy objectives, gross vs. net scoring
  semantics, how round state changes recommendation utility, and the
  course-data requirements needed to support these calculations. No WHS
  formula, Course Handicap/Playing Handicap arithmetic, expected-strokes
  table, Strokes Gained calculation, course-state classification, putting
  model, risk utility, round-state logic, or course/tee data ingestion is
  specified or implemented here — this is a planning-scope note only.

  This distribution-aware requirement (candidates carry expected Strokes
  Gained, upside/downside, and tail/penalty information rather than a
  single collapsed scalar) is also what future recommendation-evaluation
  work (see [decision-journal.md](decision-journal.md)) will need to
  consume — M5 does not need additional scope to satisfy this, only to
  preserve it.

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
  framework, database, or cloud provider. Scope also includes the
  cross-cutting monitoring/evaluation requirement below: define
  cross-component event contracts (recommendation, decision, outcome) and
  the local storage/sync boundary for them; decide repository/service
  ownership; design model/config versioning (course data, player model,
  strategy/config, expected-strokes/Strokes Gained model) needed to
  interpret a decision-time snapshot later. Additionally, and kept
  conceptually separate per [decision-journal.md](decision-journal.md#monitoring-vs-evaluation):
  determine the operational-observability architecture (is
  infrastructure/application behaviour healthy — metrics/logs/traces/
  alerts). Separately, determine the evaluation-data architecture (are
  CaddAI's predictions/recommendations good — analytics datasets,
  calibration analysis, Strokes Gained analysis, experiment comparison).
  These two need not share a service or repository. Scope also includes a
  pre-mobile-MVP Rules-of-Golf/competition-conformance review of
  environmental assistance: whether wind information/measurement, elevation
  or slope adjustment, effective-playing-distance adjustment, club
  recommendations, and recommended target/line of play are permissible
  under the Rules of Golf and any applicable Local Rules (including
  distance-measuring-device restrictions), and how casual/practice and
  rules-conforming modes should differ as a result — disabling one
  environmental input (e.g. wind) must not be assumed sufficient on its
  own to make a mode rules-conforming.

  Scope also includes an **offline synthetic round/scenario validation
  harness** requirement: before broad mobile/on-course field testing (M7,
  M10) begins, CaddAI should have a repeatable, deterministic offline
  validation capability that runs large numbers of synthetic golf rounds
  — configuration-driven synthetic golfer profiles (using the same
  `PlayerShotDistribution`/`player`/`statistics` contracts as production,
  not hard-coded personas) playing real/representative canonical CaddAI
  course geometry (toy fixtures remain fine for targeted unit tests) — by
  invoking the actual production `strategy`/`simulation` engine through its
  existing public interface, never a separate mock/reimplemented strategy
  engine. This is intended to bridge unit/integration tests and real
  golfer field testing (M10), answering questions such as: does CaddAI
  always produce a valid recommendation or an explicit unsupported/
  fallback result; does strategy behave sensibly across golfer abilities;
  are risk/reward recommendations internally coherent; do recommendation
  changes between engine versions look intentional; can pathological
  scenarios (extreme crosswind, severe Student-t tails, negative downrange
  samples, very wide dispersion, missing/incomplete course geometry,
  PUTTER/full-shot boundary cases) crash the engine or produce silently
  invalid advice; and are strategy invariants preserved across many
  decisions. Illustrative, not exhaustive — full design is deferred to
  this checkpoint — validation should span at least three complementary
  classes: **hard validity/invariants** that should never be violated
  (e.g. NaN/inf in an evaluation, a recommendation referencing a club the
  golfer doesn't own, a numerically invalid target/course coordinate, an
  engine crash on a valid scenario, or an unsupported shot regime silently
  treated as supported); **scenario/strategy sanity** (controlled
  scenarios with an expected qualitative behaviour — e.g. a forced carry
  the golfer cannot realistically make should not be preferred, a simple
  unobstructed par-3 should generally target a sensible approach region,
  increasing hazard exposure should not mysteriously decrease predicted
  downside — without prescribing an exact club answer for every scenario);
  and **statistical/policy regression** (comparing engine versions over
  large deterministic scenario sets — e.g. percentage of recommendations
  changed, expected-Strokes-Gained delta, penalty/hazard exposure,
  distribution of recommended risk, invalid-recommendation count,
  fallback/unsupported rate — without fixing pass/fail thresholds now).
  Metamorphic/property-based scenarios (e.g. increasing headwind should
  not increase expected carry from the same shot; increasing player
  dispersion should not reduce symmetric hazard exposure; reducing golfer
  carry should not make a long forced carry more attractive) may be
  particularly valuable given golf recommendations rarely have one single
  exact correct answer, but concrete invariants remain future design work,
  not specified here. Every validation run should ultimately be
  reproducible given the same scenario-set, course-package, player/
  profile, CaddAI-core, strategy/config, environment-config, and
  expected-strokes/Strokes-Gained model versions plus random seed — M4.8's
  explicit `np.random.Generator`-based seeded sampling contract (no global
  RNG state) is what makes this possible, and is essential for regression
  debugging. This synthetic validation is explicitly distinct from the
  MVP monitoring/evaluation architecture above: it is controlled,
  reproducible, high-volume, and supports counterfactual scenarios,
  whereas real-world evaluation (decision journal, M6/M7) uses real
  golfers, real execution, and real conditions and remains essential for
  calibration and product validation — neither replaces the other, and
  synthetic run data must not flow into production telemetry by default.
  A future pre-mobile release criterion may require this synthetic
  validation suite to pass — e.g. zero hard-invariant failures, no
  crashes, only known/accepted behavioural deltas, and statistically
  sensible calibration/regression summaries — before broad mobile/field
  testing proceeds, though no numeric thresholds are fixed here. If a
  future Rust production core (informed by this spike) later replaces the
  Python engine, this same harness — and the current Python
  implementation retained as a reference — should support differential/
  parity validation via language-neutral golden scenarios, reference
  outputs, and deterministic seeds, distinguishing exact deterministic
  parity, numerical-tolerance parity, statistical/distributional parity,
  and strategic/semantic parity as appropriate; not all behaviour requires
  bit-for-bit parity, and this is not designed here. This checkpoint must
  also decide: whether the harness becomes a separate `caddai-sim`
  repository/component, part of a future `caddai-evals` repository, or
  another clearly separated testing/research/integration component (not
  decided now); where synthetic validation fits in CI/CD — e.g. fast
  repo-local tests on a normal PR, a broader synthetic regression suite
  for integration/release-candidate branches, and large scenario matrices
  only on a scheduled/nightly/manual basis (not decided now, and large-
  scenario runs must not become a mandatory PR check without evidence that
  runtime/cost make that practical); and, if CaddAI later moves to
  multiple repositories, how this harness participates as a
  cross-repository integration gate (repository ownership, how agents
  trigger validation, how failures are associated with the responsible
  repository/change, whether it becomes a release gate, and how
  deterministic scenario definitions are versioned — not designed now).
  The one property this checkpoint does not get to change: the harness
  must invoke the real production engine through a stable contract and
  must never duplicate or reimplement `strategy`/`simulation` decision
  logic — this is [ADR 0001](adr/0001-deterministic-strategy-engine.md)'s
  testability rationale applied at scale, not a change to it.

- **M6 — Round tracking and decision journal**
  Recording situation, recommendation, rationale, player decision, shot
  outcome, resulting lie/position (see
  [decision-journal.md](decision-journal.md)). No storage technology
  selected yet — requires an ADR when this milestone starts. Recording a
  decision/outcome is active-round core functionality (`AGENTS.md` §2.2): the
  write path must work locally; any remote sync of round history is
  connectivity-enhanced, not a prerequisite. The decision journal is the
  primary data source for **recommendation evaluation** (is a
  recommendation actually good — decision-time candidate snapshots,
  counterfactual candidate retention, probabilistic calibration, realised
  Strokes Gained), a distinct concern from **operational monitoring** (is
  the system behaving correctly); see
  [decision-journal.md](decision-journal.md#monitoring-vs-evaluation) for
  the full framing and the non-goals that remain unspecified here.

- **M7 — GPS/mobile application integration**
  Live GPS position feeding the engine; mobile/UI integration. Requires
  human decision on target platform (`AGENTS.md` escalation rules). Builds
  on the M5.5 research spike's findings; positioning must remain an
  active-round core capability per `AGENTS.md` §2.2 regardless of platform.
  Broad mobile/on-course field testing under this milestone is expected to
  be preceded by the M5.5 offline synthetic validation checkpoint passing,
  not run instead of it. Scope also includes an MVP level of
  monitoring/evaluation instrumentation building on M6's decision journal:
  local event capture during a round,
  lightweight (occasional/post-round, not per-shot) issue reporting with
  automatically associated recommendation context, and optional post-round
  sync/export — enough to evaluate pilot use, not a full analytics or
  calibration platform (deferred to post-MVP work; see
  [decision-journal.md](decision-journal.md#intended-uses) for the
  candidate MVP evaluation scorecard).

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
  real, on-course rounds before any dedicated hardware is designed, after
  the M5.5 offline synthetic validation checkpoint has passed. Field
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
