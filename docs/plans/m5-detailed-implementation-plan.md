# M5 — Detailed implementation plan

> Status: implementation plan. Turns the M5.0 research/design spike
> (PR #79, merged) into an executable, dependency-ordered issue tree for
> milestone M5. This document itself changes no production code, writes
> no ADR, and performs no numeric-baseline research — see
> [Non-goals](#non-goals-of-this-planning-task) below.

## Scope

This plan decomposes M5 ("Course-relative golf state & expected-value
strategy", tracking issue [#11](https://github.com/andywrussell/caddai/issues/11))
into 14 child issues (M5.1–M5.14, created as GitHub issues
[#81](https://github.com/andywrussell/caddai/issues/81)–[#94](https://github.com/andywrussell/caddai/issues/94),
native sub-issues of #11 — see the mapping table in #11's own body) across
three dependency-ordered streams, plus the explicit human decision gate
that already exists per the M5.0 spike. It reflects CaddAI Architect, QA
Engineer, and Adversarial Reviewer
input gathered while drafting this plan (see
[Review record](#review-record) below).

## Architecture decisions inherited from M5.0 (binding inputs, not re-decided here)

Recorded in
[docs/research/m5-golf-state-expected-strokes.md](../research/m5-golf-state-expected-strokes.md)
and [docs/backlog.md](../backlog.md):

1. **`GolfState` semantic architecture (approved, architecture direction
   only):** `course` owns geometry/data; a new, neutral, dependency-free
   top-level module (`caddai.golf_state`) owns player-neutral
   course-relative state semantics; `simulation` owns the mapping
   operation `ShotOutcome + shot origin + actual selected target/target
   frame + course geometry -> GolfState`; expected-strokes/value consumes
   `GolfState`; `strategy` consumes distributions of resulting values. A
   dedicated `GolfState`/course-relative-state ADR is still required
   before implementation (not yet written — this is M5.1 below).
2. **Value architecture (approved):** long-term = Architecture Option B
   (neutral `E_base(state)` + a separate, later, unscheduled
   `Delta(state, player_context)`); V0 = Architecture Option C
   (`E_player(state) = E_base(state)`, no player-adjustment layer in V0).
   Architecture Option A (single ability-conditioned function) is **not**
   selected as the long-term core value architecture.
3. **Benchmark Strokes Gained semantics (approved):** `SG_base =
   E_base(current_state) - (1 + E_base(resulting_state))`, the canonical
   benchmark-comparable quantity for the M5 baseline path.
4. **Numeric expected-strokes baseline/data source: UNRESOLVED.** This is
   a separate, still-open follow-on decision (M5.7 below). It blocks only
   the `E_base` implementation path (Stream B's implementation issues and
   everything downstream of it in Stream C) — it does **not** block
   `GolfState`/course-relative domain work (Stream A), which is
   independent and may proceed immediately and in parallel.
5. **`Delta`/player-state adjustment is future, unscheduled work** —
   already recorded in [docs/backlog.md](../backlog.md); no M5 issue
   implements it (see [Non-goals](#non-goals-of-this-m5-plan) below).

## Non-goals of this M5 plan

Per the M5 roadmap entry and the M5.0 spike, M5 does **not** cover:
player-state value adjustment (`Delta`); score-sensitive/risk-sensitive
strategic policy (e.g. handicap-aware risk, "need birdie" policy); WHS
scoring policy (Course Handicap/Playing Handicap arithmetic, gross/net
objectives — WHS **data shape** was already pulled forward at M2/M3, only
scoring *policy* is deferred, to M8); full round lifecycle/decision
journal storage; mobile integration; Rust/production-runtime architecture
(M6); production course-data packages (M7); a full synthetic validation
harness (M9); cloud services; LLM explanation (M12). Putting-shot
*physical simulation* (`ClubCategory.PUTTER`) remains deferred — M5 values
an on-green `GolfState` without simulating a putt stroke (see
[Putting boundary](#putting-boundary)).

## Non-goals of this planning task

This task creates/updates docs and GitHub issues/project fields only. It
does **not** implement `GolfState`, write the `GolfState` or
expected-strokes ADRs, perform the expected-strokes numeric-baseline
research, implement course-relative mapping, expected strokes, Strokes
Gained, or strategy, change runtime architecture, or start M6 work.

## Issue tree

All child issues are native GitHub sub-issues of parent
[#11](https://github.com/andywrussell/caddai/issues/11) and carry
`## Dependencies` / `## Blocks` sections (matching the M4 issue
convention, e.g. issue #51), milestone `M5`, and CaddAI Development
project fields (Area/Priority/Status).

### Stream A — GolfState / course-relative domain

| # | Title | Owner | Area | Priority | Status | Depends on | Blocks |
|---|---|---|---|---|---|---|---|
| M5.1 | GolfState ADR | Strategy Engineer (ADR author) + Architect review | GolfState | P0 | Ready | — | M5.2, M5.8 |
| M5.2 | GolfState domain contract implementation | Strategy Engineer | GolfState | P1 | Backlog | M5.1 | M5.5, M5.9 |
| M5.3 | Course domain support for classification | Course Engineer | Course | P1 | Ready | — | M5.5 |
| M5.4 | Course-relative coordinate transformation + rollout seam | Strategy Engineer | Simulation | P1 | Backlog | M5.1 | M5.5 |
| M5.5 | Course-relative classification + GolfState assembly | Strategy Engineer | Simulation | P1 | Backlog | M5.2, M5.3, M5.4 | M5.6, M5.11 |
| M5.6 | GolfState/course-relative mapping edge-case & invariant hardening | Strategy Engineer | Simulation | P2 | Backlog | M5.5 | M5.11 |

**M5.1 — GolfState ADR.** Writes `docs/adr/0008-*.md` (number assigned at
creation time) recording: canonical module ownership (`caddai.golf_state`,
new top-level module); the exact domain contract (fields, types, which
are required vs derivable-but-stored); terminal/holed representation
(explicit bool, never inferred from distance proximity); lie/surface
representation (closed category set, explicit `UNKNOWN`/recovery
fallback, never silently `FAIRWAY`); penalty-state representation
(explicit bool/enum, never a magic distance value); stable course/hole
identity/reference semantics (an identifier, not an embedded mutable
`Course`/`Hole` graph); dependency direction (`simulation -> golf_state`,
`simulation -> course`, `simulation -> gps`, future `strategy ->
golf_state`); interaction with `course` (geometry-only, never imported by
`golf_state`), `simulation` (the mapping owner), expected-strokes/value
(a consumer, never the reverse), and `strategy` (a consumer); M6
portability considerations (a plain, dependency-free, scalar/categorical
value type, not an embedded provider/geometry object); test/invariant
expectations (the domain invariants already catalogued in the M5.0
research document's section D); and an explicit `AGENTS.md` §4
module-ownership decision for `caddai.golf_state` (recorded conclusion:
Strategy Engineer, who already owns `simulation`/`strategy` and is the
natural owner of this consumer-breadth-spanning type — decided here, not
silently implied). Must preserve `GolfState`'s player-neutrality: no
player identity, handicap, risk preference, round score, WHS policy, or
strategic goal. **Deliverable: an accepted ADR document + an `AGENTS.md`
§4 edit recording the new module's owner. No production code.**

**M5.2 — GolfState domain contract implementation.** Implements the new
`caddai.golf_state` module per ADR 0008: a frozen Pydantic model with the
fields/invariants the ADR records (finite/non-negative distances; a
closed lie/surface category enum with an explicit `UNKNOWN` member;
explicit penalty and terminal/holed boolean fields; a position field; a
selected-target/aim-frame reference field, preserved as given, never
reinterpreted; a stable course/hole geometry reference identifier). Its
`caddai.*` dependency list is **exactly what ADR 0008 specifies** (likely
zero, but may reuse `caddai.gps.models.Coordinate` if the ADR decides
that's the correct way to avoid duplicating a coordinate type — not
pre-asserted as zero by this issue). Adds a new `SubsystemBoundary` entry
for `golf_state` to `tests/test_architecture_boundaries.py`.

**M5.3 — Course domain support for classification.** Adds `ROUGH` and a
generic `PENALTY_AREA` `FeatureType` to `caddai.course.models` (today's
enum has neither — see the M5.0 research document's "Current-state
audit"); adds a point-in-polygon containment primitive to `caddai.course`
(Shapely-backed — Shapely is already an approved dependency already used
by `course`); extends `tests/fixtures/sample_course.geojson` (or adds a
purpose-built fixture) with a rough/fallback polygon, a deliberately
overlapping/adjacent polygon pair, a point positioned exactly on a
boundary edge, and a concave polygon. Independent of `GolfState`/ADR
work — **no blockers, can start immediately in parallel with M5.1/M5.2.**

**M5.4 — Course-relative coordinate transformation + rollout seam.**
Implements, in `caddai.simulation`: (1) the deterministic transform
`ShotOutcome + shot origin + actual selected target -> resulting
position`, reusing `gps.projection`'s tangent-plane convention anchored
at the shot origin (ADR 0002/0004 precedent), metres-canonical,
deterministic, honouring whatever target was actually used (never
substituting the pin/green-centre/CaddAI's own recommendation); tested
via a concrete reflected-frame property (the same classified result under
a mirrored coordinate frame, not merely an unverifiable "handedness
independent" claim); and (2) a distinct, separately-named, swappable
rollout/final-position function applied before classification — a coarse
deterministic offset **if** defensible parameters exist, otherwise an
explicit identity/no-rollout transform, either way carrying a visible
`rollout_model_version`-style provenance marker so it is never presented
as a validated physics model. Adds `caddai.gps` and `caddai.course` to
`simulation`'s allow-list in `tests/test_architecture_boundaries.py` (this
issue is the first to need them — moved here from M5.5 per Architect
review, so M5.4's own code can pass the boundary test without waiting on
M5.5).

**M5.5 — Course-relative classification + GolfState assembly.** Consumes
M5.2 (`GolfState` contract), M5.3 (`FeatureType`/containment primitive),
and M5.4 (resulting position) to implement `simulation`'s full mapping
function producing a `GolfState`. Covers: explicit, deterministic
precedence rules for overlapping/duplicate course features (never
"whichever feature happens to be checked first"); an explicit, documented
boundary-edge convention (Shapely `covers` vs `contains`) for a point
exactly on a polygon edge; the explicit `UNKNOWN`/recovery fallback for
any point outside every mapped feature (never silently `FAIRWAY`); target
override support (classification works against any candidate target, not
only an accepted/recommended one). Adds `caddai.golf_state` to
`simulation`'s allow-list in `tests/test_architecture_boundaries.py` (the
one remaining edge M5.4 doesn't need).

**M5.6 — GolfState/course-relative mapping edge-case & invariant
hardening.** Scoped specifically (narrowed from M5.5, per QA review, to
avoid duplicate test-ownership) to: extreme/heavy-tailed M4 Student-t
outcomes landing far outside any mapped course feature (must fall back to
`UNKNOWN` gracefully, never raise an unhandled exception); fixture-driven
regression tests exercising M5.3's new fixtures (the overlapping-polygon
pair, the boundary-edge point, the concave polygon) end-to-end through the
full M5.5 mapping function, not just at the primitive level.

### Stream B — Expected-strokes baseline

| # | Title | Owner | Area | Priority | Status | Depends on | Blocks |
|---|---|---|---|---|---|---|---|
| M5.7 | Expected-strokes numeric-baseline/data-source research | Strategy Engineer (research) | Simulation | P0 | Ready | — | M5.8 |
| M5.8 | Expected-strokes interface & value-model ADR | Strategy Engineer (ADR author) + Architect review | Simulation | P1 | Backlog (blocked) | M5.1, M5.7 (human decision) | M5.9 |
| M5.9 | Baseline expected-strokes (`E_base`) implementation + batch evaluation | Strategy Engineer | Simulation | P1 | Backlog (blocked) | M5.2, M5.8 | M5.10 |
| M5.10 | Expected-strokes edge-case & invariant hardening | Strategy Engineer | Simulation | P2 | Backlog | M5.9 | M5.11 |

**M5.7 — Expected-strokes numeric-baseline/data-source research.**
Bounded research issue (mirrors M4.0/M5.0's format). Question: *what
defensible numeric `E_base(GolfState)` can CaddAI legally and technically
ship for V0?* Compares at least: a reusable/open numeric source; values
legally derivable from published methodology/data; an explicitly
provisional CaddAI-authored baseline; a licensed source; another
defensible model/source. Must cover distance/lie state support,
putting/on-green values, penalty/recovery treatment, golfer population
represented, numeric provenance, licensing/redistribution,
interpolation/extrapolation, monotonicity, unsupported states, offline
embedding, and future replaceability. **Must end in a literal `HUMAN
DECISION REQUIRED` block** — no expected-strokes implementation issue may
be opened for real work until that decision is recorded. **Deliverable: a
research document only. No code, no ADR.** No blockers — independent of
Stream A, may run in parallel from day one.

**M5.8 — Expected-strokes interface & value-model ADR.** Records the
`baseline_expected_strokes(state) -> value` interface (input/output
semantics, model/version provenance field, batch API shape, deterministic-
behaviour requirement, explicit unsupported-state signal — never a silent
default, interpolation/extrapolation policy, replaceability mirroring ADR
0007's precedent, dependency direction with no dependency on
`player`/`statistics`/`strategy`); and **decides the owning module** for
`E_base`/the future `CandidateValueDistribution` type (candidates:
`caddai.simulation`, extending its existing scope, vs. a new neutral value
module — an ownership question this plan does not pre-decide, matching
how M5.0 left `GolfState`'s ownership to its own ADR). **Blocked: must not
begin real ADR-drafting work until M5.7's `HUMAN DECISION REQUIRED` is
resolved** (Status stays `Backlog`, not `Ready`, until then) — also depends
on M5.1 (the `GolfState` ADR text, not its code) for the state shape it
consumes.

**M5.9 — Baseline expected-strokes (`E_base`) implementation + batch
evaluation.** Implements ADR 0008/0009's interface: a NumPy-array-friendly
batch path plus a scalar convenience wrapper; a terminal/holed state
short-circuits to exactly `0` via the explicit flag (never via
distance-proximity inference); provisional numeric content carries a
visible version/provenance marker; deterministic (same input + same model
version -> same output, always). **Scoped explicitly to whichever branch
M5.7's `HUMAN DECISION REQUIRED` actually resolves to** — most plausibly,
per the verified evidence in the M5.0 research document, "an explicitly
provisional CaddAI-authored approximation," but this issue does not
pre-assume that outcome; if M5.7 instead resolves to a licensed/derived
source, this issue's scope is revisited before work begins. **Blocked on
M5.8**, which is itself blocked on M5.7's decision — the same "not `Ready`
until the gate clears" rule applies transitively.

**M5.10 — Expected-strokes edge-case & invariant hardening.** Covers: an
unsupported/unknown state produces an explicit signal (e.g. a
`nan`/masked-array entry or an explicit exception path), never a silently
defaulted numeric value that could pollute a downstream mean; interpolation/
extrapolation boundary behaviour (both within-range and beyond the most
extreme observed distance); batch-vs-scalar equivalence (identical results
either way); and the penalty-stroke counting convention (does a penalty
outcome's expected-strokes value already reflect the drop/replay position,
and does the SG formula's "+1" correctly represent one shot taken, not an
extra penalty stroke) resolved **explicitly as an `E_base`/`SG_base`
modelling choice**, not as an implementation of Rules-of-Golf penalty
procedure generally (that remains M9's Rules-of-Golf gate) — flagged
explicitly so this issue cannot silently grow into Rules conformance work.

### Stream C — Value / strategy composition

| # | Title | Owner | Area | Priority | Status | Depends on | Blocks |
|---|---|---|---|---|---|---|---|
| M5.11 | Benchmark Strokes Gained + candidate value distribution | Strategy Engineer | Simulation | P1 | Backlog | M5.6, M5.10 | M5.12 |
| M5.12 | Baseline expected-value strategy | Strategy Engineer | Strategy | P1 | Backlog | M5.11 | M5.13 |
| M5.13 | Structured recommendation assembly + legacy M3 transition | Strategy Engineer | Strategy | P1 | Backlog | M5.12 | M5.14 |
| M5.14 | M5 integration, demo & closeout | Strategy Engineer | Strategy | P2 | Backlog | M5.13 | — |

**M5.11 — Benchmark Strokes Gained + candidate value distribution.**
Implements `SG_base = E_base(current_state) - (1 + E_base(resulting_state))`
over a batch of simulated resulting `GolfState`s, correctly reflecting
whatever penalty-stroke-counting convention M5.10 resolved (tested, not
merely assumed); defines a `CandidateValueDistribution` type (mean SG,
tail/downside probability, penalty/hazard probability, upside probability
where meaningful, sample count, model/version provenance) that **never**
collapses to a single scalar — the full distribution must always remain
retrievable. **Must carry forward M5.10's unsupported-state safety
property into this issue's own aggregation, not merely rely on it existing
upstream**: any masked/`nan` unsupported-state entry M5.10 flags must be
excluded from `mean SG` and from the other aggregate fields, with `sample
count` reflecting only valid samples (and the excluded count separately
recoverable) — tested explicitly, so an unsupported state can never
silently pollute a candidate's mean value. Adds `caddai.simulation` and
`caddai.golf_state` (and whatever module M5.8's ADR named for `E_base`) to
`strategy`'s allow-list in `tests/test_architecture_boundaries.py` — the
first Stream C issue that needs this edge.

**M5.12 — Baseline expected-value strategy.** Selects the candidate
maximising mean benchmark `SG_base` from its `CandidateValueDistribution`.
Explicitly excludes handicap-aware risk preference, current-score/"need
birdie" strategy, competition/rules policy, and user-configured
aggression — enforced by a keyword-scan architecture test mirroring the
existing `test_simulation_contains_no_rules_of_golf_policy_identifiers`
pattern.

**M5.13 — Structured recommendation assembly + legacy M3 transition.**
Adds a **new** probabilistic recommendation entry point in `strategy`,
distinct from the existing `recommend_club()` — which **remains callable
and unchanged in M5** (see
[Legacy deterministic strategy transition](#legacy-deterministic-strategy-transition)
below). Recommendation fields: recommended club, recommended target,
candidate identity, expected benchmark SG/value, a risk/penalty summary,
model/config/version provenance references, and an unsupported/fallback
reason where applicable. The risk/penalty summary is **presentational
only** — a test asserts its fields are copied unchanged from the selected
candidate's `CandidateValueDistribution` (an equality/copy test), with no
new risk computation introduced here. Demo/tests exercise both the legacy
and new entry points side by side so the two are visibly distinguishable.

**M5.14 — M5 integration, demo & closeout.** An end-to-end demo script
exercising the full pipeline (`PlayerShotDistribution -> simulated
ShotOutcomes -> resulting GolfStates -> E_base -> SG_base ->
CandidateValueDistribution -> baseline strategy selection -> structured
recommendation`) on a fixed, seeded scenario; documentation status updates
to `roadmap.md`/`architecture.md`/`strategy-engine.md` marking M5's scope
complete, **accurately describing whatever M5.7 actually decided** — if
M5.7 resolved to an explicitly-provisional CaddAI-authored baseline (the
most plausible outcome per the verified evidence), the docs must say so
plainly and never present it as validated data; if M5.7 instead resolved
to a licensed/derived source, the docs must describe *that* provenance
accurately instead — this issue must not hard-code an assumed outcome
ahead of M5.7's actual decision, mirroring the same hedge already applied
in M5.9 and the [M5 exit criteria](#m5-exit-criteria) section; full
quality-gate confirmation (`ruff format --check`, `ruff check`, `mypy
src`, `pytest` all green); a short M6-handoff readiness note (see
[M6 handoff](#m6-handoff) below).

## Dependency graph

```
M5.1 (GolfState ADR) ------------------------------------\
    |-> M5.2 (GolfState contract) --------------------\    \
    |                                                   \    \
    |-> M5.4 (transform + rollout) -----\                \    \
                                          \                \    \
M5.3 (course support, independent) -------+--> M5.5 (classification + assembly)
                                                    |                \
                                                    v                 \  (M5.1 also feeds M5.8; M5.2 also feeds M5.9 — cross-stream edges, not a Stream A/B independence)
                                          M5.6 (edge-case hardening) -----\      \
                                                                            \     \
M5.7 (expected-strokes research) --[HUMAN DECISION]--> M5.8 (interface/ADR) <-----+
    (independent, no blockers)                          |      ^
                                                          v      \-- also depends on M5.1
                                          M5.9 (E_base impl) <-- also depends on M5.2
                                                          |
                                                          v
                                                   M5.10 (hardening)
                                                                            \    |
                                                                             v   v
                                                                    M5.11 (SG_base + CandidateValueDistribution)
                                                                             |
                                                                             v
                                                                    M5.12 (baseline EV strategy)
                                                                             |
                                                                             v
                                                                    M5.13 (recommendation + legacy transition)
                                                                             |
                                                                             v
                                                                    M5.14 (integration, demo, closeout)
```

**Independent, immediately startable in parallel:** M5.1 (GolfState ADR),
M5.3 (course support), M5.7 (expected-strokes research) — none of these
three has any blocker. **Correction (flagged by Adversarial Review): this
does not mean Stream A and Stream B are independent all the way to
M5.11.** Stream B's *implementation* issues depend on Stream A directly:
M5.8 depends on M5.1 (the `GolfState` ADR text) as well as M5.7's human
decision, and M5.9 depends on M5.2 (the real `GolfState` type). The ASCII
diagram above shows these cross-stream edges explicitly. What genuinely
runs independently in parallel is each stream's *entry point*: M5.1/M5.3
(Stream A) and M5.7 (Stream B) have no blockers and may start on day one
together — but Stream B's later issues still converge on Stream A's
outputs well before M5.11, and a slip in M5.1/M5.2 will delay M5.8/M5.9
accordingly.

## Human decision gate representation

M5.7 ends in a literal `HUMAN DECISION REQUIRED` block, per the M4.0/M5.0
precedent. Until a human resolves it:

- M5.8 remains at project Status `Backlog` (never `Ready`) and its issue
  body states plainly: *"Blocked: do not begin ADR-drafting work until
  issue #<M5.7> records a `HUMAN DECISION: APPROVED/RESOLVED` outcome."*
- M5.9/M5.10 inherit the same block transitively (both reference M5.7's
  issue number in their `## Dependencies` section, not only M5.8's).
- The parent issue (#11) states this gate explicitly in its own body so
  it is visible without opening every child issue.

## Review record

- **CaddAI Architect** (read-only review of the draft tree): approved the
  Stream A decomposition (M5.4/M5.5 split judged not artificial — mirrors
  the M5.0 research document's own staged pipeline); required moving the
  `caddai.gps`/`caddai.course` boundary-test edit from M5.5 into M5.4;
  flagged that `GolfState`'s "zero dependencies" must be ADR-decided, not
  asserted; identified a missing `strategy -> simulation`/`golf_state`
  boundary-test edge (added to M5.11); required M5.8's ADR to also decide
  `E_base`/`CandidateValueDistribution`'s owning module; required an
  `AGENTS.md` §4 ownership decision for `caddai.golf_state` (added to
  M5.1); required M5.13's risk/penalty summary be scoped as
  presentational-only; required M5.10's penalty-stroke semantic be framed
  as a modelling choice, not Rules-of-Golf implementation; required M5.14
  to state the shipped baseline is provisional. All incorporated above.
- **QA Engineer** (testability review): confirmed all 14 issues are
  objectively testable or are transparently scoped as document/ADR/
  research deliverables; required M5.9/M5.10/M5.11 to carry explicit
  language scoping/inheriting M5.7's decision and M5.10's resolved
  penalty convention; required narrowing M5.6 away from duplicate
  precedence/fallback test-ownership with M5.5; required reframing two
  unverifiable "absence" claims (M5.4's "handedness-independent", M5.13's
  "no new risk computation") as concrete, positive, checkable assertions.
  All incorporated above.
- **Adversarial Reviewer** (read-only challenge of the finalized tree):
  `REQUEST_CHANGES` on first pass, three findings addressed above —
  M5.14 was rewording M5.7's still-open outcome as an unconditional
  "provisional/placeholder" claim (fixed: M5.14 now describes whatever
  M5.7 actually decides, mirroring M5.9's hedge); M5.11 didn't carry
  M5.10's unsupported-state masking safety property into its own
  aggregation (fixed: M5.11 now requires masked/`nan` entries be excluded
  from `mean SG`/aggregate fields, with sample counts adjusted
  accordingly); the "Dependency graph" section's "independent until
  M5.11" claim contradicted the issue tables' own `M5.1`/`M5.2 ->
  M5.8`/`M5.9` edges (fixed: graph and prose corrected to show the
  cross-stream dependency explicitly). Two minor findings also addressed:
  rollout's "defensible parameters" judgement call had no review gate
  (fixed: M5.4 now requires an Architect read-only check for any
  non-identity rollout offset); M5.14's demo pipeline description omitted
  the `PlayerShotDistribution` step (fixed). No blocking findings —
  `GolfState` player-neutrality, the `SG_base` formula, unsupported-state
  handling elsewhere, the putting/Rules boundary, the legacy
  `recommend_club()` transition, and overall scope-vs-M6 proportionality
  were all approved without changes.

## Legacy deterministic strategy transition

M3's deterministic `recommend_club()` continues to exist, unchanged, in
M5. M5 adds a **new**, separate probabilistic recommendation entry point
(M5.13) rather than mutating `recommend_club()`'s existing semantics.
Deprecation/removal of the legacy path is **not** decided or performed by
M5 — that is an explicit future decision, recorded here as open, not
silently assumed. Demo/tests exercise both entry points side by side so
their behaviour is visibly distinguishable (M5.13).

## Putting boundary

M4's probabilistic shot-distribution model still defers
`ClubCategory.PUTTER` (`resolve_population_prior` raises
`PopulationPriorUnsupportedCategoryError`). M5's `E_base`/`GolfState` may
nevertheless assign a baseline expected-strokes value to an on-green
`GolfState` (a value-model lookup, not a physical putt simulation) — per
the M5.0 research document's section L. No M5 issue implements putting
shot-simulation; a dedicated putting probabilistic model remains a
tracked backlog item (already recorded in `docs/backlog.md`).

## Penalty / Rules boundary

M5 needs enough abstract semantics to *value* important bad outcomes
(penalty/OB states exist and are valued by `E_base`), but does **not**
implement formal Rules-of-Golf procedure (exact drop/relief positioning,
stroke-and-distance mechanics) — that remains M9's Rules-of-Golf gate.
Where an exact Rules behaviour would materially change a numeric baseline
(e.g. the penalty-stroke counting convention in M5.10/M5.11), the
dependency/assumption is flagged explicitly in that issue rather than
inventing policy.

## Rollout treatment

Per the M5.0 research document's section G: rollout is a distinct,
separately-named, swappable step (M5.4), never fused with classification
(M5.5). A coarse deterministic offset ships **only if** defensible
parameters exist; otherwise an explicit, visibly-labelled identity/
no-rollout approximation is an acceptable M5 outcome — M5 must not be
blocked on a calibrated rollout model. Sophisticated/calibrated rollout
physics remains a tracked backlog item, not an M5 issue.

**Guarding against an unreviewed "defensible parameters" judgement call.**
Unlike the expected-strokes numeric baseline (M5.7), which is gated by a
mandatory `HUMAN DECISION REQUIRED` block, whether coarse-rollout
parameters are "defensible" is otherwise left to the implementing
engineer alone — an asymmetry the Adversarial Reviewer flagged. M5.4's
acceptance criteria therefore require that if a non-identity rollout
offset is proposed, its justification (source/reasoning for the specific
offset) is recorded in the PR description and confirmed by an Architect
read-only check before merge, exactly as if it were any other
new-assumption escalation — an identity/no-rollout transform needs no
such check.

## M5 exit criteria

M5 is complete when:

- `GolfState`'s semantics are stable, ADR-recorded, and implemented
  (Stream A).
- Real course-relative mapping (classification + a swappable rollout
  seam, however coarse) is implemented against `course` geometry (Stream
  A).
- A V0 baseline expected-strokes model (`E_base`) is implemented per an
  explicit human decision on its numeric source (Stream B) — the model
  may be, and most plausibly is, an explicitly-provisional CaddAI-authored
  approximation; this is an acceptable, sanctioned M5 outcome, not a
  blocker.
- Benchmark Strokes Gained (`SG_base`) distributions are computed for
  simulated candidate outcomes, never collapsed to a single scalar
  (Stream C).
- A baseline probabilistic strategy selects a candidate by maximising
  expected benchmark SG (Stream C).
- A structured recommendation is assembled, distinguishable from the
  legacy M3 deterministic path (Stream C).
- An end-to-end, fixed-seed deterministic demo/reference scenario exists
  (M5.14).
- All quality gates pass (`ruff format --check`, `ruff check`, `mypy
  src`, `pytest`).
- Relevant documentation (`roadmap.md`, `architecture.md`,
  `strategy-engine.md`, `backlog.md`) and `CHANGELOG.md` are updated.

## M5 explicit non-goals

See [Non-goals of this M5 plan](#non-goals-of-this-m5-plan) above —
restated for exit-criteria clarity: no `Delta`/player-state adjustment, no
risk/goal-sensitive strategic policy, no WHS scoring policy, no full round
lifecycle, no mobile integration, no Rust/runtime architecture, no
production course packages, no full synthetic validation harness, no
cloud, no LLM.

## M6 handoff

M5's exit state hands M6 (production system architecture & runtime
checkpoint) a genuine Python reference implementation to benchmark/port:
stable `GolfState` semantics, real course-relative mapping, a V0 baseline
expected-strokes model, benchmark SG distributions, a baseline
probabilistic strategy, a structured recommendation, and deterministic/
seeded reference scenarios (M5.14's demo). M5 performs no Rust/mobile/
repository/CI-CD architecture work itself — that is M6's own,
separately-gated scope.

## Docs updates from this planning task

- This file (new).
- `docs/backlog.md` — cross-references updated to point at this plan
  where the existing M5.0-decision backlog entry benefits from it (no
  duplication of content already there); adds explicit backlog entries
  for sophisticated/calibrated rollout physics and a richer future
  risk/goal strategic objective layer if not already distinctly present.
- `CHANGELOG.md` — an `[Unreleased]` entry recording this planning task.
- Issue #11 — rewritten as the authoritative M5 tracking issue (see the
  completion report for its new body).

No other `docs/` file is rewritten by this planning task; `roadmap.md`'s
existing M5 entry already describes M5's scope accurately and is left
as-is (per this task's brief: "do not rewrite the high-level roadmap").
