# M5.0 Research Spike: Course-Relative `GolfState` & Expected-Strokes V0

> **Status: research/design spike only.** No production code is changed by
> this document. No `GolfState`, classification, rollout, expected-strokes,
> Strokes Gained, strategy utility, round lifecycle, WHS calculation, or
> synthetic-validation-harness code is implemented here. No ADR or GitHub
> issue is created by this document. This mirrors
> [docs/research/m4-probabilistic-golfer-model.md](m4-probabilistic-golfer-model.md)'s
> (M4.0's) format and rigour, per the M5 roadmap entry and GitHub issue #11.

## ⚠️ CRITICAL TOOLING LIMITATION — read before trusting section H

**This research session had no live web-fetch/browsing tool available.**
Unlike M4.0's research document, whose evidence table cites sources
verified via live research tooling (DOIs/URLs checked at the time of
writing), **nothing in [section H](#h-expected-strokes-evidence-review) or
[section K](#k-datalicensing-table) below was freshly verified this
session.** Every claim in those sections is limited to stable, extremely
well-established public golf-analytics knowledge the author is highly
confident about from general training knowledge, not from a verified
citation. Every such claim is explicitly flagged inline as
**`[UNVERIFIED THIS SESSION — recommend human verification]`**.

**This evidence review does NOT meet M4.0's verification bar.** The human
must treat [section H](#h-expected-strokes-evidence-review) as a **starting
hypothesis**, not settled evidence, and must independently verify — before
relying on it for any implementation decision — exact table values,
licensing terms, current URLs/DOIs, and publication currency of every
source discussed. No specific numeric expected-strokes table or formula is
invented anywhere in this document; only the *structural shape* of known
public expected-strokes research is described. This limitation is repeated
at the top of section H and again in the final decision-gate block for
visibility.

---

## A. Executive recommendation

1. **`GolfState` should be defined as a new, dependency-free neutral
   domain module** (illustratively `caddai.golf_state`), not folded into
   `simulation` or `strategy`. This is the CaddAI Architect's recommended
   option (see [section E](#e-golfstate-ownership-options)) and this
   research concurs: it is the only option that avoids a real
   dependency-direction risk, avoids over-scoping `simulation`, and serves
   the full breadth of future consumers (`strategy`, M8 round model, M9
   synthetic harness, decision journal) without forcing them to import an
   unrelated subsystem for a type. This decision needs an ADR before
   implementation (new foundational module + new public contract — see
   [section P](#p-adr-requirements)).
2. **Course-relative classification (turning a `ShotOutcome` + geometry
   into a `GolfState`) should live in `simulation`**, consuming `course`
   geometry and returning the neutral `GolfState` type. This adds no new
   dependency edge beyond what `docs/architecture.md`'s target diagram
   already documents (`simulation -> course`).
3. **Terrain/rollout should ship as a deliberately simple, clearly-labelled
   V0 approximation** — classify the M4 simulated landing point with a
   small deterministic offset applied first, not a physics rollout model —
   consistent with the roadmap's own explicit statement that "a real
   rollout/bounce physics model is explicitly not required for V1."
4. **No expected-strokes model, table, or formula should be implemented
   yet.** The evidence available without live verification this session
   supports only a *structural* recommendation (a distance/lie-conditioned
   lookup/interpolation approach, in the spirit of Mark Broadie's Strokes
   Gained methodology and the USGA/R&A World Handicap System's adoption of
   a similar baseline), not a specific numeric table. A **decision gate**
   (per the roadmap's own explicit requirement) must follow independent
   human verification of sources before any implementation issue is
   opened.
5. **This spike recommends, but does not decide,** both the `GolfState`
   ownership question and the expected-strokes V0 approach — see the two
   `DECISION REQUIRED` blocks at the end of this document.

## B. Current-state audit

### What exists today (verified against current source, not documentation only)

- **`course` (src/caddai/course/models.py, distance.py):**
  `FeatureType` is a `StrEnum` with exactly seven members: `TEE`,
  `FAIRWAY`, `GREEN`, `BUNKER`, `WATER`, `OUT_OF_BOUNDS`, `LANDING_AREA`.
  `Feature` has a required `position: Coordinate` and an optional
  `boundary: tuple[Coordinate, ...] | None` (single exterior ring only, no
  interior rings). `Hole` has `number`, `par`, and an ordered `features`
  list — **no `pin_position` field exists**. `course/distance.py` provides
  `green_front_centre_back_distances` (signed front/centre/back distance
  to a green, "centre" meaning the green polygon's own centroid, **not** a
  pin) and `hazard_carry_distance` (signed carry distance to clear a
  hazard along a line of play, or `None` if the line never crosses it).
  Both are explicitly documented as correct only for a **convex** boundary
  ring — a concave ring can produce more than two line crossings, which is
  an explicit non-goal, not a silently wrong answer (ADR 0004).
- **`simulation` (models.py, sampling.py, environment.py):**
  `ShotOutcome` is a frozen, finite-value-validated Pydantic model with
  exactly two fields, `downrange_metres`/`lateral_metres`, both signed
  floats relative to the shot's own origin and the golfer's intended
  target line — **not** course-relative in any way (no lie, no
  hole/course reference, no terminal-state flag). `sampling.py` draws
  seeded intrinsic outcomes from a `PlayerShotDistribution`
  (bivariate Student-t, ADR 0006); `environment.py`'s
  `apply_environment_transform` applies a deterministic wind/elevation/
  air-density adjustment to a `ShotOutcome`, still in the same
  origin-relative, non-course-aware coordinate space.
- **`player` (models.py):** `ShotRecord.final_downrange_metres`/
  `lateral_offset_metres` follow the *same* convention: signed distances
  relative to the golfer's own **selected/accepted** target line for that
  specific shot, explicitly documented as "not automatically the pin,
  green centre, hole centreline, or a CaddAI-recommended target, unless
  the golfer actually accepted that target" (the "M4.4 round-4 addendum").
  No player-domain lie/context type exists yet (tracked in
  [docs/backlog.md](../backlog.md) as a deferred item, explicitly noting a
  future such type must not import `caddai.strategy.LieType`).
- **`gps/projection.py`:** `to_local`/`to_coordinate` implement a
  small-area tangent-plane (equirectangular) approximation, valid only
  within roughly a 2 km radius of the projection origin — sufficient for
  a single hole/shot, not for course-wide or multi-hole spatial
  reasoning without care.

### Specific gaps relevant to M5 (confirmed against code, not assumed)

1. **No `ROUGH` `FeatureType`.** The current enum has no rough category at
   all — an outcome landing anywhere that is not tee/fairway/green/
   bunker/water/OOB/landing-area currently has **no matching feature
   type to classify against**.
2. **No generic penalty area distinct from `WATER`.** Many golf courses
   have lateral/environmental hazards that are not water (e.g. desert,
   waste areas, environmentally sensitive areas) treated similarly to a
   penalty area under the Rules of Golf. Today's model conflates "penalty
   area" with `WATER` specifically; there is no `FeatureType.PENALTY_AREA`
   or equivalent.
3. **No pin/flag position concept.** `Hole` has no `pin_position` field;
   `course/distance.py`'s "centre" is a green polygon's own centroid, not
   a pin. This is already an explicitly documented known limitation in
   [docs/course-engine.md](../course-engine.md). Any course-relative
   distance-to-hole calculation for expected strokes (which fundamentally
   needs distance-to-pin, not distance-to-green-centroid) has **no data
   source to read from today**.
4. **Convex-polygon-only distance queries.** `green_front_centre_back_distances`/
   `hazard_carry_distance` are documented as correct only for convex
   boundary rings. A real green or hazard shape is not guaranteed convex;
   classification logic built on top of these queries inherits this
   limitation.
5. **No "is this point inside this polygon" containment query exists at
   all.** Everything in `course/distance.py` computes distances/crossings
   along a specific line of play (player → aim point). Classifying an
   arbitrary landing point's lie requires point-in-polygon containment
   tests against every relevant `Feature.boundary` on a hole — this is a
   **new geometric primitive**, not a reuse of an existing one, though
   Shapely (already an approved dependency, already used by `course`) can
   supply it directly (`shapely.geometry.Polygon.contains`/`covers`).
6. **No terminal/holed-state concept anywhere.** Nothing in `simulation`
   or `player` has a boolean or enum for "this shot finished in the hole."
7. **No penalty/OB outcome flag on `ShotOutcome` or `ShotRecord`.** Both
   are purely geometric (downrange/lateral); a shot that crossed OB or a
   penalty area has no way to be flagged as such today. (`docs/backlog.md`
   separately notes a "penalty/out-of-bounds/lost-ball outcome flag on
   `ShotRecord`" as an already-identified deferred item.)
8. **No stable course/hole identifier scheme for a "which hole/course was
   this" reference outside of holding a live `Course`/`Hole` object.**
   `Course`/`Hole` have no id/version field — only `Course.name` (a bare
   string) and `Hole.number`.
9. **No tee-set/Course-Rating/Slope-Rating/Stroke-Index data shape yet** —
   flagged by the M5 roadmap entry as "pulled forward" WHS data-shape
   work, not yet implemented.

### What this means for M5

Course-relative classification cannot be a thin wrapper around today's
`course` module unmodified — it will need, at minimum: a `ROUGH` (and
likely a generic penalty-area) `FeatureType`, point-in-polygon containment
queries (new, not present), and either a `Hole.pin_position` field or an
explicit decision to classify against green-centroid only for V0 (see
[section C](#c-course-relative-transformation)). None of these are
implemented by this spike.

## C. Course-relative transformation

### The conceptual mapping

```
golfer-relative ShotOutcome (downrange_metres, lateral_metres)
        +
shot origin (a Coordinate, e.g. player's GPS position at address)
        +
selected/intended target (defines the target line the ShotOutcome's
        downrange/lateral axes are measured against)
        +
course geometry (Course/Hole/Feature boundaries for the hole in play)
        ↓
resulting absolute position (a Coordinate, or an equivalent local-frame point)
        ↓
[optional V0 rollout approximation — see section G]
        ↓
lie/surface classification (point-in-polygon against Feature boundaries)
        ↓
GolfState
```

### Precisely defining each input, and preserving existing conventions

- **Origin.** The shot's starting position — a `Coordinate` (or an
  already-projected local point, consistent with `gps.projection`'s
  ~2 km validity radius per ADR 0002/0004). For a single shot this is
  always within that radius of any point on the same hole in practice, so
  reusing the existing tangent-plane projection (anchored at the shot
  origin, matching ADR 0004's player-anchored convention) is a natural fit
  — **no new projection technique is required**, only a decision about
  *which* point anchors the frame for a given classification call
  (recommendation: the shot origin, mirroring ADR 0004's
  `player_position`-anchored precedent for `course/distance.py`).
- **Selected/intended target vs. pin vs. green-centre vs. CaddAI
  recommendation — these are four conceptually distinct points and must
  not be conflated:**
  1. **Selected/accepted target** — the golfer's actual intended target
     for this specific shot, which the `ShotOutcome`'s
     `downrange_metres`/`lateral_metres` are measured relative to. This
     preserves the M4.4 "round-4 addendum" principle verbatim: **the
     target-line-relative coordinate convention already established for
     `ShotRecord` must be reused unchanged for classification, not
     reinterpreted.** A `ShotOutcome`'s axes are only meaningful once the
     selected target (and hence the target line direction) is known — the
     course-relative transformation cannot proceed without it.
  2. **Intended target line** — the geometric line implied by the origin
     and the selected target; this is the axis `downrange_metres`/
     `lateral_metres` are measured against, not necessarily the
     straight line to the pin or green centre.
  3. **Pin/flag position** — does not exist in the domain model today (see
     [section B](#b-current-state-audit)). If a future round/decision API
     provides pin position, distance-to-pin for expected-strokes purposes
     should use it directly; V0 without pin data must fall back to
     distance-to-green-centroid (already available via
     `green_front_centre_back_distances`), explicitly labelled as a known
     approximation, not silently substituted.
  4. **CaddAI recommendation** — a *candidate* target CaddAI is evaluating,
     which may or may not be what the golfer selects. Course-relative
     classification, as a `simulation`-owned operation, must be usable
     against **any** candidate target a `strategy` caller wants evaluated
     (recommended or not) — it must not assume the classified target was
     necessarily accepted by the golfer. This is the correct generalisation
     of "selected target" for M5's *forward* simulation-and-evaluation use
     case (evaluating hypothetical candidate targets), as distinct from
     `ShotRecord`'s *retrospective* use case (recording what the golfer
     actually did) — the same target-line-relative coordinate convention
     serves both, and this spike does not propose diverging it.
- **Golfer handedness independence.** Already structurally guaranteed:
  `ShotOutcome.lateral_metres`, `DirectionalDispersion.lateral_bias_metres`,
  and `ShotRecord.lateral_offset_metres` all share one fixed sign
  convention (negative left, zero on-line, positive right of the intended
  target line) that is defined relative to the target line's direction of
  travel, not the golfer's stance — so it is already independent of
  whether the golfer is left- or right-handed. Course-relative
  classification introduces no new handedness concern; it only needs to
  correctly rotate the local downrange/lateral frame to match the
  actual origin→target line's real-world bearing (via `gps.projection`),
  which is a geometry detail, not a new domain concept.
- **Local metre frame reuse.** ADR 0002 (point projection) and ADR 0004
  (player-anchored local frame for distance queries) already establish the
  pattern this transformation should reuse: project the origin, the
  selected target, and every candidate `Feature.boundary` together, fresh,
  per classification call, anchored at the shot origin — never at a
  feature's own ad hoc `boundary[0]` origin (ADR 0003's unrelated,
  narrower-purpose origin). This spike recommends classification follow
  the same frame-consistency invariant ADR 0004 already established for
  `course/distance.py`, rather than inventing a new projection convention.
- **Where selected-target geometry comes from, without implementing the
  round model.** For M5's own strategy-evaluation use case, `strategy`
  itself supplies the candidate target directly (it is evaluating a
  candidate shot to *that* target) — no round/decision API is needed for
  that path. A **future** round/decision-journal API (M8) will need to
  supply the golfer's actual selected target for retrospective
  `ShotRecord`-based classification (e.g. reconstructing what golf state a
  past shot produced); this spike does not design that API, only notes
  that the same `GolfState`-producing classification function should serve
  both callers without change, since both ultimately provide "an origin +
  a target + course geometry."

### Rollout's place in this pipeline

Rollout (if applied at all in V0) sits **between** "resulting absolute
position from `ShotOutcome`" and "lie/surface classification," as a
distinct, separately-named, swappable step — see
[section G](#g-terrain-rollout-v0) for the full recommendation, which
mirrors the CaddAI Architect's guidance.

## D. GolfState requirements

The following is a field-by-field review of what a **minimal**
expected-strokes-oriented `GolfState` plausibly needs. For each: why
expected strokes needs it, whether it can be *derived* instead of stored,
whether M5 needs it *now*, and whether it actually belongs to later
round/scoring state (M8) instead.

| Candidate field | Why expected strokes needs it | Derivable vs. stored | Needed now (M5)? | Belongs to M8 instead? |
|---|---|---|---|---|
| Distance-to-hole (or to green-centroid fallback) | The single most important expected-strokes conditioning variable in all known public methodology (Strokes Gained baselines are fundamentally distance-conditioned) | Could be derived on demand from position + course geometry, but storing it as a resolved scalar on `GolfState` avoids every consumer needing course-geometry access just to read a distance | **Yes** | No |
| Lie/surface category (fairway/rough/bunker/green/recovery/etc.) | Public Strokes Gained methodology conditions baselines on lie category as well as distance | Must be *produced* by classification (not derivable from `GolfState` itself after the fact) | **Yes** | No |
| Penalty/OB state (explicit boolean or enum) | A penalty stroke materially changes expected strokes (extra stroke + replay position); must never be inferred from a "suspicious" distance value | Stored, explicit — must not be inferred from lie category alone (e.g. "lie == WATER" is a reasonable proxy but the state itself should carry the flag explicitly per the domain-invariant analysis below) | **Yes** | No |
| Terminal/holed state (explicit boolean) | Expected strokes from a holed state is trivially zero *to the consuming expected-strokes model*, but `GolfState` itself must not silently assume "distance ≈ 0 implies holed" | Stored, explicit — never inferred from floating-point proximity | **Yes** | No |
| Position (absolute or local-frame point) | Needed to compute distance-to-hole/pin once pin data exists, and useful for a future decision-journal record | Could be recomputed from other stored data in some cases, but a resolved position is the most natural single source of truth | **Yes** | No |
| Selected/aim-frame reference (which target line produced this state) | Needed to avoid silently reinterpreting a golfer's genuine target as "the pin" — a real risk given course's documented pin-position gap | Must be stored/labelled explicitly, not re-derived, since re-deriving it would require re-guessing which target was actually used | **Yes** | No |
| Course/hole geometry reference (stable id, not embedded object) | Any expected-strokes/round consumer needs to know *which* hole/course this state belongs to, without embedding a full mutable `Course`/`Hole` graph | Stored as an identifier | **Yes, in shape** — actual stable id/version scheme is course-package/M7 work, not decided here | Partially — full versioning may mature alongside M7 |
| Number of strokes taken so far this hole | Needed for a **round**-level Strokes-Gained running total, not for a single candidate-shot evaluation in isolation | N/A — this is round state | **No** | **Yes — M8** |
| Score relative to par / round context | Needed for goal-sensitive strategy (e.g. "need birdie"), explicitly out of scope per the roadmap's M5 entry | N/A | **No** | **Yes — M8** |
| WHS Course Handicap / Stroke Index usage | Explicitly deferred WHS scoring *policy*, per the roadmap's hybrid decision | N/A | **No** | **Yes — M8** |
| Wind/elevation/environment inputs at the time of the shot | Useful for a future decision-journal snapshot, not for the state's own validity | Could be attached by a caller, but is arguably outside `GolfState`'s own minimal contract (it describes the *outcome* state, not the *conditions* that produced it) | **Debatable — lean no for the type itself** | Possibly captured alongside `GolfState` by the decision journal (M8), not inside `GolfState`| 

### Domain invariants (adapted from the Architect's analysis)

Some plausible invariants actually belong to the future expected-strokes
model, not to `GolfState`'s own validity — precision matters here:

**`GolfState`-level invariants:**
1. Distance-to-hole/geometry-context fields must be finite and
   non-negative where semantically a distance.
2. Lie/surface category must be a well-defined closed set and must
   **never** silently default to `FAIRWAY` (or any "safe" default) for
   unmapped/unknown geometry — it must map to an explicit
   `UNKNOWN`/recovery category instead.
3. Penalty state must be an explicit, structured field (boolean/enum),
   never a magic distance value or an overloaded lie category.
4. Terminal/holed state must be an explicit boolean/enum, never inferred
   internally from "distance-to-hole ≈ 0" — a lip-out is not holed, and
   floating-point proximity is the wrong basis for a binary rules fact —
   it must be set explicitly by whatever produced the state.
5. The selected-target/aim frame used to produce this state must be
   preserved as given, never silently reinterpreted as pin or green
   centre — given `course`'s documented gap (no `Hole.pin_position`;
   "centre" means green centroid per ADR 0003/0004), `GolfState` must not
   paper over this; it should carry whatever frame was actually used,
   visibly labelled.
6. The course/hole geometry reference must be a stable identifier
   (course id/version, hole number), not an embedded mutable `Course`/
   `Hole` object graph.
7. No WHS/scoring-policy fields (Course Handicap, Stroke Index usage,
   gross/net) inside `GolfState`.
8. Raw course-provider/geometry implementation details must not leak in
   (no embedded Shapely objects, no raw GeoJSON properties).
9. Should be structurally immutable (`frozen=True`), consistent with
   `ShotOutcome`/`WindComponents`/`EnvironmentInput` precedent.

**Explicitly NOT `GolfState`-level:** "holed state has zero expected
strokes remaining" belongs to the expected-strokes model that *consumes*
`GolfState`, not to `GolfState` itself — `GolfState` only needs to make
"holed" an unambiguous explicit fact (invariant 4); interpreting it as "0
strokes remaining" is the expected-strokes model's job. The same applies
to Strokes Gained/risk/scoring-probability invariants — none of those
belong on `GolfState`.

## E. `GolfState` ownership options

*The following is the CaddAI Architect subagent's read-only architecture
analysis (issue-referenced, already reviewed), adapted directly into this
document per the task brief. It is authoritative input to this spike's
recommendation, not itself a final decision.*

`GolfState` here means the **minimal** representation the roadmap M5 entry
scopes: position, distance-to-hole/geometry context, lie/surface category,
penalty state, hole-out/terminal state, and a course-geometry reference —
explicitly **not** round/scoring state (M8).

### Option (a) — New neutral top-level module (e.g. `caddai.golf_state`)

- **Location.** A new sibling module alongside `course`, `player`,
  `statistics` — i.e. a fourth "domain primitive" module, not owned by an
  existing subsystem.
- **Dependency graph impact.** `GolfState` itself would depend on nothing
  but stdlib/Pydantic (a pure value type), matching how `course`/`gps`/
  `statistics` are leaf-ish domain modules today (per
  `test_architecture_boundaries.py`, `statistics` and `gps` currently
  permit *zero* other `caddai.*` imports). `simulation` and `strategy`
  would gain a new edge *into* this module; no edge is introduced *from*
  it into anything, so no cycle risk. This is the same shape as the
  already-flagged-but-undone "neutral shared-domain module" for
  `Wind`/`LieType`/`EnvironmentInput` noted in `docs/backlog.md` and
  `docs/architecture.md` ("Shared concepts... live in a neutral
  shared-domain module, not duplicated or cross-imported") — this is
  precedented intent, not a novel pattern.
- **Who depends on it.** `simulation` (to construct instances from
  classification), `strategy` (to evaluate/compare candidate resulting
  states), a future expected-strokes/value model, the M8 round model, the
  M9 synthetic validation harness, and the decision journal — i.e. almost
  every consumer named in the roadmap.
- **Reuse/testability.** Highest of the three options: a pure value type
  with no behavioural coupling to `simulation`'s Monte Carlo internals or
  `strategy`'s optimisation logic is trivially constructible in tests
  without importing either subsystem.
- **Rust/reference-portability.** Best fit — a plain, dependency-free data
  contract maps cleanly to a serialisable schema independent of which
  subsystem's *algorithm* eventually gets reimplemented in a future
  non-Python core (M6).
- **Separation from course-provider concerns.** Clean — no dependency on
  `course` is required for the type itself.
- **Separation from round/product concerns.** Clean.
- **Migration/M6 implications.** Lowest churn.
- **Pros.** Matches existing sibling-module precedent; no ownership
  ambiguity; best portability; avoids future consumers (M8, M9) importing
  `simulation` merely to get a type.
- **Cons.** Introduces a fourth top-level domain module and a genuinely
  new ownership question (which agent/team owns it — not currently any of
  the three named in `AGENTS.md` §4) that must be resolved explicitly.

### Option (b) — Inside `caddai.simulation` (the roadmap/issue's own suggested-but-undecided candidate)

- **Location.** `caddai/simulation/golf_state.py`.
- **Dependency graph impact.** No *new* edge beyond what's already
  documented: `simulation -> course` is already the target diagram's
  edge. However, the *current* `test_architecture_boundaries.py` boundary
  for `simulation` only allows `("caddai.simulation", "caddai.statistics")`
  — `caddai.course` is not yet in that allow-list, so this option still
  requires a concrete test/allow-list change even though it matches the
  documented target.
- **Who depends on it.** Same broad consumer set as (a), but now
  `strategy`, the M8 round model, M9's harness, and the decision journal
  must all import `caddai.simulation` merely to reference the state type
  — coupling unrelated consumers to `simulation`'s full module for a
  type-only need.
- **Reuse/testability.** Weaker than (a) — conceptual coupling ("why does
  the round model import the physics simulator module?").
- **Rust/reference-portability.** Weaker — ties the contract's lifecycle
  to whichever subsystem is most likely to be reimplemented/optimised
  first in a future Rust core (Monte Carlo sampling is a classic
  performance-migration candidate).
- **Separation from course-provider concerns.** Fine, but means
  `simulation` now owns both "produce outcomes" and "define the state
  contract those outcomes populate."
- **Migration/M6 implications.** Ties the type's stability to
  `simulation`'s migration timeline specifically.
- **Pros.** Zero new diagram edge; lowest documentation-diff; issue #11
  itself flags this as the "obvious" candidate.
- **Cons.** Over-scopes `simulation`'s ownership; forces every
  non-simulation consumer (round, decision journal, harness) to depend
  on an irrelevant subsystem; weakest portability story.

### Option (c) — Inside `caddai.strategy`

- **Location.** `caddai/strategy/golf_state.py`.
- **Dependency graph impact.** Would require `simulation` to import
  `strategy` to construct/return a `GolfState` from its classification
  step — this **inverts** the documented dependency direction
  (`strategy -> simulation`, never the reverse) and is a direct violation
  of `AGENTS.md` §3/§13's dependency-direction rule, or would force
  classification itself into `strategy`, conflating a low-level geometry
  operation with decision logic.
- **Who depends on it.** Would force `simulation`, the round model, and
  the harness to depend "upward" into `strategy`'s conceptual layer —
  backwards.
- **Reuse/testability, Rust portability, provider/round separation.** All
  weaker for the same structural reason.
- **Migration/M6 implications.** Worst of the three — couples a
  foundational contract to the module most likely to encode
  player-preference/risk-policy logic that will churn.
- **Pros.** None that outweigh the dependency-direction risk.
- **Cons.** Real risk of an actual dependency-direction violation or
  forces classification logic into the wrong module; conflates state
  description with decision logic.

### Recommendation (present as *a* recommendation, not a foregone conclusion)

**Option (a) — a new neutral module (e.g. `caddai.golf_state`)** is the
strongest fit: matches consumer breadth, avoids the only real
dependency-direction risk (option c), avoids over-scoping `simulation`
(option b), and is directly precedented by the already-flagged "neutral
shared-domain module" intent. Its main cost — a new top-level module and
explicit ownership assignment under `AGENTS.md` §4 — is exactly the kind
of decision the roadmap says must be deliberately resolved with Architect
input, not avoided by defaulting into an existing module for convenience.
**This is a recommendation for the human to weigh against option (b)'s
lower documentation-diff, not a decided outcome.**

## F. Course-relative classification ownership

*Also adapted directly from the Architect's analysis.*

The operation: **`ShotOutcome + origin + target + course geometry ->
GolfState`**. A separate design question from [section E](#e-golfstate-ownership-options).

- **`course` must not own it.** `course`'s explicit non-goals already
  state "no club selection, target selection, or risk assessment," and
  `course` has zero dependency on `player`/`simulation`/`strategy` today,
  deliberately, so course-data/provider concerns stay swappable
  independent of golfer/shot semantics. Classifying a shot outcome
  requires knowing about `ShotOutcome` (a `simulation` type), which would
  force `course` to depend outward on `simulation`, inverting the
  documented direction. Not a close call.
- **`simulation` is the strongest candidate.** Already depends on `course`
  per the target diagram; `strategy-engine.md` already earmarks this exact
  composition as a `simulation` responsibility ("Produce a distribution of
  simulated outcomes (resulting position, lie, and any hazard/penalty
  incurred) per shot candidate... course-relative mapping... [is] still
  M5+"). Keeps a single new edge (`simulation -> course`) rather than a
  second, redundant edge elsewhere.
- **A neutral domain/state layer** owning classification logic too is
  plausible but weaker — would force that module to depend on both
  `simulation` and `course`, diluting the "pure type, no behaviour"
  cleanliness that made option (a) attractive for the *type*. Better to
  keep `GolfState` (the type) dependency-free and let `simulation` (which
  already legitimately depends on both) perform classification and
  *return* a `GolfState`.
- **`strategy` must not do low-level geometry classification.** Two
  reasons: (1) duplicates a capability `simulation` is already positioned
  to have (correctness-drift risk given ADR 0004's already-documented
  convex-polygon/frame-consistency subtleties); (2) inverts `strategy`'s
  intended role as an *evaluator* of already-classified states, not a
  re-deriver of physical facts, risking an informal `strategy -> course`
  dependency growing purely for classification purposes.

**Recommendation:** classification lives in `simulation`, consuming
`course` (already-documented edge) and producing a `GolfState` whose
*type* is defined in the neutral module from section E's recommended
option. Keeps `course` geometry-only, keeps `strategy` a pure evaluator,
adds no edge beyond what `architecture.md`'s target diagram already shows.

## G. Terrain/rollout V0

The M5 roadmap entry and issue #11 both already state that "a real
rollout/bounce physics model is explicitly not required for V1 — a
deliberately simple, clearly-labelled-as-approximate deterministic
adjustment... is sufficient." This spike evaluates the three options
named in the original brief:

### Option A — Classify the M4 landing point directly (no rollout at all)

- **Description.** Feed `ShotOutcome`'s downrange/lateral endpoint
  straight into classification, treating the M4 simulated point as if it
  were the ball's *final* resting position.
- **Evaluation.** Simplest possible V0. But `ShotOutcome`/`ShotRecord`'s
  own documentation already models a *final* resting position concept
  (the round-4 addendum discusses "final resting position" explicitly)
  distinct from carry/landing — collapsing landing and final position
  ignores rollout's real, sometimes material, effect (e.g. a drive rolling
  from fairway into first-cut rough, or a running approach rolling off the
  back of a green). This risks systematically over-optimistic
  classification (e.g. treating a ball that actually rolled into a bunker
  as if it stayed on the fairway).

### Option B — Coarse deterministic rollout approximation

- **Description.** Apply a small, explicit, clearly-labelled deterministic
  offset to the landing point before classification — e.g. a fixed
  percentage of intrinsic carry added downrange, possibly conditioned on
  club category (a full-swing iron rolls less than a low, running
  fairway-wood approach) — mirroring the "fixed or lie/club-conditioned
  offset applied before classification" language already used in the
  roadmap's own M5 entry.
- **Evaluation.** Matches the roadmap's own explicit guidance almost
  verbatim. Materially better than option A for cases where rollout
  changes the classified lie/surface (fairway vs. first-cut rough, green
  vs. green-edge fringe), while remaining simple, deterministic, and
  reproducible — no new probabilistic/ML component, no new approved
  dependency. It must be clearly and visibly labelled as an
  approximation (e.g. a `rollout_model_version` or similar provenance
  marker), never presented as a physically validated bounce/roll model.

### Option C — Require a sophisticated rollout model before proceeding

- **Description.** Block M5 classification work until a real
  bounce/terrain physics model (surface firmness, slope, grass
  height/species, spin-dependent bounce) exists.
- **Evaluation.** Rejected for V0 — directly contradicts the roadmap's own
  explicit statement that a real rollout model is "not required for V1,"
  and would materially delay the entire M5 milestone (course-relative
  classification, expected strokes, and Strokes Gained all depend on
  classification existing first) for a capability with essentially no
  public, locally-embeddable evidence base to build on today. This option
  is the most conservative, but conservatism here has a real,
  roadmap-documented cost: it blocks the entire rest of M5 on a dependency
  the roadmap has already explicitly decided not to require.

### Recommendation

**Option B — a coarse, clearly-labelled deterministic rollout
approximation**, applied as a distinct, separately-named, swappable step
from classification (per the Architect's guidance below), not fused into
one non-decomposable operation.

**Ownership (from the Architect's analysis):** rollout and classification
should live in the **same module** (`simulation`), but as two distinct,
separately named, swappable functions — never merged into one operation.
Reasoning: rollout approximation and classification answer conceptually
different questions with very different maturity trajectories (rollout is
an explicit placeholder pending real bounce/terrain physics; classification
is comparatively stable once course geometry exists). This mirrors the
existing pattern of M4.7's `apply_environment_transform` and M4.8's
sampling being kept as separately composable steps (via the
`ShotOutcomeSampler` `Protocol`) specifically so a technique can be
swapped without changing the call shape.

## H. Expected-strokes evidence review

> **⚠️ REPEATED DISCLOSURE: this section was written without live
> web-fetch/browsing tool access this session.** Every claim below is
> limited to stable, extremely well-established public golf-analytics
> knowledge, and is explicitly flagged
> `[UNVERIFIED THIS SESSION — recommend human verification]`. This does
> **not** meet M4.0's verification bar (M4.0's evidence table cited
> sources with DOIs verified via live research tooling at the time of
> writing). No exact numeric expected-strokes value, table, or formula is
> stated anywhere in this section — only the *structural shape* of known
> methodology. The human must independently verify every source's exact
> content, current availability, licensing terms, and publication currency
> before any of this is relied upon for implementation.

### What evidence can plausibly be used

- **Mark Broadie's "Strokes Gained" methodology** — originally developed
  using PGA Tour ShotLink data, and published in his book *Every Shot
  Counts* (2014) and in earlier academic work (e.g. a 2012 paper commonly
  cited as "Assessing Golfer Performance Using Strokes Gained")
  `[UNVERIFIED THIS SESSION — recommend human verification]`. The
  well-known structural idea — not a specific number — is that Broadie's
  work publishes an **expected-strokes-to-holeout baseline conditioned on
  distance-to-hole and lie/category** (e.g. tee, fairway, rough, sand,
  green, recovery), separately for different reference-skill populations
  (commonly a "PGA Tour scratch-level" baseline and, in later
  work/handicap-methodology adoption, baselines for higher-handicap/
  "bogey golfer" populations)
  `[UNVERIFIED THIS SESSION — recommend human verification]`.
- **USGA/R&A World Handicap System (WHS) Strokes Gained-based
  handicap methodology** — the WHS's underlying statistical framework is
  understood to be built on, or closely related to, a Strokes-Gained-style
  expected-strokes baseline, which the governing bodies are understood to
  publish or reference in some form as part of handicap calculation
  methodology, conditioned on distance and category, for a range of
  handicap/ability levels (not only scratch)
  `[UNVERIFIED THIS SESSION — recommend human verification]`. The exact
  current publication, its scope, and its licensing/reuse terms were not
  checked this session.
- **Amateur-golf performance research** (the same general body of work
  referenced by [docs/research/m4-probabilistic-golfer-model.md](m4-probabilistic-golfer-model.md)'s
  evidence table, e.g. Broadie's amateur-scoring analysis) already
  established, for M4.0's purposes, that a relatively small number of very
  poor ("awful") shots materially affects amateur scoring outcomes — this
  is *directionally* relevant to expected strokes (a handicap-conditioned
  baseline must reflect a realistically wide outcome distribution, not
  only a scratch-golfer's tight one), but M4.0's own citation of this
  point should be treated as the more-verified source; this section adds
  no new verification of it.

### Tour vs. amateur/handicap-conditioned transferability

The **single most important transferability caveat** for CaddAI: Broadie's
original, most widely known Strokes Gained baseline was built from PGA
Tour ShotLink data — elite, highly consistent players.
`[UNVERIFIED THIS SESSION — recommend human verification]` CaddAI's actual
target user is very unlikely to be a scratch/tour-level golfer. Using a
tour-level expected-strokes baseline directly for an amateur/handicap
golfer would very likely **systematically understate** the amateur's
actual expected strokes from every non-trivial lie/distance (amateurs take
measurably more strokes to hole out from the same distance/lie than tour
professionals). The more relevant transfer question for CaddAI, exactly as
the roadmap's own M5 entry states, is **amateur/handicap-conditioned
expected-strokes baselines**, not tour-level ones. Published handicap-level
or bogey-golfer baseline tables are understood to exist in some form
(commonly discussed alongside WHS methodology and in some published
Strokes Gained literature extensions)
`[UNVERIFIED THIS SESSION — recommend human verification]`, but their
exact scope, granularity, and licensing were not verified this session.

### Conditioning variables

- **Required for V0 (structurally, per all known Strokes Gained
  methodology):**
  - **Distance to hole** (continuous, the primary conditioning axis in all
    known public methodology) `[UNVERIFIED THIS SESSION — recommend human
    verification]`.
  - **Lie/category** (tee, fairway, rough, sand/bunker, green, recovery —
    at minimum some coarse categorical split; exact category granularity
    in any specific published table was not verified this session)
    `[UNVERIFIED THIS SESSION — recommend human verification]`.
- **Desirable later, not required for V0:**
  - Handicap/skill-level-specific baseline selection (multiple baseline
    curves, not just one) — desirable given the tour-vs-amateur
    transferability caveat above, but a full continuum (rather than a
    small number of discrete bands) would require either a licensed
    detailed dataset or CaddAI's own calibration data.
  - Slope/uphill-downhill or green-speed-conditioned putting baselines —
    plausible refinements, not established as a public, freely reusable
    conditioning axis at the granularity CaddAI would need
    `[UNVERIFIED THIS SESSION — recommend human verification]`.
- **Unsupported by any evidence reviewed this session (must not be
  invented):**
  - Course-specific or hole-specific expected-strokes adjustments beyond
    distance/lie/category (e.g. a specific green's slope or firmness
    affecting expected strokes numerically) — no public source for this
    was identified or recalled with any confidence this session.
  - Weather/wind-conditioned expected-strokes baselines — plausible in
    principle (a wet, into-wind approach plausibly changes expected
    strokes) but not something this session can point to a specific
    public source for.

### Putting, penalty, and recovery states

Known Strokes Gained methodology treats putting as **its own
distance-conditioned baseline category** (an expected number of putts to
holeout from a given distance on the green), separate from full-swing
approach/tee-shot baselines
`[UNVERIFIED THIS SESSION — recommend human verification]`. Penalty
states (water, OB) in known methodology are typically handled by
adding the penalty stroke(s) plus the expected strokes from the resulting
(replay or drop) position, rather than requiring a wholly separate
"penalty" expected-strokes curve
`[UNVERIFIED THIS SESSION — recommend human verification]` — but the
*exact* mechanics of how any specific published methodology treats a
penalty are not verified here and must be checked independently.
"Recovery" lies (deep rough, trees, awkward stances) are the category
where public methodology is likely **thinnest and least granular** — this
session cannot point to any specific, well-established public
recovery-lie expected-strokes table with confidence.

**Nothing in this section should be read as establishing that a specific
numeric expected-strokes value exists or is known for any distance/lie
combination.** Only the *category structure* (distance × lie × skill-level
baseline) is described.

## I. Expected-strokes V0 options

Evaluated per the brief's required dimensions. **No option here defaults
to ML** — this is a deliberate evaluation choice matching M4.0's own
"should V1 use ML? No." precedent, since the same reasoning applies here:
data availability and licensing clarity are the binding constraint, not
modelling sophistication.

### 1. Lookup/bucket table (discrete distance bands × lie category)

- **Evidence support.** Best-matched to how expected-strokes baselines are
  understood to be published (a table of values, not a continuous
  parametric formula) — though the exact published granularity is
  unverified this session.
- **Interpretability.** Highest — a human (or a future explanation layer)
  can point directly at "expected strokes from 120m fairway = X."
- **Offline performance.** Excellent — a small embedded table, O(1)
  lookup after bucketing.
- **Deterministic reproducibility.** Excellent — trivially deterministic.
- **Data requirements.** Needs a defensible, licensable source table (or
  CaddAI's own calibration data) at a reasonable bucket granularity.
- **Interpolation/extrapolation behaviour.** Poor at bucket edges unless
  paired with interpolation (see option 2/5) — a naive lookup produces
  visible discontinuities across a bucket boundary, which is a bad look
  for a "trustworthy" recommendation engine.
- **Monotonicity.** Not guaranteed unless the source table itself is
  monotonic and the bucket scheme preserves it.
- **Replaceability.** Excellent — a table swap requires no code change if
  the interface is kept stable (mirrors ADR 0007's `PopulationPrior`
  precedent).
- **Calibration path.** Good — CaddAI's own future round/decision-journal
  data could refine table cells directly.
- **Licensing.** Depends entirely on the specific source table (see
  [section K](#k-datalicensing-table)) — this is the biggest open risk
  for this option specifically, since a table (rather than a described
  methodology) is the most literally reproducible/copyable artifact and
  therefore the most licensing-sensitive.
- **Implementation complexity.** Low.

### 2. Interpolated surface (e.g. piecewise-linear or spline over distance, discrete lie category)

- **Evidence support.** Same underlying data need as option 1, but smooths
  between table entries.
- **Interpretability.** Slightly lower than a raw table, but still
  reasonably explainable ("interpolated between two known reference
  distances").
- **Offline performance.** Excellent — cheap to evaluate.
- **Deterministic reproducibility.** Excellent, if a fixed, documented
  interpolation method is used (e.g. `numpy`'s deterministic linear
  interpolation) — no new dependency needed for simple interpolation.
- **Data requirements.** Same source-table dependency as option 1.
- **Interpolation/extrapolation behaviour.** Better than raw lookup
  *within* the table's observed range; extrapolation *beyond* the
  table's most extreme observed distance is still an open design question
  (e.g. clamp vs. linear extension) that must be handled explicitly, not
  silently.
- **Monotonicity.** Can be explicitly enforced (e.g. isotonic/monotonic
  interpolation, see option 5) if the raw table itself is monotonic in
  distance, which is a physically reasonable expectation (expected
  strokes should not decrease as distance-to-hole increases, all else
  equal) but is not automatically guaranteed by all interpolation methods
  (e.g. naive cubic splines can overshoot/violate monotonicity between
  points).
- **Replaceability.** Good — same as option 1.
- **Calibration path.** Good.
- **Licensing.** Same as option 1 (depends on the source table).
- **Implementation complexity.** Low-to-moderate (mostly the choice of
  interpolation method and its extrapolation policy).

### 3. Parametric curve (e.g. a fitted closed-form function of distance per lie category)

- **Evidence support.** Plausible in principle (expected strokes vs.
  distance is known to follow a smooth, roughly monotonic, diminishing-
  returns-shaped curve in most published discussions of Strokes Gained)
  `[UNVERIFIED THIS SESSION — recommend human verification]`, but fitting
  a defensible closed-form curve requires either (a) access to enough raw
  or aggregate data points to fit against, or (b) reusing already-fitted
  published coefficients (which raises the same licensing question as a
  raw table, since published fitted-curve coefficients are themselves a
  reproducible, potentially copyrighted artifact).
- **Interpretability.** Moderate — a formula is explainable in principle,
  but a specific functional form (e.g. a particular power-law or
  logarithmic shape) is less immediately intuitive to a golfer-facing
  explanation than "here is the table entry" would be.
- **Offline performance.** Excellent — trivial to evaluate.
- **Deterministic reproducibility.** Excellent.
- **Data requirements.** Fitting requires either real data (which CaddAI
  does not have yet) or reusing someone else's already-fitted
  coefficients (a licensing question, not a modelling one).
- **Interpolation/extrapolation behaviour.** Naturally smooth by
  construction, including at range extremes — a genuine advantage over
  raw lookup/interpolation for extrapolation, provided the fitted form is
  well-behaved outside the fitted range (not guaranteed for every
  functional form).
- **Monotonicity.** Can be guaranteed by construction if a monotonic
  functional family is deliberately chosen.
- **Replaceability.** Good, if kept behind a stable interface.
- **Calibration path.** Requires a fitting step (more machinery than a
  table swap) whenever CaddAI's own data becomes available to refit
  against.
- **Licensing.** Same core risk as option 1/2 if coefficients are sourced
  from a specific published fit rather than fit by CaddAI itself.
- **Implementation complexity.** Moderate — requires choosing and
  justifying a specific functional form, which is itself a modelling
  decision with real room to get wrong absent real fitting data.

### 4. Regression model (fit against available amateur/handicap data)

- **Evidence support.** Would require actual raw or aggregate amateur
  data to fit against — the same data-availability gap M4.0 already
  identified for the *player* model applies here too, likely more
  acutely, since no CaddAI-specific expected-strokes calibration dataset
  exists at all yet.
- **Interpretability.** Depends heavily on model complexity — a simple
  linear/generalized-additive regression over distance/lie remains
  interpretable; anything more complex trades interpretability for a
  marginal, currently unjustified, fit improvement.
- **Offline performance.** Fine for a simple regression; not materially
  different from a parametric curve once fit.
- **Deterministic reproducibility.** Excellent once fit and frozen.
- **Data requirements.** Highest of the options that don't involve ML —
  needs a real dataset to fit against, which CaddAI does not currently
  have and no verified public raw dataset was identified this session
  (mirroring M4.0's own conclusion for the player model: "no verified
  public dataset... combines" the needed variables).
- **Interpolation/extrapolation behaviour.** Depends on the chosen
  regression family; broadly similar considerations to option 3.
- **Monotonicity.** Not guaranteed unless deliberately constrained
  (e.g. isotonic regression, option 5).
- **Replaceability.** Good, behind a stable interface.
- **Calibration path.** This *is* the calibration path once data exists —
  arguably the natural V-next once CaddAI has its own round/decision-
  journal data, but premature without it.
- **Licensing.** Depends on whatever dataset is fit against.
- **Implementation complexity.** Moderate-to-high, and — crucially —
  **not justified today given no dataset exists to fit against.**

### 5. Monotonic interpolation (isotonic-regression-style, guaranteeing expected strokes never decreases with distance for a fixed lie)

- **Evidence support.** Same underlying data dependency as options 1/2,
  but adds an explicit structural guarantee (monotonicity) that is a
  physically reasonable prior even without extra data.
- **Interpretability.** Similar to option 2.
- **Offline performance.** Excellent.
- **Deterministic reproducibility.** Excellent.
- **Data requirements.** Same as option 1/2 (a source table), plus a
  deterministic algorithm to enforce monotonicity where the raw source
  table might have small non-monotonic noise (plausible in any
  small-sample or interpolated source).
- **Interpolation/extrapolation behaviour.** Good within range; still
  needs an explicit extrapolation policy beyond the table's extremes.
- **Monotonicity.** Guaranteed by construction — the whole point of this
  option.
- **Replaceability.** Good.
- **Calibration path.** Good — refitting the monotonic envelope as new
  data arrives is straightforward.
- **Licensing.** Same as option 1/2.
- **Implementation complexity.** Low-to-moderate — a monotonic
  interpolation/regression step is simple, well-understood, and
  implementable with NumPy alone (no new dependency required for a basic
  pool-adjacent-violators-style or simple monotonic-clamping approach).

### 6. Handicap-conditioned tables (a family of tables/curves, one per handicap band, mirroring `PopulationPrior`'s handicap-band precedent)

- **Evidence support.** Directly addresses the tour-vs-amateur
  transferability gap identified in [section H](#h-expected-strokes-evidence-review)
  — the single most important structural feature any V0 needs, in this
  spike's assessment.
- **Interpretability.** Same as whichever underlying representation
  (table/interpolation/curve) is chosen per band — this is an
  orthogonal, additive axis (like `PopulationPrior`'s handicap banding),
  not a competing option to 1–5.
- **Offline performance.** Same as the underlying representation, times a
  small constant number of bands.
- **Deterministic reproducibility.** Same as the underlying
  representation.
- **Data requirements.** Higher than a single-baseline option — needs
  either multiple published baselines (by handicap/ability band) or
  CaddAI's own banded calibration data; the granularity/number of bands
  is itself an open design question deferred to implementation.
- **Interpolation/extrapolation behaviour.** Same considerations as the
  underlying representation, per band; additionally, interpolating
  *between* handicap bands (rather than snapping to the nearest band) is
  an additional design question, mirroring `population_prior_config.py`'s
  own existing handicap-banding precedent and its own open questions.
- **Monotonicity.** Same considerations as the underlying representation,
  per band; additionally, expected strokes should plausibly be monotonic
  *across* handicap bands too (a higher handicap should never have a
  strictly lower expected-strokes baseline from the same
  distance/lie) — another structural check worth enforcing if adopted.
- **Replaceability.** Good, mirrors ADR 0007's precedent directly.
- **Calibration path.** Good — this is the natural longer-term direction,
  consistent with `PopulationPrior`'s already-accepted
  replaceability contract.
- **Licensing.** Depends on the specific banded source(s) used;
  potentially *more* licensing-sensitive than option 1 alone, since
  multiple distinct published baselines (tour + several
  handicap/amateur bands) may need separate licensing review.
- **Implementation complexity.** Moderate — the banding structure itself
  is simple (precedented by `population_prior_config.py`), but sourcing
  defensible per-band baseline data is the real work, and is currently
  unresolved (see [section H](#h-expected-strokes-evidence-review)).

## J. Recommended expected-strokes V0

**Recommendation (structural only — no formula, no table values, no
implementation):** a **monotonic, interpolated lookup table, conditioned
on distance and lie category, with an explicit handicap/ability-band axis**
— i.e. **option 5 (monotonic interpolation) combined with option 6
(handicap-conditioned banding)** from [section I](#i-expected-strokes-v0-options),
deliberately **not** options 3/4 (parametric curve / regression), since
both require either data CaddAI does not have or reused published
coefficients whose licensing is exactly the open question this section
cannot resolve without live verification.

This recommendation is **explicitly provisional and gated**, for two
independent reasons:

1. It is offered without the live source verification this session lacked
   (see the disclosure at the top of this document and of
   [section H](#h-expected-strokes-evidence-review)) — the human must
   independently verify candidate sources, their exact table shape,
   licensing terms, and currency before this recommendation is actionable.
2. The roadmap's own M5 entry explicitly requires "an explicit human/model
   decision gate... between" this spike and implementation — this
   recommendation does **not** itself constitute that gate having passed.

No specific numeric table, formula, or coefficient is proposed anywhere in
this document.

## K. Data/licensing table

Every entry below reuses the tooling-limitation disclosure above:
**none of this table's licensing/availability assessments were verified
live this session** — every row must be independently re-checked by the
human before being relied upon.

| Source | Contents (structural description only) | Population | Sample scope | Publication date | Accessibility | Licensing/reuse status | Offline-embeddability | Caveats |
|---|---|---|---|---|---|---|---|---|
| Mark Broadie, *Every Shot Counts* (book, 2014) `[UNVERIFIED THIS SESSION — recommend human verification]` | Describes Strokes Gained methodology and (in some editions/appendices) reference expected-strokes-by-distance/lie tables | PGA Tour (primary), some amateur discussion | Not verified this session | 2014 (approximate, unverified) | Commercial book — not freely redistributable | **Unclear — likely copyrighted book content; any table reproduced from it is almost certainly not freely licensable for redistribution inside an app without explicit permission** | Would require manual/licensed transcription, not an open dataset | Tour-level bias (see section H); exact table contents/edition not verified |
| Broadie's earlier academic paper(s) (e.g. a 2012 "Assessing Golfer Performance Using Strokes Gained"-titled paper) `[UNVERIFIED THIS SESSION — recommend human verification]` | Academic exposition of the Strokes Gained methodology | PGA Tour ShotLink-derived | Not verified this session | ~2012 (approximate, unverified) | Depends on the specific journal/repository — some academic papers are open-access, others are paywalled | **Unclear — depends on specific publication venue, not verified this session** | Would need explicit re-verification of open-access status | Same tour-level bias caveat |
| USGA/R&A World Handicap System documentation `[UNVERIFIED THIS SESSION — recommend human verification]` | Understood to reference or embed a Strokes-Gained-style expected-strokes baseline as part of handicap methodology, across a range of ability levels | Broader than tour-only (this is the most promising *amateur-relevant* source category identified, but unverified) | Not verified this session | Ongoing/versioned (WHS is a maintained standard) | Publicly documented in some form (governing-body publications) | **Unclear — governing-body handicap methodology documents are often publicly viewable but may carry usage restrictions on embedding derived data commercially; must be checked explicitly** | Plausible if licensing permits — this is the most promising candidate for a locally-embeddable, amateur-relevant baseline, but **not confirmed this session** | Highest-priority source for the human to verify first |
| Any third-party "Strokes Gained calculator" web tool or app `[UNVERIFIED THIS SESSION — recommend human verification]` | Various — some publish underlying baseline tables, most do not | Varies | Not verified this session | Not verified this session | **Almost certainly not licensed for reuse** — typically a derived commercial product | Not embeddable without explicit licensing | Not recommended as a source without direct outreach/licensing |
| CaddAI's own future round/decision-journal data (M8+) | Not a currently existing source — a future first-party dataset | CaddAI's actual users | N/A (does not exist yet) | Future | Fully owned by CaddAI once collected | **Fully licensable (first-party data)** | Fully embeddable once collected and aggregated | The only source in this table requiring **no** licensing verification, but not available for V0 |

**Every "Unclear" licensing status above must be resolved by the human
before any V0 implementation embeds derived numeric content from that
source.** This spike does not resolve licensing; it only flags where the
question exists.

## L. Putting / penalty / recovery treatment

- **On-green value must be modelled as a distinct "value from this green
  state" question, separate from "simulating an actual putt stroke".**
  Expected strokes from an on-green `GolfState` (distance-to-pin on the
  green) is a lookup against a putting-specific baseline (per
  [section H](#h-expected-strokes-evidence-review)'s known structural
  category split), **not** a Monte Carlo simulation of a putt's physical
  outcome. This is an important distinction: CaddAI does **not** need to
  simulate the stochastic physical outcome of a putt to answer "what is
  the value of being on the green X metres from the hole" — it only needs
  a value-lookup, exactly analogous to how expected strokes from a fairway
  lie doesn't require simulating every future shot to the green.
- **This explicitly does NOT require adding `PUTTER` to the M4 shot-
  distribution model.** `ClubCategory.PUTTER` remains `DEFERRED` in
  `resolve_population_prior` (per M4.2/M4 closeout), and this spike does
  not propose changing that. Expected-strokes-from-a-green-state is a
  **value-model** question (section 2 of the "keep separate" framing in
  the roadmap/issue #11), entirely independent of whether CaddAI can
  *simulate* a putt's physical outcome (a **physical-outcome-model**
  question, section 1). A putting `PlayerShotDistribution` would only
  become relevant if/when CaddAI wants to simulate candidate *putting*
  shots themselves (e.g. "should I putt aggressively or lag this putt"),
  which is a distinct, deferred capability the backlog already tracks
  separately, not implied or required by expected-strokes V0.
- **Penalty states** (water, OB, generic penalty area once it exists — see
  [section B](#b-current-state-audit)'s gap) should be modelled as: the
  penalty stroke(s) plus expected strokes from the resulting (drop/replay)
  position — consistent with the general shape described (unverified) in
  [section H](#h-expected-strokes-evidence-review). The exact drop/replay
  position rule itself
  `[UNVERIFIED — subject to M9 Rules-of-Golf gate confirmation]` (Rules of
  Golf-compliant relief) is **not** designed here and is a real,
  non-trivial future concern (see [section O](#o-edge-cases)).
- **Recovery lies** (deep rough, trees, awkward stances) are the category
  where evidence is thinnest (per section H). A defensible V0 fallback:
  treat "recovery/unknown" as its own explicit `GolfState` lie category
  (never silently mapped to `FAIRWAY` or `ROUGH`), and accept that its
  expected-strokes baseline will be the least evidence-backed cell in
  whatever table/model V0 ships — this must be visibly flagged to
  whatever future explanation layer or decision-journal consumer reads
  it, not silently presented with the same confidence as a fairway/green
  baseline.

## M. Provisionality / replaceability

**Contract shape inspired by, not copied from, ADR 0007's precedent**
(`PopulationPrior`'s stable-interface/replaceable-implementation contract):

- **Stable consumer contract, replaceable implementation.** Whatever
  expected-strokes function CaddAI eventually implements
  (`expected_strokes(golf_state) -> float`, illustratively) should be
  designed so its initial implementation (a lookup/interpolated table) can
  later be replaced by a refitted table, a regression fit against CaddAI's
  own data, or a richer representation — **without changing the function
  signature or the `GolfState` contract that `strategy`/the decision
  journal/the M9 harness consume.** This mirrors ADR 0007's core
  guarantee almost exactly, applied to a new value-model contract instead
  of a population-prior contract.
- **Explicit model/version provenance.** Any expected-strokes result
  should be traceable to which underlying table/model version produced
  it (mirroring `population_prior_config.py`'s `config_version` /
  `onboarding_config_version` precedent) — essential for the future
  decision journal's "identity/versioning" requirement
  ([docs/decision-journal.md](../decision-journal.md) already anticipates
  "the version of the... expected-strokes/Strokes Gained model in effect
  at the time" as part of its planned record shape).
- **No baked-in provider dependence.** Whatever source table V0 embeds
  must resolve to purely local, embeddable data — no runtime network
  dependency, consistent with `AGENTS.md` §2.2/ADR 0005 (active-round core
  functionality, which strategy/recommendation and shot simulation both
  are, must never require network access on the critical path).
- **Deterministic offline behaviour.** Given the same `GolfState` input
  and the same model version, the same expected-strokes value must always
  be returned — no stochastic component belongs in the expected-strokes
  function itself (unlike `simulation`'s intentionally stochastic
  Monte Carlo sampling, which produces the *distribution* of resulting
  `GolfState`s expected strokes is then evaluated against).
- **Explicitly provisional numeric content, visibly marked.** Mirroring
  ADR 0006/0007's precedent for `PlayerShotDistribution`/
  `PopulationPrior`, any V0 expected-strokes table/coefficients must be
  marked with an explicit confidence/provenance indicator (e.g. an
  analogous `confidence`/`provenance` pairing) so downstream consumers
  (and, eventually, a user-facing explanation) can distinguish "a
  provisional, evidence-informed guess" from "CaddAI's own calibrated
  data" — never silently presented as validated fact, especially given
  this spike's own tooling-verification limitation.

## N. Performance / batch-evaluation implications

- **Scalar vs. batch expected-strokes API.** `simulation`'s M4.8 sampling
  already produces **vectorised, batch** outcomes (`count` draws per call,
  returned as a tuple of `ShotOutcome`, backed by NumPy array operations
  internally). An expected-strokes/Strokes Gained evaluation step that
  only accepts one `GolfState` at a time would force a Python-level loop
  over potentially thousands of Monte Carlo samples per candidate shot —
  a real performance risk once `strategy` needs to evaluate many candidate
  shots (each producing many simulated outcomes) per recommendation. **A
  batch-friendly expected-strokes contract should be designed from the
  start**, even if V0's actual table lookup is trivially cheap per-item —
  the *interface* shape matters more than the per-item cost at this data
  volume.
- **Pydantic-per-sample overhead risk.** If `GolfState` is a full Pydantic
  model (recommended for its public-contract validation benefits, matching
  `ShotOutcome`/`WindComponents`/`EnvironmentInput` precedent), constructing
  one `GolfState` instance per Monte Carlo sample (potentially thousands
  per candidate shot) could reintroduce meaningful per-sample Pydantic
  construction/validation overhead — the same tension `ShotOutcome`
  already manages by staying a small, frozen model rather than something
  heavier. This is a legitimate implementation concern for a future issue,
  not resolved here, but should inform batch-evaluation-oriented interface
  design (e.g. a NumPy-array-friendly batch classification/expected-
  strokes path alongside a Pydantic-model single-item convenience path,
  mirroring how `sampling.py` builds a NumPy array internally and only
  wraps the final `ShotOutcome` tuple in Pydantic objects at the
  boundary).
- **NumPy-friendly representation.** Whatever internal batch
  classification/expected-strokes computation looks like, it should
  operate on plain NumPy arrays (positions, distances, categorical lie
  codes) internally — consistent with `sampling.py`'s existing precedent
  of doing the numeric heavy lifting in NumPy and only constructing
  Pydantic model instances at the public boundary.
- **Deterministic batching.** A batch expected-strokes evaluation must
  produce identical results to evaluating each item individually (order-
  independence, no accidental cross-sample interaction) — an important
  correctness property to test once implemented.
- **Future Rust portability.** A batch-oriented, NumPy-array-friendly
  internal representation (rather than a Python-object-per-sample loop) is
  also the representation most likely to translate cleanly to a future
  Rust/vectorised implementation if M6 ultimately selects one — this
  spike does not choose a technology, only notes the shape that keeps
  that option open.
- **Verifying the Strokes Gained formula is representable in batch form.**
  `strokes_gained = expected_strokes(current_state) - (1 +
  expected_strokes(resulting_state))`. This is representable in a fully
  vectorised form **provided**:
  - `expected_strokes` itself accepts a batch of `GolfState`s (or their
    array-representable fields) and returns a same-shaped array of
    values — a scalar-only `expected_strokes(state) -> float` signature
    would force exactly the batch-to-scalar-loop problem flagged above.
  - `current_state` is broadcastable against a batch of `resulting_state`s
    (it is a single state; the resulting states are a distribution of
    many) — a straightforward NumPy broadcast if `expected_strokes` itself
    is vectorised.
  - **Tricky cases requiring explicit handling, not silent broadcasting:**
    - **Penalty outcomes.** `resulting_state`'s expected-strokes value
      must already reflect the penalty stroke's *position* consequence
      (the drop/replay lie), but the formula's "+1" is the *shot just
      taken*, not the penalty stroke — a penalty outcome may actually cost
      *two* strokes relative to a clean outcome (the shot taken, plus the
      penalty stroke itself) depending on how the resulting `GolfState`'s
      "position" is defined (pre- or post-penalty-stroke). This must be
      resolved explicitly at implementation time, not assumed; it is a
      real semantic trap for a naive vectorised formula.
    - **Holed shots.** `expected_strokes` from a terminal/holed
      `resulting_state` must be exactly `0`, by an explicit rule inside
      `expected_strokes` (checking the terminal/holed flag first, per the
      domain-invariant discussion in [section D](#d-golfstate-requirements)),
      not by a distance-based fallback that happens to produce something
      close to zero.
    - **OB.** Typically stroke-and-distance under the Rules of Golf
      (replay from the original position plus a penalty stroke)
      `[UNVERIFIED — subject to M9 Rules-of-Golf gate confirmation]` — this
      changes what "resulting_state" even *means* for an OB outcome (it
      may not be the simulated landing point's classification at all, but
      a reversion to a prior position plus penalty), a genuine special
      case the vectorised formula must branch on, not silently apply
      uniformly.
    - **Unsupported/unknown state.** A classification that cannot resolve
      to a known lie category (e.g. landing wildly outside any mapped
      course feature) must not silently receive some default expected-
      strokes value in a batch computation — it must be flagged (e.g. a
      `nan`/masked-array entry or an explicit unsupported-category
      exception path) so a downstream aggregate (like a mean expected
      Strokes Gained) does not silently average in a meaningless number.
    - **Putting.** As per [section L](#l-putting-penalty-recovery-treatment),
      on-green states use a distinct baseline category but are otherwise
      representable in the same vectorised call — no special-casing
      needed *for the formula itself*, only for which baseline table cell
      is selected.
    - **Coarse-rollout approximation.** Since rollout ([section G](#g-terrain-rollout-v0))
      is applied before classification, it must also be vectorisable
      (a deterministic array-wise offset, not a per-item Python loop) to
      avoid becoming the actual bottleneck in an otherwise-vectorised
      pipeline.

## O. Edge cases

For each: whether it needs an immediate semantic decision now (flagged
`NOW`) or can be reasonably deferred to implementation time (flagged
`DEFER`), and why.

| Edge case | Now / Defer | Rationale |
|---|---|---|
| Hole-in-one | `DEFER` | Purely a terminal/holed-state flag being set correctly by classification (distance-to-pin exactly/effectively zero *and* the ball is confirmed in the hole, not merely near it) — no new semantic category, just correct implementation of the already-identified domain invariant (section D, invariant 4). |
| Shot finishing behind origin | `NOW` (conceptually, already resolved) | Already explicitly supported: `ShotOutcome.downrange_metres`/`ShotRecord.final_downrange_metres` are both explicitly unconstrained/signed (no `ge=0`) specifically to allow this. `GolfState`'s position must simply be computed correctly from a negative downrange value — no new decision needed, just correct arithmetic. |
| Shot crossing OB then finishing in bounds | `NOW` | A genuinely ambiguous Rules-of-Golf question (crossing an OB boundary in flight before returning in bounds is generally *not* penalised under the Rules — only where the ball *comes to rest* matters) `[UNVERIFIED — subject to M9 Rules-of-Golf gate confirmation]` that a naive "did the trajectory cross an OB polygon" classification could get wrong if implemented naively as a line-crossing check rather than a final-position containment check. Irrespective of the exact Rules mechanic, this must be decided explicitly at classification-design time as the conservative default: **classify only the final resting position's containment, never trajectory-crossing**, consistent with how `course/distance.py` already treats "crossings" as a distance-query concept, not a rules concept. |
| Landing in water | `DEFER` (mechanics), `NOW` (category existence) | The category gap itself (`WATER` already exists as a `FeatureType`) is fine; the *penalty/drop-position mechanics* consequence is genuinely complex (Rules of Golf relief options) and reasonably deferred to implementation, provided the classification step itself correctly flags "penalty incurred" now conceptually. |
| Green edge | `NOW` | Point-in-polygon containment is inherently binary; a landing point exactly on a green boundary edge needs an explicit, documented convention (e.g. "on boundary counts as green," matching Shapely's `covers` vs `contains` distinction) — this is a real, easily-inconsistent detail if left undecided. |
| Bunker overlapping/adjacent to green | `NOW` | Course data quality/authoring question: if two `Feature` polygons genuinely overlap (a modelling error or a legitimate green-side bunker cut close to a green), classification needs an explicit precedence rule (e.g. bunker takes precedence over green if both contain the point, or vice versa) — must not be left as "whichever feature happens to be checked first in a list," which would be nondeterministic-by-accident. |
| Unknown/unmapped ground | `NOW` (category existence), `DEFER` (data source) | The **existence** of an explicit `UNKNOWN`/recovery fallback category is a `GolfState`-level invariant already established in section D (must never silently default to `FAIRWAY`); *how* that fallback expected-strokes value is sourced is deferred to the expected-strokes model's own design. |
| Missing course feature geometry (e.g. no rough polygon ever authored for a course) | `NOW` (category existence), `DEFER` (data completeness) | Same reasoning as above — the fallback category must exist by design; whether/how course-data quality is improved is a separate, future course-package concern (M7). |
| Poor course-data quality generally | `DEFER` | A real, ongoing concern but not specific to `GolfState`/expected-strokes design — belongs to course-package/data-provider work (M7) and course-engine data-quality practices generally. |
| Extreme M4 Student-t outcome (a very large, heavy-tail-drawn downrange/lateral value) | `NOW` | Classification must handle a landing point far outside any known course feature's boundary gracefully (falling back to the `UNKNOWN`/recovery category, per the invariant above) rather than raising an unhandled exception — this is a direct, foreseeable consequence of ADR 0006's deliberately heavy-tailed model and must be designed for, not discovered as a bug later. |
| Target override (golfer/candidate target differs from CaddAI's recommended target) | `NOW` (conceptually, already resolved) | Already addressed in [section C](#c-course-relative-transformation): classification must operate against *whatever* target/target-line was actually used for a given `ShotOutcome`, never assume it was the recommended one. |
| Resulting point outside known course extent entirely (e.g. a wild mishit leaving the course's mapped area) | `NOW` (category existence) | Same `UNKNOWN`/recovery fallback applies; must not raise an unhandled exception or silently default to a specific lie. |
| Unsupported `PUTTER` simulation but on-green value state needed | `NOW` (conceptually, already resolved) | Already addressed in [section L](#l-putting-penalty-recovery-treatment): expected-strokes-from-a-green-state does not require `PUTTER` shot simulation to exist. |
| Penalty outcome (mechanics) | `DEFER` | Real Rules-of-Golf relief mechanics are non-trivial and deserve their own focused design; the *existence* of an explicit penalty flag (section D) is the only part needed now. |
| Recovery lie | `DEFER` | Evidence-thinnest category (section H); the category's existence is decided now, its expected-strokes value-sourcing is deferred. |
| Duplicate/overlapping course features | `NOW` | Same as "bunker overlapping/adjacent to green" above — needs an explicit precedence rule, not left implicit. |

## P. ADR requirements

Adapted from the Architect's ADR-trigger assessment (already completed):

| Trigger (`AGENTS.md` §13) | Applies? | Reasoning |
|---|---|---|
| New foundational module | **Yes** | A new top-level module alongside `course`/`player`/`statistics` (per section E's recommendation) is a new foundational domain module by definition. |
| Changes documented dependency direction | **No, for the already-diagrammed edge; partially yes for new edges.** | `simulation -> course` is already shown in `architecture.md`'s target diagram — implementing it (and updating `test_architecture_boundaries.py`'s allow-list) executes documented intent, not changes it. However, new edges `simulation -> caddai.golf_state` and `strategy -> caddai.golf_state` (and later M8/M9/decision-journal edges) are genuinely new graph edges not currently drawn anywhere. |
| Public API contract change | **Yes** | `GolfState`'s field shape is a brand-new, multi-subsystem public contract; an expected-strokes function's interface is a second, later such contract. |
| Canonical units change | **No** | Reuses existing SI/metres conventions and enum-style categorical fields. |
| Module ownership change (`AGENTS.md` §4) | **Yes** | A new module (or extending `simulation`'s/`strategy`'s existing ownership) is an ownership question §4 does not currently answer. |

**Conclusion: at least one ADR would likely be required before `GolfState`
implementation begins** (not written now, per this spike's scope). A
**second, likely-separate** future ADR is anticipated for the
expected-strokes function's interface at its own implementation time,
mirroring ADR 0007's `PopulationPrior` replaceability precedent (per
[section M](#m-provisionality-replaceability)) — the roadmap's own M5
entry already anticipates this ("The concrete expected-strokes interface
this eventually produces is a likely future ADR trigger").

**Comparison to ADR 0007's `PopulationPrior` precedent.** Analogous but
mirrored: ADR 0007 locked a stable *interface* while leaving the
*implementation* free to evolve. `GolfState`'s situation is the mirror
case — the implementation question (how classification derives it) is
less contested than the shape question (which fields exist, how
"minimal" stays minimal, how future consumers — M8, M9, decision journal —
extend it without a breaking change). A `GolfState` ADR would likely need
an explicit "replaceable/extensible contract" clause analogous to ADR
0007's.

Neither ADR is written by this spike.

## Q. Deferred work

Explicitly out of scope for M5.0 / this document, and not designed here:

- `GolfState`'s actual field types, validators, and module code.
- Course-relative classification's actual implementation (point-in-polygon
  logic, precedence rules for overlapping features, the `ROUGH`/generic
  penalty-area `FeatureType` additions).
- Rollout's actual coefficients/config (any numeric value at all).
- Any expected-strokes table, coefficient, or formula.
- Strokes Gained distribution computation/aggregation code.
- Risk/reward summary metrics (upside probability, downside/tail risk,
  penalty/catastrophic probability, scoring probabilities).
- Baseline expected-value strategy/recommendation assembly.
- WHS Course Rating/Slope Rating/Stroke Index data-shape implementation
  (though this spike notes it is "pulled forward" per the roadmap, it is
  not designed here).
- Round lifecycle / decision journal implementation (M8).
- Synthetic validation harness implementation (M9).
- Any ADR text.
- Any GitHub issue creation or sub-issue decomposition beyond the proposal
  in the final section below.
- Pin/flag position data model (`Hole.pin_position` or equivalent) —
  flagged as a real, load-bearing gap (section B/C) but not designed here.
- A stable course/hole identifier/versioning scheme (feeds M7's
  course-package architecture).
- The exact monotonic-interpolation algorithm/library choice for expected
  strokes (only the *category* of approach is recommended, per section J).
- A handicap-band granularity/interpolation scheme specific to
  expected-strokes (distinct from, though possibly reusable alongside,
  `population_prior_config.py`'s existing player-model banding).

## Fixture/scenario validation

`tests/fixtures/sample_course.geojson` currently has two holes, each with
point tee/fairway/green features plus one green polygon (hole 1) and one
bunker polygon (hole 2). This is **insufficient** for future
classification testing without additions, specifically:

- **No rough polygon anywhere** — future classification tests will need
  at least one hole with a rough (or generic "everything not otherwise
  mapped" fallback) area to exercise the `UNKNOWN`/recovery fallback
  category meaningfully, and eventually a real `ROUGH` `FeatureType` once
  it exists.
- **No overlapping/adjacent polygon scenario** — needed to exercise the
  "duplicate/overlapping course features" edge case (section O) once
  classification precedence rules are designed.
- **No polygon positioned to test a point landing exactly on a boundary
  edge** — needed to exercise the "green edge" edge case (section O).
- **No concave polygon fixture** — both existing polygons (a green
  rectangle, a bunker triangle) are convex; a concave fixture would be
  needed to exercise the already-documented ADR 0004 concave-polygon
  non-goal explicitly, once classification is built on top of the same
  convex-only distance-query primitives.
- **No pin/flag data at all** (unsurprising, since `Hole.pin_position`
  doesn't exist) — any future classification/expected-strokes test that
  wants realistic distance-to-pin behaviour will need either a fixture
  extension once `Hole.pin_position` exists, or an explicit
  green-centroid-fallback test path in the interim.

**Recommendation (not implemented here):** when classification
implementation begins, extend `sample_course.geojson` (or add a second,
purpose-built fixture) with a rough/fallback area, at least one
deliberately-adjacent/overlapping pair of polygons, and a boundary-edge
test scenario — a minimal, targeted addition, not a wholesale fixture
redesign.

## Synthetic-validation (M9) compatibility note

The roadmap's M9 (field-readiness validation, evaluation & Rules-of-Golf
gate) will eventually need an offline synthetic round/scenario validation
harness that exercises `strategy`/`simulation` at scale. For that harness
to eventually validate M5's output meaningfully, `GolfState` (and whatever
expected-strokes/Strokes Gained types accompany it) should be:

- **Serialisable/inspectable** — a harness running thousands of synthetic
  scenarios needs to log/compare `GolfState` values across runs, which a
  plain, dependency-free Pydantic model (section E's recommendation)
  supports naturally.
- **Deterministic given a fixed seed** — already a standing requirement
  for `simulation`'s stochastic components (per
  `.github/instructions/tests.instructions.md`); `GolfState`/expected-
  strokes computation must not introduce any new non-determinism (e.g. an
  unseeded random tie-break in a classification precedence rule).
- **Free of any harness-specific coupling** — per
  `docs/architecture.md`'s existing statement, the harness depends
  inward on `strategy`/`simulation`'s existing public interface and must
  never be imported by, or influence the design of, `GolfState`/
  classification/expected-strokes code itself.

No synthetic-validation loop is designed or implemented here — this note
only identifies what M5's output shape should preserve for that future
capability, since M9 was raised as one of `GolfState`'s anticipated
consumers (section E).

## Batch/vectorisation + M6 compatibility note

This note is **language-neutral** — no Rust, Flutter, Protobuf, or FFI
technology is chosen or implied here, consistent with M6 remaining a
future, undecided architecture checkpoint.

- A `GolfState` representation that can be described as a small, fixed set
  of scalar/categorical fields (rather than one embedding arbitrary nested
  mutable objects like a live `Course`/`Hole` graph — per the domain
  invariant in section D) is the representation most likely to translate
  cleanly to **any** future cross-language contract (a schema definition
  language, an FFI struct, a serialisation format) without redesign,
  regardless of which specific technology M6 eventually selects.
- The batch/vectorisation shape recommended in
  [section N](#n-performance-batch-evaluation-implications) (NumPy-array-
  friendly internals, Pydantic only at the public boundary) is already
  precedented by `simulation/sampling.py`'s existing implementation
  approach — continuing that pattern for classification/expected-strokes
  keeps M5's code shape consistent with whatever M6 concludes, rather than
  requiring a redesign specifically because M5 was built Python-object-at-
  a-time.
- No technology decision is made or implied by this note; it only
  observes that a *representation-shape* choice made now (fixed
  scalar/categorical fields, batch-friendly internals) is a low-regret
  choice regardless of M6's eventual outcome.

---

```
DECISION REQUIRED: GolfState ownership and course-relative mapping
```

**Recommended ownership:** `GolfState` (the type) lives in a new, neutral,
dependency-free top-level module (illustratively `caddai.golf_state`),
alongside `course`/`player`/`statistics` as a fourth domain-primitive
module. Course-relative classification (the `ShotOutcome + origin + target
+ course geometry -> GolfState` operation) lives in `caddai.simulation`,
consuming `caddai.course` (an edge already shown in `docs/architecture.md`'s
target diagram) and `caddai.golf_state` (a new edge). Rollout is a
distinct, separately-named, swappable function, also in `caddai.simulation`,
applied before classification.

**Alternatives considered:**
- `GolfState` inside `caddai.simulation` (issue #11's own suggested
  candidate) — lower documentation-diff, but over-scopes `simulation` and
  forces every non-simulation consumer (round model, decision journal, M9
  harness) to depend on an unrelated subsystem for a type.
- `GolfState` inside `caddai.strategy` — rejected: risks inverting the
  documented `strategy -> simulation` dependency direction, or forces
  classification logic into the wrong module.

**Dependency implications:** new edges `simulation -> caddai.golf_state`
and (eventually) `strategy -> caddai.golf_state`, plus later M8 (round
model), M9 (synthetic harness), and decision-journal edges into the same
neutral module. `test_architecture_boundaries.py`'s allow-list will need
updating for `simulation -> caddai.course` (already-documented-but-not-yet-
encoded) and for the new `caddai.golf_state` edges.

**ADR implications:** a new foundational module, a new public API
contract, and a new module-ownership question (`AGENTS.md` §4 does not
currently name an owner for a fourth domain-primitive module) together
trigger the ADR requirement per `AGENTS.md` §13 — an ADR is expected before
implementation begins, not written by this spike.

**Migration implications:** lowest-churn of the three options for a future
M6 production-system/runtime decision, since a plain, dependency-free value
type is the representation shape least coupled to any one subsystem's
future migration timeline (see the Batch/vectorisation + M6 compatibility
note above).

```
DECISION REQUIRED: Expected-Strokes V0
```

**Recommended option:** a monotonic, interpolated lookup table, conditioned
on distance-to-hole and lie/category, with an explicit handicap/ability-
band axis (combining options 5 and 6 from section I) — deliberately not a
regression/ML approach (no data to fit against) and not a raw parametric
curve reused from a specific published fit (same licensing risk as a raw
table, with less transparency).

**Alternatives considered:** plain lookup table without interpolation
(discontinuous at bucket edges); parametric curve (licensing risk on
reused coefficients, or no data to fit CaddAI's own); regression model (no
dataset currently available to fit against); single-baseline table without
handicap conditioning (fails the tour-vs-amateur transferability concern
that is this domain's single most important structural fact).

**Evidence:** ⚠️ **limited to stable, well-known public golf-analytics
knowledge, NOT verified via live tooling this session** — Mark Broadie's
Strokes Gained methodology and the USGA/R&A World Handicap System's
Strokes-Gained-based methodology are the two candidate evidence bases
identified, both flagged `[UNVERIFIED THIS SESSION — recommend human
verification]` throughout section H. **This does not meet M4.0's
verification bar.**

**Consequences:** enables a defensible, distance/lie/ability-conditioned
expected-strokes baseline without requiring data CaddAI does not have;
defers exact numeric content and licensing resolution to a follow-up,
explicitly gated implementation step.

**Provisional assumptions:** that a licensable or first-party-derivable
distance/lie/ability-conditioned baseline can be found or built at all;
that the roadmap's own required "amateur/handicap-conditioned" framing
(not tour-only) is achievable from currently identifiable sources — **not
confirmed this session.**

**Licensing implications:** every candidate source identified in section K
carries an "Unclear" or worse licensing status except CaddAI's own
(not-yet-collected) future data — **no numeric content from any external
source should be embedded until the human explicitly verifies and
documents its licensing terms.**

**Implementation implications:** an implementation sub-issue must not be
opened until (a) the human has independently re-verified sources per the
tooling-limitation disclosure at the top of this document, and (b) the
roadmap's own required decision gate has explicitly accepted this spike's
findings — mirroring M4.0's own gating precedent exactly.

---

## Likely future M5 implementation decomposition (proposal only, not created as issues)

**None of the following are created as GitHub issues by this task.** This
is a candidate ordering only, for the human/Orchestrator to review:

1. **`GolfState` domain/state contract** — new neutral module, minimal
   fields per section D, gated on an ADR per section P.
2. **Course-relative mapping** — classification + rollout in
   `caddai.simulation`, including the `ROUGH`/generic-penalty-area
   `FeatureType` additions and new point-in-polygon geometric primitives
   identified in section B.
3. **Expected-strokes V0** — gated on independent human verification of
   section H/K's sources and the roadmap's required decision gate; not to
   be opened until that gate passes.
4. **Strokes Gained distribution-aware candidate evaluation** — consumes
   1–3 above; produces the full outcome distribution (never a single
   scalar), per the roadmap's explicit requirement.
5. **Baseline expected-value strategy & recommendation assembly** —
   consumes 1–4; the first structured, trustworthy `strategy`
   recommendation maximising expected Strokes Gained as its baseline
   objective.

Ordering follows strict data dependency (each item consumes the previous).
Item 3's gate is the most consequential sequencing constraint: items 4–5
cannot meaningfully begin before it, and item 3 itself cannot begin before
its own human-verification/decision-gate step completes.
