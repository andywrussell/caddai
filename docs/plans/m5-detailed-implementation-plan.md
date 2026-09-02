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
| M5.4 | Course-relative coordinate transformation and rollout/final-position seam | Strategy Engineer | Simulation | P1 | Backlog | M5.1 | M5.5 |
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
**Confirmed on amendment review:** this issue's three deliverables
(`FeatureType` additions, the containment primitive, fixture extensions)
are a `course`-domain completeness fix that does not depend on ADR 0008's
exact `GolfState` field/enum shape — `course.FeatureType` and
`GolfState`'s own lie/surface category are related but distinct enums, so
`Ready` status and no dependency on M5.1 remain correct.

**M5.4 — Course-relative coordinate transformation and rollout/
final-position seam.** Implements, in `caddai.simulation`: (1) the
deterministic transform `ShotOutcome + shot origin + actual selected
target -> resulting position`, reusing `gps.projection`'s tangent-plane
convention anchored at the shot origin (ADR 0002/0004 precedent),
metres-canonical, deterministic, honouring whatever target was actually
used (never substituting the pin/green-centre/CaddAI's own
recommendation) — the selected-target-frame semantics this issue owns;
tested via a concrete reflected-frame property (the same classified result
under a mirrored coordinate frame, not merely an unverifiable "handedness
independent" claim); and (2) a distinct, separately-named, swappable
rollout/final-position function — the replaceable stage between a
landing/carry-space outcome and the resulting final/course-relative
position — applied before classification. **This issue owns the
architectural seam only, never a calibrated terrain/rollout model:** a
coarse deterministic offset ships **only if** defensible parameters exist;
otherwise an explicit identity/no-rollout transform is a complete,
acceptable V0 outcome (with explicit documentation of its known
limitations and deterministic behaviour), not a placeholder blocking
issue closure. This issue must not invent fixed roll distances, arbitrary
club multipliers, fake firmness constants, or undocumented terrain
coefficients to justify a non-identity offset. Either way, the function
carries a visible `rollout_model_version`-style provenance marker so it is
never presented as a validated physics model. **If a non-identity offset
is proposed at all, its justification must be recorded in the PR
description and confirmed by an Architect read-only check before merge**
(this check applies only to a non-identity offset; an identity/no-rollout
transform needs no such check) — stated here directly in this issue's own
acceptance criteria, not only in the narrative sections below, so it
cannot be satisfied by a self-labelled "provisional" number alone. Adds
`caddai.gps` and `caddai.course` to `simulation`'s allow-list in
`tests/test_architecture_boundaries.py` (this issue is the first to need
them — moved here from M5.5 per Architect review, so M5.4's own code can
pass the boundary test without waiting on M5.5).

**M5.5 — Course-relative classification + GolfState assembly.** Consumes
M5.2 (`GolfState` contract), M5.3 (`FeatureType`/containment primitive),
and M5.4 (resulting position) to implement `simulation`'s full mapping
function producing a `GolfState`. **Owns normal correctness in full** —
hardening (M5.6) only adds pathological/adversarial coverage on top, it
does not complete correctness left unfinished here. Covers: explicit,
deterministic precedence rules for overlapping/duplicate course features
(never "whichever feature happens to be checked first", unit-tested with
a minimal, purpose-built synthetic overlapping-feature case — not
necessarily M5.3's own named fixture, which M5.6 exercises separately as
integration regression); an explicit, documented
boundary-edge convention (Shapely `covers` vs `contains`) for a point
exactly on a polygon edge (likewise unit-tested with a minimal synthetic
case); the explicit `UNKNOWN`/recovery fallback for
any *ordinary* point outside every mapped feature (never silently
`FAIRWAY`, unit-tested with a normal, non-extreme out-of-bounds point);
target override support; deterministic output (identical input always
produces an identical `GolfState`); basic input validation (a
malformed/degenerate course geometry input is rejected clearly, never
silently misclassified) — all required, tested in this issue's own PR.
Adds `caddai.golf_state` to `simulation`'s allow-list in
`tests/test_architecture_boundaries.py` (the one remaining edge M5.4
doesn't need).

**M5.6 — GolfState/course-relative mapping edge-case & invariant
hardening.** Scoped specifically (narrowed from M5.5, per QA review, to
avoid duplicate test-ownership — M5.5 already owns ordinary
precedence/boundary-edge/`UNKNOWN`-fallback correctness **using its own
minimal synthetic test geometries**) to genuinely additional
adversarial/integration coverage: extreme/heavy-tailed M4
Student-t outcomes with a large-magnitude sampled draw landing far outside
any mapped course feature (must fall back to `UNKNOWN` gracefully, never
raise an unhandled exception — distinct from M5.5's own ordinary
out-of-bounds test); and **running M5.3's actual named fixtures — the
overlapping-polygon pair, the boundary-edge point, and the concave
polygon — end-to-end through the complete M5.5 mapping function as
integration/regression tests**, which is genuinely additional to M5.5's
unit-level synthetic-case coverage (M5.5 proves the logic is correct in
isolation; M5.6 proves the real fixture file behaves correctly once wired
through the full pipeline), not just at the primitive level.

### Stream B — Expected-strokes baseline

| # | Title | Owner | Area | Priority | Status | Depends on | Blocks |
|---|---|---|---|---|---|---|---|
| M5.7 | Expected-strokes numeric-baseline/data-source research | Strategy Engineer (research) | Statistics | P0 | Ready | — | M5.8 |
| M5.8 | Expected-strokes interface & value-model ADR | Strategy Engineer (ADR author) + Architect review | Statistics | P1 | Backlog (blocked) | M5.1, M5.7 (human decision) | M5.9 |
| M5.9 | Baseline expected-strokes (`E_base`) implementation + batch evaluation | Strategy Engineer | Statistics | P1 | Backlog (blocked) | M5.2, M5.8 | M5.10 |
| M5.10 | Expected-strokes edge-case & invariant hardening | Strategy Engineer | Statistics | P2 | Backlog (blocked) | M5.9 | M5.11 |

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
version -> same output, always). **Owns normal correctness in full** —
every closed lie/surface category `GolfState` can carry, including
`UNKNOWN`, must produce a defined, tested result (a finite value, or an
explicit unsupported-state signal for `UNKNOWN`/any category with no
defensible baseline — never an unhandled exception for an ordinary
input); batch and scalar paths must agree for ordinary, well-formed
inputs (a required unit test here, not deferred to M5.10); basic input
validation (a malformed/invalid `GolfState` is rejected clearly, never
silently coerced) — tested in this issue's own PR. **Scoped
explicitly to whichever branch M5.7's `HUMAN DECISION REQUIRED` actually
resolves to** — most plausibly, per the verified evidence in the M5.0
research document, "an explicitly provisional CaddAI-authored
approximation," but this issue does not pre-assume that outcome; if M5.7
instead resolves to a licensed/derived source, this issue's scope is
revisited before work begins. **Blocked on M5.8**, which is itself
blocked on M5.7's decision — the same "not `Ready` until the gate clears"
rule applies transitively.

**M5.10 — Expected-strokes edge-case & invariant hardening.** Scoped
narrowly (per QA review, to avoid duplicate test-ownership — M5.9 already
owns basic validation, ordinary batch/scalar agreement, and ordinary
unsupported-state signalling) to genuinely additional coverage: extreme
interpolation/extrapolation boundary behaviour (distances far beyond the
most extreme observed/table range, not ordinary within-range
interpolation); batch-vs-scalar equivalence under adversarial/mixed
batches (e.g. a single batch mixing valid, terminal, and unsupported-state
entries together); and the penalty-stroke counting convention (does a
penalty outcome's expected-strokes value already reflect the drop/replay
position, and does the SG formula's "+1" correctly represent one shot
taken, not an extra penalty stroke) resolved **explicitly as an
`E_base`/`SG_base` modelling choice**, not as an implementation of
Rules-of-Golf penalty procedure generally (that remains M9's Rules-of-Golf
gate) — tested against a deliberately constructed penalty-heavy scenario.

### Stream C — Value / strategy composition

| # | Title | Owner | Area | Priority | Status | Depends on | Blocks |
|---|---|---|---|---|---|---|---|
| M5.11 | Benchmark Strokes Gained + candidate value distribution | Strategy Engineer | Statistics | P1 | Backlog | M5.6, M5.10 | M5.12 |
| M5.12 | Baseline expected-value strategy | Strategy Engineer | Strategy | P1 | Backlog | M5.11 | M5.13 |
| M5.13 | Structured recommendation assembly + legacy M3 transition | Strategy Engineer | Strategy | P1 | Backlog | M5.12 | M5.14 |
| M5.14 | M5 integration, demo & closeout | Strategy Engineer | Strategy | P2 | Backlog | M5.13 | — |

**M5.11 — Benchmark Strokes Gained + candidate value distribution.**
Implements `SG_base = E_base(current_state) - (1 + E_base(resulting_state))`
over a batch of simulated resulting `GolfState`s, correctly reflecting
whatever penalty-stroke-counting convention M5.10 resolved (tested, not
merely assumed); defines a `CandidateValueDistribution` type (mean SG, lower-tail
(adverse-outcome) probability, penalty/hazard probability, upper-tail
(favourable-outcome) probability where meaningful, sample count,
model/version provenance) that **never**
collapses to a single scalar — the full distribution must always remain
retrievable. **Must carry forward M5.10's unsupported-state safety
property into this issue's own aggregation, not merely rely on it existing
upstream**: any masked/`nan` unsupported-state entry M5.10 flags must be
excluded from `mean SG` and from the other aggregate fields, with `sample
count` reflecting only valid samples (and the excluded count separately
recoverable) — tested explicitly, so an unsupported state can never
silently pollute a candidate's mean value. **Must NOT include** strategic
risk preference, WHS scoring policy, the player-adjusted `Delta`, or
candidate/recommendation selection — this issue only produces the value
distribution; M5.12 (`strategy`) consumes it and makes the selection.
Adds `caddai.simulation` and `caddai.golf_state` (and whatever module
M5.8's ADR named for `E_base`) to `strategy`'s allow-list in
`tests/test_architecture_boundaries.py` — the first Stream C issue that
needs this edge.

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

## Amendment (2026-09-02): project metadata corrections and issue boundary tightening

A follow-up review of this plan and the created issues found four
corrections, applied to the plan and to the affected issues directly (no
new M5 issues created, no architecture reopened):

1. **GitHub Project `Area`-field corruption, re-audited (confidence
   levels stated honestly).** Adding the `GolfState` `Area` option
   earlier had blanked all pre-existing items' `Area` values (a GitHub
   Projects API behaviour: `updateProjectV2Field` with
   `singleSelectOptions` replaces the *entire* option set, which also
   clears every item's existing value for that field — it does not merge
   new options into the existing set). Values were restored by inference
   at the time. **This is a second inference pass over the same kind of
   circumstantial evidence (issue title/body/owning subsystem), not
   empirical confirmation against a preserved pre-corruption record** —
   only one item (#56) was ever independently observed before the
   corruption occurred, and that remains the sole `VERIFIED` case; every
   other restored value, including the three corrected below, is a
   `HIGH-CONFIDENCE INFERENCE` or, where genuinely unclear, left
   `AMBIGUOUS`/blank. This pass does not claim a stronger evidentiary
   basis than that. Three items' restorations did not hold up on this
   second pass (#47 "M4.0" research spike, #53 "M4.5" — explicitly a dual
   `player`/`statistics` split by its own issue body, #57 "M4.9" —
   multi-subsystem docs/ADR closeout): each was cleared back to blank,
   matching the established convention that milestone-parent and
   multi-subsystem closeout/research issues (e.g. #2/#9/#10/#32, already
   blank) carry no `Area` rather than an invented single-subsystem label.
   #29 ("Club identity and category") was separately scrutinised against
   an original planning document that placed its implementation in
   `caddai.player` — **checked against current source, not the stale
   plan**: `ClubCategory` is implemented in `src/caddai/statistics/models.py`
   today (`grep -rn "class ClubCategory" src/caddai/`), confirming its
   existing `Area: Statistics` label is correct as shipped, even though an
   earlier planning draft intended `player`. #28 was checked the same way
   and remains a defensible `Area: Player` (the `Club`/`Player` objects it
   evolves are `player`-owned, even though the carry/dispersion types they
   gain are `statistics`-owned). **Operational note, to prevent
   recurrence:** any future edit to an existing single-select Project
   field's option set must first fetch and explicitly re-include every
   existing option (as this task did once the mistake was found) — never
   call `updateProjectV2Field` with a partial or freshly-authored option
   list.
2. **Expected-strokes/value work (#87–#91) reassigned from `Area:
   Simulation` to `Area: Statistics`.** The approved architecture is
   `course` (geometry) → `GolfState` (neutral state) → `simulation`
   (physical `ShotOutcome` → `GolfState`) → baseline expected-strokes/
   value (`GolfState` → `E_base`) → `strategy` (value distributions →
   recommendation) — expected-strokes/value is a distinct conceptual
   layer, not owned by `simulation` merely because it consumes
   simulated/mapped outcomes. `Statistics` is the closest existing `Area`
   semantically: it already represents CaddAI's other quantitative/
   data-driven domain models (`CarryDistribution`, `PopulationPrior`), the
   same shape a numeric expected-strokes baseline table takes, and using
   it keeps `simulation`'s `Area` scoped to what it actually does
   (physical outcome production and course-relative mapping). All five of
   #87 (research), #88 (interface/ADR), #89 (`E_base` implementation),
   #90 (hardening), and #91 (`SG_base`/`CandidateValueDistribution`) move
   together, deliberately: #91 is still a value-layer computation (no
   selection/policy happens there — see point 4 below), so splitting it
   into `Strategy` while #87–#90 stayed in `Statistics` would blur, not
   sharpen, the value/strategy boundary this plan exists to preserve.
   **This is Project tracking metadata only** — it does not decide, and
   must not be read as deciding, `E_base`/`CandidateValueDistribution`'s
   actual Python package (still M5.8's ADR's job, per that issue's
   existing "decides the owning module" requirement, unchanged by this
   amendment).
3. **#84's title and scope clarified.** Retitled
   "Course-relative coordinate transformation and rollout/final-position
   seam" (from "...+ rollout seam") to make the architectural intent
   explicit. Its body now states plainly that it owns the architectural
   seam only, that an identity/no-rollout V0 is a complete and acceptable
   outcome (not a placeholder), and explicitly forbids inventing fixed
   roll distances, club multipliers, firmness constants, or terrain
   coefficients to manufacture a non-identity offset. **The
   Architect-read-only-check requirement for any non-identity offset is
   now stated directly in #84's own acceptance criteria** (previously it
   only appeared in this plan's narrative "Rollout treatment"/"Review
   record" sections, not in the text that actually defines the issue —
   an Adversarial Review finding, now fixed), so it cannot be satisfied by
   a self-labelled "provisional" number alone.
4. **#83's `Ready` status re-verified, confirmed correct — with an
   honestly-stated residual risk.** #83's three deliverables (new
   `FeatureType` members, a point-in-polygon primitive, fixture
   extensions) are a `course`-domain completeness fix independent of ADR
   0008's exact `GolfState` contract shape — no dependency on #81 was
   added, no artificial parallelism was removed. **One soft risk is
   acknowledged, not hidden:** the *specific granularity* chosen for the
   new `FeatureType` members (one generic `PENALTY_AREA` rather than
   several narrower categories) is a reasonable engineering bet, not a
   risk-free certainty — if ADR 0008 later wants a different granularity
   for `GolfState`'s own lie/surface mapping, `course.FeatureType` may
   need a small follow-up change. This does not block #83 (the course
   domain gap is real and independent of that eventual choice), but it is
   recorded here rather than glossed over.
5. **#85/#86 and #89/#90 boundaries tightened, including a fixture-level
   correction.** #85 and #89 (the implementation issues) now explicitly
   own *all* normal correctness — standard invariants, ordinary edge
   cases (including an ordinary `UNKNOWN`/out-of-bounds case each), basic
   input validation, deterministic behaviour, and the required unit tests
   for all of the above — stated as their own scope, not deferred. #85's
   own unit tests use **minimal, purpose-built synthetic geometries**
   (not necessarily M5.3's specific named fixtures) to prove
   precedence/boundary-edge logic in isolation. #86/#90 (the hardening
   issues) were narrowed correspondingly to genuinely additional
   adversarial/integration coverage only: #86 covers extreme/heavy-tailed
   Student-t inputs, plus **running M5.3's actual named fixtures
   end-to-end through the complete M5.5 pipeline as integration/
   regression tests** — genuinely additional to M5.5's own unit-level
   synthetic-case coverage, not a re-test of the same cases at the same
   level (an Adversarial Review finding that the original wording left
   ambiguous for the overlapping-pair/boundary-edge fixtures specifically,
   now resolved by this unit-vs-integration distinction); #90 covers
   extreme extrapolation, adversarial/mixed batches, and the
   penalty-stroke counting convention. Both #86 and #90 were preserved as
   distinct issues (not merged back) — each has genuine, non-duplicated
   adversarial/integration value once this boundary is stated explicitly.
6. **#91's boundary restated explicitly, with risk-adjacent field names
   softened.** #91's body now states plainly that it must **not** include
   strategic risk preference, WHS policy, the player-adjusted `Delta`, or
   candidate/recommendation selection — it only produces the value
   distribution; #92 (`strategy`) consumes it
   and makes the selection. This was already true in substance but is now
   an explicit, checkable statement in the issue itself. Its
   `CandidateValueDistribution` field names were also reworded ("tail/
   downside probability" → "lower-tail (adverse-outcome) probability";
   "upside probability" → "upper-tail (favourable-outcome) probability")
   — an Adversarial Review finding that, while not a substantive policy
   leak, noted this vocabulary echoed risk-preference language that M5.12
   alone is meant to own; the renamed fields are purely statistical
   quantities, unambiguously so.

An Adversarial Review pass on this amendment itself found one blocking
issue (the Architect-check requirement was absent from #84's own
acceptance criteria — fixed in point 3) and several major findings (the
"re-verified" overclaim in point 1, #29's `Area` needing verification
against current source rather than a stale plan, the M5.5/M5.6 fixture
overlap, and M5.10's Status-table annotation not matching the gating
prose) — all incorporated above. **Only M5.10's Status-table annotation
was corrected** (the underlying project item was already `Backlog`, never
`Ready`; only this plan document's table cell text was missing the
`(blocked)` qualifier M5.8/M5.9 already carried). No actual dependency,
human-gate, or project Status value changed as a result of points 3–6
above — only wording/scope clarification and the one documentation-table
annotation fix. Point 2 is a Project-metadata `Area` value change only,
applied to #87–#91's Project item, not to any issue body's substance.

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

### Second review round (2026-09-02 amendment: Project metadata + issue boundary tightening)

- **CaddAI Architect**: `APPROVE` on all 7 points reviewed — the
  Simulation → Statistics `Area` reassignment for #87–#91, the
  Area-metadata-vs-package-ownership distinction, #84's fake-precision
  guard, #83's readiness, #91's value/strategy separation, #86/#90's
  hardening distinctness, and the absence of M6/M8/M9 scope creep. One
  non-blocking observation: the `Area: Statistics` label on #87–#91 may
  need a further metadata refresh once ADR 0008/0009 settle `E_base`'s
  real module — already anticipated by this plan's point 2 above.
- **QA Engineer**: confirmed M5.5/M5.9 now state "owns normal correctness
  in full" with concrete ordinary-case criteria, and M5.6/M5.10 correctly
  scope themselves to genuinely additional adversarial/extreme coverage
  with an explicit non-duplication statement. Flagged one wording gap:
  "basic input validation" appeared in the amendment's summary but not
  verbatim in M5.5's/M5.9's own paragraphs — fixed by adding it explicitly
  to both.
- **Adversarial Reviewer**: `REQUEST_CHANGES` on this amendment's first
  draft, six findings (one blocking, four major, one minor), all
  addressed: (1, major) the "re-verified" `Area`-audit language overclaimed
  certainty beyond what a second inference pass actually establishes —
  softened, and the sole empirically-`VERIFIED` item (#56) is now named
  explicitly; (2, major) #29's `Area` needed checking against current
  source rather than a stale planning document — verified
  (`ClubCategory` is implemented in `caddai.statistics.models` today,
  confirming `Area: Statistics` is correct as shipped); (4, major) #83's
  `Ready` status glossed over a soft dependency (the specific
  `FeatureType` granularity chosen is a bet on ADR 0008's eventual
  lie/surface shape) — now acknowledged explicitly without changing the
  decision; (5, blocking) the Architect-read-only-check requirement for a
  non-identity rollout offset existed only in this plan's narrative
  sections, not in #84's own acceptance criteria — added directly to
  #84's text (and #84's own GitHub issue body already had it, confirmed);
  (6, major) M5.5/M5.6's fixture-based split still overlapped for the
  overlapping-polygon/boundary-edge fixtures specifically — resolved by
  distinguishing M5.5's own minimal synthetic-case unit tests from M5.6's
  integration/regression run of M5.3's actual named fixtures; (8, major)
  M5.10's Status-table cell was missing the `(blocked)` qualifier M5.8/
  M5.9 already carried, risking a false impression it could be promoted
  to `Ready` independently — corrected. One minor finding (#91's
  "tail/downside"/"upside" field names echoed risk-preference vocabulary)
  also addressed via renaming. Two questions returned no finding: expected-
  strokes decoupling from `simulation` is wording-consistent (M5.8 still
  correctly frames `caddai.simulation` as only one undecided ADR
  candidate, not a settled fact), and #28's `Area: Player` was checked
  against current source and remains defensible.
- **Integrator**: verified #81–#94 all carry milestone `M5`; #11's native
  sub-issue count remains 14; every `Area`/`Priority`/`Status` value for
  #81–#94 matches this plan's tables exactly, with #88/#89/#90 confirmed
  `Backlog` (never `Ready`); all 39 pre-existing project items outside
  #81–#94 were compared against their pre-amendment baseline with zero
  drift found; #84's title and #11's table both reflect the new wording.
  No discrepancy found.

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
