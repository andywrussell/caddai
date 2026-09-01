# Roadmap

> Status: milestone sequencing for planned work. **M0**–**M4** are
> complete. Milestones are directional, not date-committed. **M4.0** is a
> numbered insertion (an architecture/research spike, not a functional
> milestone) chosen to avoid renumbering the rest of M4; it precedes the
> rest of M4 without implying a fractional level of completeness. After
> M4's closeout (M4.9, issue #57), the project deliberately paused before
> detailed M5 implementation planning began, and jointly reassessed M5+
> scope rather than planning M5 in isolation — see
> [docs/plans/post-m4-roadmap-reassessment.plan.md](plans/post-m4-roadmap-reassessment.plan.md)
> for the approved analysis this M5+ structure implements. That pause is
> now resolved: **M5–M14** below reflect the human-approved outcome, with
> one subsequent narrow ordering/naming amendment (M9 reframed as
> "field-readiness", and M11–M13 reordered so mobile real-round
> validation precedes optional LLM/on-device-inference enrichment — see
> the note immediately before M9 below). The
> previous **M5.5** entry ("Runtime & Offline Architecture") never had a
> GitHub milestone of its own and is **superseded** — its scope is now
> split across **M6** (production runtime & architecture checkpoint), **M7**
> (offline course package architecture), and **M9** (field-readiness
> validation, evaluation & Rules-of-Golf gate) below, per the
> dependency/decision-timing analysis in the reassessment. See
> [docs/prfaq.md](prfaq.md) for the long-term product vision this sequencing
> works towards.

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
  before the rest of M4 is detailed or implemented, the same way M5's own
  expected-strokes research spike must be resolved via an explicit
  decision gate before its implementation begins.
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
  *(complete)*
  Built on M4.0's conclusions. `player`/`statistics`/`simulation`
  subsystems, covering four concerns kept clearly separate: (1)
  **population/player modelling** — what shots a golfer of a given ability
  is likely to produce, evidence-based per M4.0 (M4.1 `PlayerShotDistribution`,
  issue #49; M4.2 `PopulationPrior`, issue #50); (2) **personalisation** —
  how a golfer's onboarding information (handicap, self-reported carry,
  shot shape, common miss) transforms the population model into an initial
  per-golfer model (M4.3, issue #51), with population assumptions
  progressively yielding influence to observed `ShotRecord` data (M4.4
  provenance/quality fields, issue #52) as sufficient high-quality personal
  history accumulates via a batch partial-pooling update (M4.5, issue #53,
  composed onto `Club`/`Player` by M4.6, issue #54); (3)
  **context/environment** — a deterministic wind/elevation/air-density
  transform of a forward-modelled shot outcome (M4.7, issue #55); and (4)
  **shot-outcome simulation** — seeded bivariate Student-t intrinsic
  outcome sampling (M4.8, issue #56) behind a pluggable
  `ShotOutcomeSampler` contract, so the model is not locked to one
  probability distribution and deterministic seeded testing remains
  possible. Candidate-shot generation for a given situation, and
  expected-value/expected-strokes optimisation/shot-target selection,
  remain M5. Closed out (M4.9, issue #57): ADR 0006/ADR 0007 accepted and
  verified against implementation; see
  [player-model.md](player-model.md), [strategy-engine.md](strategy-engine.md),
  and [architecture.md](architecture.md#m4-forward-shot-production-pipeline)
  for the final pipeline, and [docs/backlog.md](backlog.md) for what
  remains explicitly deferred (severe-miss mixture, lateral skew,
  lie-specific multipliers, a learned/ML population prior, and other
  items). Tracking issues: #10 (parent), #57 (closeout).

> **Post-M4 checkpoint (resolved).** Pre-mobile architecture scope grew
> materially since M4 was defined (the old M5.5 entry's runtime/offline,
> monitoring/evaluation, Rules-of-Golf, and synthetic-validation scope).
> After M4 closeout, the project deliberately paused before detailed M5
> implementation planning began and jointly reassessed M5+ scope rather
> than planning M5 in isolation — see
> [docs/plans/post-m4-roadmap-reassessment.plan.md](plans/post-m4-roadmap-reassessment.plan.md)
> for the full capability/dependency analysis and the human decisions that
> resolved it. That reassessment considered together: M5's
> golf-state/value/strategy scope; the round/decision-journal model; the
> offline synthetic round/scenario validation harness requirement;
> real-world recommendation-evaluation and operational-monitoring
> architecture; a possible future Rust production-core direction; the
> mobile boundary; offline course-package architecture; Rules-of-Golf
> conformance; DevOps/release engineering; and agentic/multi-repository
> development-harness considerations. A separate deep-research report,
> [docs/research/agentic-development-multi-repo-devops.md](research/agentic-development-multi-repo-devops.md),
> remains **research input only** — it is **not** an accepted CaddAI
> architecture decision, and none of its candidate technology choices
> (e.g. a `caddai-product` split, Protobuf, a C ABI, PyO3, Copilot CLI
> orchestration, or a specific agentic-workflow tool) are adopted by this
> roadmap; any such choice requires its own future ADR and human approval
> (`AGENTS.md` §13). **M5–M14 below are the resolved outcome of that
> reassessment.** The previous M5.5 entry never had a GitHub milestone of
> its own and is **superseded**: its scope is now split across M6
> (production runtime & architecture checkpoint), M7 (offline course
> package architecture), and M9 (field-readiness validation, evaluation &
> Rules-of-Golf gate) below. This resolution is
> itself documentation/roadmap-structure only — it does not constitute
> detailed M5 implementation planning, which remains a separate, later
> task.
>
> **Subsequent narrow amendment (still pre-M5-implementation, still
> documentation-only).** M9 was originally named "pre-mobile validation"
> and M13 was "mobile real-round validation prototype", which implied M9
> blocked M10's build and that mobile real-round validation was a distant,
> lower-priority afterthought behind optional LLM/on-device-inference
> work. Both were corrected before merge: **M9** is renamed
> "field-readiness validation, evaluation & Rules-of-Golf gate" and
> explicitly does **not** block M10's implementation (`M9 + M10 -> gate
> M11`, run in parallel where genuinely independent); **M10** is reframed
> as a build/integration milestone only ("Mobile MVP implementation"),
> not proof of real-round performance; the mobile real-round validation
> capability moves from M13 to **M11**, immediately after the mobile MVP
> build, gated by both M9 and M10; and the LLM (M12) and on-device
> inference research (M13) milestones move down to sit after real-round
> validation, preserving "golf engine decides, LLM explains" but now also
> "prove it works for real before enriching it." Hardware research (M14)
> is unaffected in substance beyond its gate now naming M11 instead of
> M13. No dependency, WHS, expected-strokes, `GolfState`, runtime-timing,
> or synthetic-validation decision already approved earlier in this
> reassessment was reopened by this amendment.

- **M5 — Course-relative golf state & expected-value strategy**
  `strategy`/`simulation` subsystems: the first milestone that turns M4's
  probabilistic, carry-space `ShotOutcome` into a structured, trustworthy
  deterministic recommendation. Tracking issue: #11 (rewritten scope).

  **1. Course-relative outcome classification.** Classify a simulated
  landing/final position (M4.8) against existing `course` polygon/boundary
  geometry (M2, ADR 0003/0004) into a minimal set of course-relative states
  — fairway, rough, bunker, green, water, out-of-bounds, other penalty
  area, and a recovery/unknown-lie fallback. This composition logic reads
  `course` geometry and `simulation`'s `ShotOutcome`; it does not belong
  inside `course` itself (`course` owns geometry only, never shot-outcome
  semantics). A real rollout/bounce physics model is explicitly **not**
  required for V1 — a deliberately simple, clearly-labelled-as-approximate
  deterministic adjustment (e.g. a fixed or lie/club-conditioned offset
  applied before classification) is sufficient; `ShotOutcome`/`ShotRecord`
  already model a *final* resting position for this reason.

  **2. Minimal `GolfState`.** A stable, deliberately minimal golf-state
  representation (position, distance/geometry context, lie/surface,
  penalty context, hole/round context only) that expected strokes, Strokes
  Gained, and later the round model and synthetic validation harness can
  all operate on. This must **not** grow into a full round/product model
  here — round lifecycle, persistence, and full scoring history are M8's
  concern, sequenced deliberately after M5. **`GolfState`'s canonical
  owning module and dependency direction are an explicit open question for
  M5's own first design task** — not decided by this roadmap document, and
  not defaulted to `simulation` merely because it is a plausible-sounding
  candidate. `GolfState` will potentially be consumed by course-relative
  mapping, expected strokes, `strategy`, the round model (M8), the
  synthetic validation harness (M9), the decision journal (M8), and
  scoring, so its ownership must be deliberately resolved with Architect
  input, which should also weigh that [architecture.md](architecture.md)'s
  existing target dependency diagram already shows `simulation -> course`,
  so placing `GolfState` in `simulation` would not itself introduce a new
  dependency edge — this observation informs, but does not pre-decide,
  that design task. If that design work concludes a new foundational
  module or dependency direction is needed, the Architect must explicitly
  assess whether an ADR is required at that time.

  **3. Expected strokes — research spike, then a decision gate, then
  implementation (not one continuous step).** No expected-strokes data
  source, model, or formula exists in any CaddAI documentation today; this
  is the single highest-uncertainty item on the path to a trustworthy
  recommendation. A scoped evidence/research spike — mirroring M4.0's
  format and rigour — must survey existing public expected-strokes/
  strokes-gained research (not only tour-level data; amateur/handicap-
  golfer baselines are the more relevant transfer question), what is
  usable/licensable, and what a defensible, explicitly-provisional V1
  approximation looks like, without assuming any proprietary
  strokes-gained dataset (e.g. ShotLink) is available. **An explicit
  human/model decision gate sits between the spike and implementation —
  they are not one automatically continuous step**, because the spike's
  findings may materially change the intended V1 implementation approach.
  Concretely: the implementation sub-issue for expected-strokes must not
  be opened until the spike's findings have been reviewed and explicitly
  accepted, the same way M4.0 gated the rest of M4. The concrete
  expected-strokes interface this eventually produces is a likely future
  ADR trigger (a new public contract other subsystems depend on, mirroring
  ADR 0007's `PopulationPrior` replaceability precedent) at implementation
  time, not created by this roadmap entry.

  **4. Strokes Gained / distribution-aware candidate evaluation.** Once a
  golf state has an expected-strokes value, a candidate shot's resulting
  golf states yield a Strokes Gained distribution: strokes gained =
  (expected strokes from the current state) − (1 stroke taken + expected
  strokes from the resulting state). Strokes Gained is CaddAI's common
  value framework for comparing golf actions and resulting states — tee
  shots, approaches, recovery shots, short game, and (once supported)
  putting — not one possible objective among several unrelated ones. A
  candidate shot must **not** be collapsed to a single scalar expected-
  Strokes-Gained value: the full probabilistic outcome distribution
  (upside probability, downside/tail risk, penalty/catastrophic
  probability, scoring probabilities) must remain available for
  risk-sensitive and goal-sensitive decisions layered on top later, and
  for the future recommendation-evaluation work in
  [decision-journal.md](decision-journal.md), which needs this same
  distribution-aware shape.

  **5. Baseline expected-value strategy & recommendation.** Assemble the
  first structured, trustworthy `strategy` recommendation: club/target
  selection that maximises expected Strokes Gained as its baseline
  objective. Risk preference (e.g. a general preference for conservative
  play) and goal-sensitive/strategic-situation objectives (e.g. needing a
  birdie given current round state, protecting a score, a future
  match-play objective) are a distinct, separable concern layered on top
  of this baseline — they must not change the underlying player/shot
  probability model, and are not implemented here.

  **What this milestone deliberately keeps separate:** (1) the **physical
  outcome model** (`PlayerShotDistribution`, environment, course geometry,
  hazards/terrain) — unchanged by any of this; (2) the **value model**
  (expected strokes, Strokes Gained); and (3) the **strategic objective**
  (risk preference, goal/scoring context) — never contaminating (1).

  **WHS data-shape requirements (pulled forward; hybrid decision).** M5/
  course-package work should account for tee-specific WHS-relevant **data
  shape** now — tee-set identity, par, tee-specific Course Rating,
  tee-specific Slope Rating, and per-hole Stroke Index — since course-data
  requirements and course-relative classification are being designed
  together anyway, and Course Rating/Slope Rating are tee-specific, never
  course-global constants. Course Rating, Slope Rating, and Stroke Index
  remain handicap/scoring-context data, **never** physical-difficulty
  inputs — CaddAI's own simulation/course model remains the sole source of
  actual physical risk, and none of this data may alter intrinsic shot
  dispersion or physics. **WHS scoring *policy*** — Course Handicap/
  Playing Handicap arithmetic, gross/net strategic objectives, and
  handicap-aware "protect my score" policy — is explicitly **deferred to
  M8** (round tracking & decision journal), once a baseline expected-value
  recommendation exists and live round/scoring state is available; only
  the policy layer waits, not the underlying course/tee data shape.

  **What this milestone is not:** general M5 implementation planning
  beyond this scope note, a production-runtime decision (M6), a full
  round/product model (M8), or WHS scoring-policy implementation (M8).

- **M6 — Production runtime & cross-language architecture checkpoint
  (research/architecture spike)**
  Architecture/decision milestone, not a large implementation effort.
  Follows the approved runtime-timing principle: implement enough M5
  domain/value semantics to establish a meaningful Python reference
  implementation first, then perform this production-runtime/mobile
  architecture decision, before undertaking substantial round/mobile/
  product implementation that would otherwise create immediate rewrite
  risk (see M8, sequenced after this milestone for exactly that reason).
  Scope: whether/when a non-Python production core (e.g. Rust) is
  justified for mobile packaging, performance, or battery reasons, and if
  so what parity tiers apply (exact deterministic parity, numerical-
  tolerance parity, statistical/distributional parity, strategic/semantic
  parity — not all behaviour requires bit-for-bit parity); the mobile/core
  runtime boundary; the Python-reference/parity strategy for validating
  any future non-Python core against it (built on M9's synthetic
  validation harness); contracts/cross-language boundaries if a second
  language is introduced; a repository-architecture decision point (only
  if a second language/runtime or mobile app codebase genuinely forces a
  split — avoid architecture by symmetry); a DevOps/release-architecture
  decision point; and the point at which a multi-repository
  agentic-development architecture (informed by, but not adopting,
  [docs/research/agentic-development-multi-repo-devops.md](research/agentic-development-multi-repo-devops.md))
  would first become relevant. This milestone also includes a throwaway/
  PoC-grade mobile runtime vertical slice proving the chosen approach
  works end-to-end on a real device with a trivial recommendation request
  — not the mobile MVP itself (M10). Rust must not become authoritative
  before a parity harness (M9) proves equivalence against the Python
  reference for real scenarios — this milestone decides *whether/when*,
  never assumes it. No mobile framework, runtime language, database, or
  cloud provider is selected by this roadmap entry; each remains its own
  future ADR/human-approval decision (`AGENTS.md` §13/§14). Tracking
  issue: #74 (supersedes part of the old M5.5 entry).

- **M7 — Offline course package architecture**
  Architecture/platform milestone, transitioning from today's fixture-only
  local GeoJSON course model (M2) to a usable offline production course
  package. At minimum, where appropriate: geometry; tee sets; par;
  tee-specific Stroke Index, Course Rating, and Slope Rating (consistent
  with M5's WHS data-shape requirement); a manifest/versioning format;
  attribution/licensing metadata; and local storage/cache/update
  semantics, consistent with the offline-first active-round principle
  (`AGENTS.md` §2.2) — course-package download/update is
  connectivity-enhanced, never a prerequisite for in-round course geometry
  access. No commercial course-data provider is selected here. Tracking
  issue: #75 (supersedes part of the old M5.5 entry).

- **M8 — Round tracking, decision journal & WHS scoring-policy layer**
  `strategy`/round-lifecycle scope, deliberately sequenced **after** M6's
  runtime checkpoint: building a full round/decision-journal model is
  exactly the kind of substantial Python product implementation the
  approved runtime-timing principle says should wait for the runtime
  decision, to avoid rewriting it under a future non-Python core. Records
  situation, recommendation, rationale, player decision, shot outcome, and
  resulting lie/position/state (see
  [decision-journal.md](decision-journal.md)): round lifecycle, selected-
  vs-recommended shot, decision-journal record, `ShotRecord` linkage,
  resulting state, and local/offline event capture. Recording a decision/
  outcome is active-round core functionality (`AGENTS.md` §2.2): the write
  path must work locally; any remote sync of round history is
  connectivity-enhanced. No storage technology is selected yet — requires
  an ADR when this milestone starts (database/infrastructure selection is
  an escalation trigger). Tracking issue: #12 (rewritten scope).

  **WHS scoring-policy layer.** M5 deferred WHS *scoring policy* (as
  opposed to the *data shape* it already carries) here because the
  round-progress-sensitive parts of that policy — protecting a score,
  needing a net birdie late in a round — genuinely need live, cumulative
  round/scoring state that only exists once round tracking does; the
  simpler, static Course Handicap/Playing Handicap arithmetic could in
  principle be built as soon as M5/M7's player/tee data exists, but is
  kept in this same milestone rather than split across two, since it is
  one coherent objective layer and splitting it for marginal benefit would
  risk the physical/value/objective separation being implemented
  piecemeal. Official WHS-derived calculations (Course Handicap, Playing
  Handicap, any jurisdiction-specific handling, e.g. GB&I/Scotland) live
  behind a clear handicap/scoring-domain boundary, separate from
  `strategy`'s deterministic decision logic, and never alter intrinsic
  shot dispersion or physics.

- **M9 — Field-readiness validation, evaluation & Rules-of-Golf gate**
  Validation milestone gating **M11** (mobile real-round validation) —
  together with M10 — not gating M10's *implementation* itself:
  `M9 + M10 -> gate M11`. M9's validation work may proceed in parallel
  with M10's build; do not read "field-readiness" as "pre-mobile" in the
  sense of blocking mobile development — it is pre-*field-exposure*, not
  pre-*build*. Bundles three workstreams that belong in the same
  pre-field-exposure validation category but must remain **distinctly
  tracked sub-issues**, not one undifferentiated task — mirroring how
  M4.1–M4.9 stayed distinct sub-issues under one milestone number:

  1. **Synthetic validation harness.** A repeatable, deterministic offline
     validation capability that runs large numbers of synthetic golf
     rounds — configuration-driven synthetic golfer profiles using the
     same `PlayerShotDistribution`/`player`/`statistics` contracts as
     production (not hard-coded personas) — by invoking the actual
     production `strategy`/`simulation` engine through its existing public
     interface, never a separate mock/reimplemented engine (this is ADR
     0001's testability rationale applied at scale, not a change to it).
     Can begin against existing M2 course fixtures once M5 lands; should
     be extended to real/representative canonical course geometry as M7's
     packages become available, rather than waiting for M7 to start.
     Spans at least: **hard validity/invariants** (no NaN/inf in an
     evaluation, no recommendation referencing a club the golfer doesn't
     own, no numerically invalid target/course coordinate, no crash on a
     valid scenario, no unsupported shot regime silently treated as
     supported); **scenario/strategy sanity** (controlled scenarios with
     an expected qualitative behaviour, without prescribing an exact club
     answer for every scenario); and **statistical/policy regression**
     (comparing engine versions over large deterministic scenario sets —
     recommendation-change rate, expected-Strokes-Gained delta, hazard
     exposure, risk distribution, invalid-recommendation count, fallback/
     unsupported rate — without fixing pass/fail thresholds now).
     Metamorphic/property-based scenarios (e.g. increasing headwind should
     not increase expected carry; increasing dispersion should not reduce
     symmetric hazard exposure; reducing carry should not make a long
     forced carry more attractive) are particularly valuable given golf
     recommendations rarely have one single correct answer. Every
     validation run must be reproducible given the same scenario-set,
     course-package, player profile, CaddAI-core, strategy/config,
     environment-config, and expected-strokes/Strokes-Gained model
     versions plus random seed (M4.8's seeded `np.random.Generator`
     contract is what makes this possible). This harness must invoke the
     real production engine through a stable contract and must never
     duplicate or reimplement `strategy`/`simulation` decision logic. If a
     future Rust production core (M6) later replaces the Python engine,
     this same harness — with the Python implementation retained as a
     reference — supports differential/parity validation via language-
     neutral golden scenarios and deterministic seeds. Deferred/open
     (not decided now): whether the harness becomes a separate repository/
     component and its CI/DevOps placement (feeds M6's repository-
     architecture decision point if a split occurs).
  2. **Monitoring/evaluation architecture**, keeping two concerns
     architecturally distinct (see
     [decision-journal.md](decision-journal.md#monitoring-vs-evaluation)):
     **operational observability** (is infrastructure/application behaviour
     healthy — metrics/logs/traces/alerts) and **recommendation/model
     evaluation** (are CaddAI's predictions/recommendations good —
     decision-time candidate data, recommendation, golfer choice, outcome,
     resulting state/value, model/config versions, calibration, issue
     reporting). These two need not share a service or repository. An MVP
     level is local event capture during a round plus lightweight,
     occasional (not per-shot) issue reporting with automatically
     associated recommendation context — enough to evaluate pilot use, not
     a full analytics/calibration platform (post-MVP, see backlog). Depends
     on M5's candidate-evaluation shape and M8's decision/outcome shape;
     event contracts must not be designed before those shapes exist in
     code.
  3. **Rules-of-Golf/competition-conformance review**: whether wind
     information/measurement, elevation/slope adjustment, effective-
     playing-distance adjustment, club recommendations, and recommended
     target/line of play are permissible under the Rules of Golf and any
     applicable Local Rules (including distance-measuring-device
     restrictions), and how casual/practice vs. rules-conforming modes
     should differ as a result — disabling one environmental input (e.g.
     wind) must not be assumed sufficient on its own to make a mode
     rules-conforming. This is a documentation/policy review only, no rule
     policy is implemented here, and it has **no technical blocking
     dependency** on the other two workstreams above or on M6/M7/M8 — it
     may be completed opportunistically at any point once M5 lands, even
     before this milestone formally opens; it is grouped here because it
     is a pre-field-exposure validation/product gate, not because it
     depends on anything else in this milestone.

  A future release criterion may require the synthetic validation suite
  to show zero hard-invariant failures, no crashes, and only known/
  accepted behavioural deltas before broad real-round field testing (M11)
  proceeds — no numeric thresholds are fixed here. Tracking issue: #76
  (supersedes part of the old M5.5 entry).

- **M10 — Mobile MVP implementation**
  Live GPS position feeding the engine; mobile/UI integration; full
  offline round: GPS, offline course package (M7), local engine,
  recommendation, decision recording (M8). Requires a human decision on
  target platform (`AGENTS.md` escalation rules). Builds on M6's runtime
  checkpoint (and its PoC vertical slice) and M7's course-package
  architecture; positioning must remain an active-round core capability
  per `AGENTS.md` §2.2 regardless of platform. **This milestone is a
  build/integration milestone, not proof that CaddAI performs well on
  real golf rounds.** Its exit condition is approximately: a complete
  offline mobile application can execute a representative round
  end-to-end in controlled/integration conditions using the production
  core, local course data, round lifecycle, and local decision/event
  capture. **Broad** real-round field validation is a distinct, later
  milestone (M11), explicitly gated by **both** this milestone's
  completion **and** M9's field-readiness validation passing —
  `M9 + M10 -> gate M11`. Building this MVP itself is **not** gated by
  M9, and M9's validation work may proceed in parallel with this
  milestone's implementation. Includes an MVP level of monitoring/
  evaluation instrumentation building on M8's decision journal and M9's
  event-contract design: local event capture during a round, lightweight
  post-round issue reporting, and optional post-round sync/export.
  Tracking issue: #13 (rewritten scope).

- **M11 — Mobile real-round validation**
  Validation milestone — **not** a second mobile build. Takes the
  completed M10 mobile MVP into real, on-course rounds to answer: does
  the completed offline mobile CaddAI system behave coherently and
  provide trustworthy value during real golf rounds? Explicitly gated by
  **both** M9 (field-readiness validation passing) and M10 (mobile MVP
  implementation complete) — `M9 + M10 -> gate M11`. Run on existing
  consumer mobile devices per M6's runtime findings — no dedicated
  hardware. Scope: controlled pilot rounds; recommendation acceptance/
  override observation; offline reliability; course-data failures; GPS/
  product usability; predicted-vs-observed outcomes where available;
  recommendation-quality evidence; user-reported bad recommendations; and
  evaluation of whether the product is ready for broader use. Field
  validates the deterministic recommendation and offline-first
  active-round behaviour (`AGENTS.md` §2.2) under real conditions (real
  GPS signal quality, real battery drain, real between-shot workflow).
  Its findings — not assumptions made now — are the evidence base for
  whether an LLM explanation layer (M12) is worth pursuing next, and for
  whether dedicated hardware (M14) is worth building, and for that
  milestone's actual sensor, compute, UX, latency, and battery
  requirements. Tracking issue: #78 (new).

- **M12 — LLM caddie communication layer**
  An LLM explains the deterministic recommendation in natural, caddie-style
  language. Deliberately sequenced **after M11's real-round validation**:
  the core deterministic engine must be proven correct and trustworthy in
  real rounds — not only in controlled/integration conditions — before any
  natural-language layer is added on top of it — see
  [adr/0001-deterministic-strategy-engine.md](adr/0001-deterministic-strategy-engine.md).
  Requires human approval to select an LLM provider. If the LLM is
  cloud-based, unreachability must degrade to the structured deterministic
  recommendation, never withhold a recommendation (`AGENTS.md` §2.2, see
  [ADR 0005](adr/0005-offline-first-active-round-architecture.md)). Tracking
  issue: #14 (renumbered, previously M11).

- **M13 — On-device inference research**
  Exploratory research into on-device inference for the M12 explanation
  layer (not the decision engine). Not committed scope. The offline-first
  active-round principle (`AGENTS.md` §2.2) does not require pulling this
  forward: a cloud-only M12 that degrades gracefully to the structured
  recommendation when unreachable already satisfies that principle.
  Tracking issue: #15 (renumbered, previously M12).

- **M14 — Hardware / on-device intelligence research**
  Exploratory research into dedicated CaddAI hardware and on-device
  sensing, deliberately sequenced after M11: dedicated hardware must not be
  committed to until M11's mobile real-round validation has been used in
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
  This milestone remains **roadmap-only** (no GitHub milestone/issue) —
  the same deliberate convention every version of this roadmap has applied
  to hardware research, since it stays a distant, non-actionable research
  placeholder until M11 findings exist; unlike M11, nothing new here
  changes its actionability.

LLM integration is deliberately kept until after real-round validation: the
deterministic engine must be proven correct and trustworthy on real rounds
before any natural-language layer is added on top of it. Dedicated hardware
is deliberately kept later still — not committed to until M11's mobile
real-round validation has proven the experience holds up in real rounds.
