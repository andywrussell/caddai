# M5.0 Research Spike: Course-Relative `GolfState` & Expected-Strokes V0

> **Status: research/design spike only.** No production code is changed by
> this document. No `GolfState`, classification, rollout, expected-strokes,
> Strokes Gained, strategy utility, round lifecycle, WHS calculation, or
> synthetic-validation-harness code is implemented here. No ADR or GitHub
> issue is created by this document. This mirrors
> [docs/research/m4-probabilistic-golfer-model.md](m4-probabilistic-golfer-model.md)'s
> (M4.0's) format and rigour, per the M5 roadmap entry and GitHub issue #11.

## VERIFIED EXTERNAL EVIDENCE vs. STILL UNVERIFIED — read before trusting section H

**Amendment (dated 2026-09-01):** this document was amended after a
follow-up session that had live web-fetch/browsing tool access. That
session performed live web research and verified the sources listed in
[section H](#h-expected-strokes-evidence-review) and
[section K](#k-datalicensing-table) below by directly fetching and reading
each source — **this supersedes the original document's "no live web tool
available" disclosure**, which applied only to the first drafting session
and no longer describes the evidence in sections H/K/the amateur-evidence
subsection.

A small number of items remain genuinely unverified even after this
amendment — see
["STILL UNVERIFIED / PROPRIETARY / LICENSING-UNCLEAR"](#h-expected-strokes-evidence-review)
in section H for the explicit list: the official USGA/R&A World Handicap
System primary PDF documentation, PGA TOUR's explicit ShotLink licensing
terms, the University of Padova thesis's full text, and Shot Scope's/
Arccos's underlying numeric benchmark tables (as opposed to their
marketing/feature descriptions). These gaps are recorded honestly, not
silently dropped.

Sections outside H/K (e.g. sections A–G on `GolfState` architecture and
ownership) were not the subject of this amendment's live research and
remain unchanged in substance — this amendment only narrows the
expected-strokes evidence/decision, not the `GolfState`
architecture/ownership conclusions.

**Second amendment (dated 2026-09-01, same day).** A further amendment
added [section H.2](#h2-value-architecture-separating-benchmark-player-adjustment-and-strategic-risk),
folding in a CaddAI Architect review of how the verified evidence above
should be applied to an expected-strokes *value architecture* (separating
a neutral benchmark, a player-specific adjustment, and strategic risk into
distinct layers). This second amendment does **not** redo, weaken, or add
to the external evidence verified above — it only changes how that
evidence is applied to the value contract in sections M/N and the decision
gates at the end of this document.

**Third amendment (dated 2026-09-02) — human decisions recorded.** The
human has now reviewed and made decisions on both `DECISION REQUIRED`
blocks at the end of this document:

- `DECISION REQUIRED: GolfState ownership and course-relative mapping` is
  **APPROVED** — semantic architecture direction only (course/`GolfState`/
  `simulation`/expected-strokes/`strategy` responsibilities, per the
  recorded architecture); exact Python APIs/implementation details are not
  approved by this. A dedicated `GolfState`/course-relative-state ADR is
  still required before implementation and is **not** created by this
  amendment.
- `DECISION REQUIRED: Expected-Strokes / State-Value Architecture` is
  **APPROVED** — long-term = Architecture Option B (neutral `E_base` +
  separate `Delta`); V0 = Architecture Option C (`E_player(state) =
  E_base(state)`, no player-adjustment layer in V0); Architecture Option A
  (single ability-conditioned function) is **not selected** as the
  long-term core value architecture.
- The numeric expected-strokes baseline (`FOLLOW-ON REQUIRED: Expected-
  Strokes Numeric Baseline / Data Source`) **remains UNRESOLVED and is
  NOT approved by this amendment** — approving the value architecture is
  not the same as approving a numeric model, table, or data source.

This amendment only **records decisions already made** by the human. It
does not introduce new research, does not redo or weaken any verified
evidence/reasoning already in this document, and does not reopen or
re-debate the architecture. See the `HUMAN DECISION: APPROVED (2026-09-02)`
blocks under each `DECISION REQUIRED` heading, and the new
["R. M5.0 resolution status"](#r-m50-resolution-status-2026-09-02-decision-recording-amendment)
and
["S. Next work after PR #79"](#s-next-work-after-pr-79-sequencing-guidance-only--no-issues-created)
sections near the end of this document, for the full detail.

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
   yet.** A follow-up amendment (2026-09-01) performed live-verified web
   research (see [section H](#h-expected-strokes-evidence-review)) and
   found the distance/lie/ability-conditioned expected-strokes *concept*
   well-supported by independent, verified sources, but found **no**
   legally reusable public numeric baseline table or dataset. A second
   amendment the same day (see
   [section H.2](#h2-value-architecture-separating-benchmark-player-adjustment-and-strategic-risk))
   further found that the ability/handicap-band part of this concept
   belongs to a future, separately-gated, **unscheduled** player-adjustment
   layer (`Delta`/Layer C), not to the neutral V0 benchmark
   (`E_base`/Layer B) — see the reconciled
   [section J](#j-recommended-expected-strokes-v0). V0's own candidate
   model family (a monotonic, distance/lie-conditioned interpolation, no
   handicap axis) is recorded as a **leading engineering candidate for
   `E_base`'s model family/contract shape only**, not an approved or
   provisionally-adopted V0. A separate, still-unresolved follow-on
   decision covers the numeric baseline/data source itself (see the
   `FOLLOW-ON REQUIRED` block at the end of this document).
5. **This spike recommends, but does not decide,** the `GolfState`
   ownership question, the expected-strokes contract direction, or the
   still-open expected-strokes numeric-baseline/data-source follow-on —
   see the decision/follow-on blocks at the end of this document.
6. **Amendment (2026-09-02):** the two decision gates in item 5 are now
   marked `HUMAN DECISION: APPROVED` — `GolfState` ownership/course-
   relative mapping (architecture direction only, ADR still required) and
   the expected-strokes/state-value architecture (long-term Architecture
   Option B, V0 Architecture Option C, Option A not selected). This
   spike still only **recommends, and does not decide**, the one item
   that remains genuinely open: the expected-strokes numeric-baseline/
   data-source follow-on (see the `FOLLOW-ON REQUIRED` block, still
   unresolved). See [section R](#r-m50-resolution-status-2026-09-02-decision-recording-amendment)
   for the full resolution status.

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

> **Amendment note (2026-09-01):** this amendment **reconfirms, and does
> not reopen**, the neutral-module ownership conclusion below. Narrowing
> the expected-strokes evidence/decision (sections H–K) has no bearing on
> `GolfState`'s ownership — `GolfState` is a physical/course-relative state
> contract, while expected strokes is a value model that consumes that
> contract; evidence quality and numeric-model maturity for expected
> strokes are orthogonal to where the state type lives. See the Architect's
> confirmation items 1–3 and 7 folded into this section and
> [section F](#f-course-relative-classification-ownership) below.

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

### Rejected options — reconfirmed (Architect item 7, 2026-09-01 amendment)

- **`GolfState` inside `strategy` "merely for convenience" — REJECTED.**
  It would force `simulation` (the classifier) to import `strategy` to
  construct/return the type it produces, inverting the documented
  `strategy -> simulation` direction (`AGENTS.md` §3/§13) — a structural
  violation, not a style preference.
- **`strategy` performing low-level course geometry classification —
  REJECTED.** Duplicates `simulation`'s (and `course`'s) capability, risks
  correctness drift, risks an undocumented `strategy -> course` edge. See
  [section F](#f-course-relative-classification-ownership) for the full
  reasoning.
- **Course-provider-specific data leaking into `GolfState` — REJECTED.**
  Would reintroduce an implicit `course`/provider dependency into what
  must remain a leaf type, undermining portability and violating
  `course`'s non-goal of golfer-semantics leakage (see domain invariant 8
  in [section D](#d-golfstate-requirements)).

## F. Course-relative classification ownership

> **Amendment note (2026-09-01):** this amendment **reconfirms, and does
> not reopen**, the classification-ownership conclusion below, and the
> dependency-direction reasoning behind it. See the Architect's
> confirmation item 2: classification remains a `simulation`
> responsibility; edges are `simulation -> course` (already documented)
> and `simulation -> caddai.golf_state` (new, one-directional, into the
> neutral module only) — no reverse edges, and no `strategy`-owned
> low-level geometry classification (see the rejected-options list at the
> end of [section E](#e-golfstate-ownership-options)).

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

> **Amendment note (2026-09-01), Architect item 6:** softened per the
> Architect's confirmation below. The rollout-stage boundary itself (a
> distinct, separately-named, swappable step inside `simulation`, never
> fused with classification) is unchanged and still correct.

**Provide a replaceable rollout/final-position transformation stage.** V0
may use a deliberately coarse deterministic rollout approximation (option
B above) if defensible parameters can be established. If they cannot, the
system must support an explicit **identity/no-rollout approximation with
known limitations** (option A above, visibly labelled as such) rather than
fake precision. Either way, rollout is applied as a distinct,
separately-named, swappable step from classification, not fused into one
non-decomposable operation — this does not commit to specific rollout
constants/percentages here; that remains an implementation-time decision
once (or if) defensible parameters exist.

**Ownership (from the Architect's analysis):** rollout and classification
should live in the **same module** (`simulation`), but as two distinct,
separately named, swappable functions — never merged into one operation.
Reasoning: rollout approximation and classification answer conceptually
different questions with very different maturity trajectories (rollout is
an explicit placeholder pending real bounce/terrain physics — including,
if no defensible parameters exist, a labelled identity transform — while
classification is comparatively stable once course geometry exists). This
mirrors the existing pattern of M4.7's `apply_environment_transform` and
M4.8's sampling being kept as separately composable steps (via the
`ShotOutcomeSampler` `Protocol`) specifically so a technique — including a
trivial identity function — can be swapped without changing the call
shape or downstream consumers.


## H. Expected-strokes evidence review

> **Amendment (2026-09-01):** this section was rewritten after a follow-up
> session with live web-fetch/browsing tool access. Every source below was
> directly fetched and read this session (not recalled from training
> knowledge), unlike the original version of this section. This
> supersedes every `[UNVERIFIED THIS SESSION — recommend human
> verification]`-tagged claim previously in this section — those claims
> are replaced by the verified findings below, or explicitly carried
> forward into
> ["STILL UNVERIFIED / PROPRIETARY / LICENSING-UNCLEAR"](#still-unverified--proprietary--licensing-unclear)
> where genuinely still unverified. No exact numeric expected-strokes
> table value is stated or invented anywhere in this section — every
> quantitative figure below is a verified, directly-cited figure from a
> named source, not an invented or interpolated one.

### VERIFIED EXTERNAL EVIDENCE

1. **Broadie, M. (2011). "Assessing Golfer Performance on the PGA TOUR."**
   PDF: https://www.columbia.edu/~mnb2/broadie/Assets/strokes_gained_pga_broadie_20110408.pdf
   (to appear in *Interfaces*, a peer-reviewed INFORMS journal). VERIFIED
   full text (31 pages, downloaded and read this session). Uses PGA TOUR
   ShotLink data, ~8 million shots, 299 golfers with 120+ rounds,
   2003–2010. The paper explicitly thanks "the PGA TOUR for providing the
   ShotLink data" — this acknowledgment language confirms ShotLink access
   was granted/restricted by the PGA TOUR to the author, not a publicly
   downloadable dataset. Population: PGA TOUR professionals only
   (tour-average baseline) — **not** an amateur/handicap population.
   **Classification: peer-reviewed academic source; tour-only population;
   underlying ShotLink data NOT publicly accessible/redistributable
   (methodology described, data proprietary).**
2. **Broadie, M. (2008). "Assessing Golfer Performance Using
   Golfmetrics."** Chapter 34 in *Science and Golf V: Proceedings of the
   2008 World Scientific Congress of Golf*, eds. D. Crews & R. Lutz,
   Energy in Motion Inc., Mesa, Arizona, pp. 253–262. PDF:
   https://www.columbia.edu/~mnb2/broadie/Assets/broadie_wscg_v_200804.pdf.
   VERIFIED full text (9 pages, downloaded and read this session) — **the
   primary amateur-relevant academic source, peer-reviewed conference
   proceedings.** Verified facts:
   - The Golfmetrics database (at time of writing) contained "almost
     40,000 shots representing about 500 rounds of golf from over 130
     golfers on six courses... primarily during 2005–2007." Golfer ages
     9–70, scores 64–120. Includes PGA/LPGA tour pros, club
     professionals, and amateurs.
   - Golfers were divided into 5 skill groups by score range: Pro1
     (64–71), Pro2 (72–79), Am1/low-handicap (70–83), Am2/middle-handicap
     (84–97), Am3/high-handicap (98–120).
   - Defines **"fractional par"**: an expected-strokes-to-holeout quantity
     conditioned on distance AND starting lie/situation (fairway, rough,
     sand, tee, green, putt distance), "estimated from Golfmetrics data,"
     explicitly benchmarked to **"a scratch golfer's average shot from a
     given situation"** — i.e. ONE population baseline (scratch), not a
     separate baseline curve fitted per handicap band, in this specific
     paper. Illustrative example values given in the paper (not a full
     table): a 140-yd par-3 has fractional par 3.2; a 200-yd hole has
     fractional par 3.5; a 14-ft putt has fractional par 1.8.
   - **Shot value formula: v = f_s - f_e - 1** (fractional-par-at-start
     minus fractional-par-at-end minus 1) — this is EXACTLY CaddAI's
     roadmap Strokes Gained formula
     (`strokes_gained = expected_strokes(current_state) - (1 +
     expected_strokes(resulting_state))`), confirming the roadmap's SG
     formula is a direct, verified application of Broadie's original
     methodology, not an invented convention.
   - Defines "awful shot" as shot value < -0.8, "great shot" as > +0.8 —
     a precedent (from a peer-reviewed source) for a severe-outcome/tail
     classification, relevant to M4's Student-t tail-risk discussion.
   - **Table 1 (verified, real quantitative data)** shows, by skill group,
     putting 50%-holing-probability distance (ft), sand-shot 2-putt-avg /
     sand-save %, and long-tee-shot median/75th-percentile distance (yds)
     and directional standard deviation (degrees): Pro (64–79): 8.2 / 30 /
     50% / [FRL 16%] / 297yd / 4.0°; Am1 (70–83): 5.8 / 25 / 26% / [FRL
     30%] / 248yd / 5.4°; Am2 (84–97): 5.1 / 19 / 17% / [FRL 40%] / 237yd
     / 6.4°. This is **real, verified, peer-reviewed quantitative evidence
     that ability/handicap materially affects distance, dispersion, and
     short-game/sand performance** — but it evidences ability-conditioned
     *performance metrics*, not a full ability-conditioned
     expected-strokes-by-distance-and-lie table (the paper's "fractional
     par" function itself is fit once, to the whole dataset, against a
     single scratch-golfer benchmark).
   - No data-availability/open-license statement exists in the paper — it
     is a conference proceedings chapter, not accompanied by a public
     dataset release.
   **Classification: peer-reviewed academic source; SMALL (n≈130 golfers,
   ~40,000 shots), DATED (2005–2007), narrow (6 courses) amateur sample;
   provides real evidence for the ability→performance relationship and
   for the distance+lie-conditioned expected-strokes CONCEPT; the
   underlying dataset itself was never published as open/redistributable
   data.**
3. **Golfmetrics today** (https://legacy.golfmetrics.com/ and
   https://new.golfmetrics.com/home) — VERIFIED fetched this session.
   Legacy site states verbatim: "The Golfmetrics effort was begun nearly
   fifteen years ago and its database of over 100,000 amateur golf shots
   allows the accurate benchmarking of golfers of all skill levels." New
   site markets itself as "the leading app for Strokes Gained... Brought
   to you by the inventor of Strokes Gained himself, Mark Broadie." It is
   now a commercial, account-gated app (login at app.golfmetrics.com).
   **Classification: the ~100,000-shot amateur database is NOT publicly
   downloadable or redistributable — it is proprietary and monetized
   inside a commercial app. Confirms the CONCEPT (amateur benchmarking
   across skill levels) at larger scale than the 2008 paper, but is not a
   usable/embeddable data source.**
4. **DataGolf, "Using the true strokes-gained metric in amateur golf"**
   (https://datagolf.com/true-strokes-gained-in-amateur-golf, dated May
   7, 2020). VERIFIED fetched this session. DataGolf's amateur SG
   coverage is built from events eligible for the World Amateur Golf
   Rankings (WAGR) plus U.S. college golf events — i.e. **elite
   competitive amateur golf, not recreational handicap-index golfers.**
   **Classification: important population mismatch — "amateur" here means
   near-scratch competitive golfers, not CaddAI's target population.
   Evidence/methodology only, not a usable population match.**
5. **Arccos Golf, "Strokes Gained Analytics" marketing page**
   (https://www.arccosgolf.com/pages/strokes-gained-analytics). VERIFIED
   fetched this session. Explicit marketing text: "Benchmark against your
   goal handicap, tour pros, or golfers at your level. See exactly where
   you stand." **Classification: confirms handicap-conditioned SG
   benchmarking is an established, shipping commercial product concept,
   built on Arccos's own proprietary GPS-sensor shot database. No public
   data-sharing/open-license terms found. Evidence for the CONCEPT's
   commercial viability; proprietary, not a usable data source.**
6. **Shot Scope, "Strokes Gained" feature page**
   (https://shotscope.com/uk/discover/features/strokes-gained/). VERIFIED
   fetched this session. Explicit text: "With every shot you hit on the
   golf course we collect two data points, where the ball starts, and
   where the ball ends, taking into consideration lie type and distance.
   We then use this data to give each shot a Strokes Gained (SG) value...
   golfers can set a handicap benchmark, allowing them to compare their
   own game against their target handicap." Shot Scope also sells an
   "Annual Golf Report" as a paid ebook
   (https://shotscope.com/uk/shop/products/ebooks/shot-scope-data-report-26/).
   **Classification: same conclusion as Arccos — confirms the concept
   commercially, proprietary data, monetized rather than freely published
   (evidence that even aggregate insights are sold, not given away).**
7. **University of Padova thesis**: "Statistica e golf: Modelli
   predittivi per il calcolo degli Strokes Gained" ["Statistics and golf:
   predictive models for calculating Strokes Gained"], author Mirko
   Gabriel Briglia, advisor Prof. Francesco Lisi, Department of
   Statistical Sciences, University of Padova. Repository:
   https://thesis.unipd.it/handle/20.500.12608/77754 (direct PDF URL
   found:
   https://thesis.unipd.it/retrieve/e4062e48-de97-4e0e-810b-bf6a06a0a9cb/Briglia_MirkoGabriel.pdf).
   A search-engine-cached abstract snippet (Italian) was recoverable:
   "Questo studio esplora l'applicazione delle analisi statistiche
   avanzate nel gioco del golf, con un focus particolare sugli Strokes
   Gained... Basato su dati raccolti tra il 2023 e il 2024, lo studio
   propone una metodologia alternativa per calcolare il benchmark delle
   performance nel golf attraverso un'ampia gamma di [snippet
   truncated]" (translation: "explores advanced statistical analysis
   applied to golf, focused on Strokes Gained... based on data collected
   2023–2024, proposes an alternative methodology for calculating
   performance benchmarks across a wide range of [truncated]"). **BOTH
   the repository page and the direct PDF URL returned a Cloudflare
   bot-challenge this session ("Just a moment...") — full text,
   methodology, sample population, and results could NOT be verified this
   session.** **Classification: identified and partially verified
   (title/author/advisor/institution/abstract snippet only) via
   search-engine caching; full content inaccessible this session; it is
   an unreviewed student thesis (not peer-reviewed), so its evidence tier
   is lower than the Broadie sources even once/if accessed. Flagged
   explicitly for human follow-up with non-automated browser access — see
   "STILL UNVERIFIED" below.**
8. **Wikipedia, "Handicap (golf)"**
   (https://en.wikipedia.org/wiki/Handicap_(golf), includes the "World
   Handicap System" section). VERIFIED fetched this session (full section
   text read). Confirms WHS mechanics: Course Rating (~67–77 for a par-72
   course; average "good score" for a scratch golfer), Slope Rating
   (55–155 range, 113 = standard difficulty), Stroke Index (per-hole 1–18
   handicap-stroke allocation), Course Handicap = handicap_index ×
   slope_rating / 113 (+ course_rating - par for WHS/EGA/RSA systems),
   handicap differential = (adjusted_score - course_rating) × 113 /
   slope_rating. WHS launched globally in 2020, jointly governed by USGA
   and The R&A. **Critically: WHS's entire mechanism is ROUND-LEVEL
   scoring/handicap arithmetic relative to par via Course/Slope Rating —
   it is NOT a distance/lie-granular expected-strokes-to-holeout model.**
   **Classification: verified secondary source (Wikipedia, well-cited);
   confirms — does not merely assume — the architectural separation
   already in the CaddAI roadmap: WHS Course Rating/Slope Rating/Stroke
   Index data is scoring/handicap POLICY data (M8's concern), categorically
   distinct from a Broadie-style shot-level expected-strokes-to-holeout
   VALUE model (M5's concern). Reusable as methodology confirmation; not
   a numeric source for expected-strokes-to-holeout at all.**

### STILL UNVERIFIED / PROPRIETARY / LICENSING-UNCLEAR

- **Official USGA/R&A World Handicap System PDF documentation** — could
  not be fetched directly this session (usga.org returned an Akamai
  "Access Denied" to automated requests; a guessed randa.org URL 404'd) —
  only the Wikipedia secondary summary (item 8 above) was accessible.
- **PGA TOUR's explicit ShotLink licensing/access-terms page** — not
  directly located this session; the access restriction is inferred from
  Broadie 2011's acknowledgment language (item 1 above), not from an
  explicit licensing document.
- **The Padova thesis's full text, methodology, sample population, and
  results** (item 7 above) — inaccessible this session (Cloudflare
  bot-challenge on both the repository page and the direct PDF URL); only
  title/author/advisor/institution and a cached abstract snippet were
  recoverable.
- **Shot Scope's and Arccos's own underlying numeric benchmark tables**
  (as opposed to their marketing/feature-page descriptions, items 5/6
  above) — not accessed this session; both companies' benchmarking
  numbers remain proprietary and unpublished as far as this session could
  determine.
- **Golfmetrics's ~100,000-shot amateur database composition** (item 3
  above) — the aggregate size is publicly stated on the legacy marketing
  page, but the underlying shot-level data is not publicly downloadable
  or inspectable; it is now folded into a commercial, account-gated app.

These gaps are recorded honestly as **not resolved by this amendment**,
not silently dropped — see the `FOLLOW-ON REQUIRED` block at the end of
this document for how they might be resolved in a future, narrower
research pass.

### OVERALL CONCLUSION

**A. EXPECTED-STROKES SEMANTICS/CONDITIONING: WELL-SUPPORTED.** Multiple
independent, methodologically different, verified sources (two
peer-reviewed Broadie papers using real distance+lie+scratch/tour-
benchmark data; three independent commercial products — Golfmetrics,
Arccos, Shot Scope — all convergently built around "distance + lie +
ability/handicap benchmark") confirm that expected-strokes-style models
conditioned on distance, lie/state, and golfer ability are a
well-established, evidence-backed, commercially-proven CONCEPT.

**B. SHIPPABLE NUMERIC BASELINE: NOT CURRENTLY SUPPORTED.** Every numeric
source identified this session is either (i) tour-only and
access-restricted (ShotLink/Broadie 2011), (ii) a small (n≈130), dated
(2005–2007), narrow (6-course) academic amateur sample never published as
open data and now folded into a commercial app (Golfmetrics), (iii) a
proprietary commercial product with no public licensing terms found
(Arccos, Shot Scope), or (iv) an inaccessible-this-session,
non-peer-reviewed student thesis of unknown reliability (Padova). **No
public, sufficiently-documented, legally-reusable numeric
expected-strokes-by-distance/lie/handicap-band table or dataset was found
or verified.**

Therefore the concrete monotonic-interpolation-plus-handicap-band V0
proposal from the original document must be **downgraded from
"recommended V0" to "leading engineering candidate for the model
FAMILY/contract shape, pending a still-unresolved
numeric-baseline/data-source decision."** It is not presented as an
approved or even provisionally-adopted V0 model anywhere in this document.

> **Reconciling note (2026-09-01, second amendment):** the value-
> architecture separation in
> [section H.2](#h2-value-architecture-separating-benchmark-player-adjustment-and-strategic-risk)
> further splits this conclusion. The **handicap/ability-band axis**
> specifically is now understood to belong to a future, separately-gated,
> **unscheduled** `Delta`/Layer C player-adjustment (Architecture Option
> B), never to V0's neutral `E_base`/Layer B benchmark (Architecture
> Option C, per the amended decision gate). Only the **monotonic,
> distance/lie-conditioned interpolation part** (no handicap axis) remains
> the candidate model family for `E_base` itself — see the reconciled
> [section J](#j-recommended-expected-strokes-v0).

## H.1 Amateur evidence extra scrutiny

Using only the verified findings above:

- **(a) Does expected strokes change meaningfully with ability?**
  **Evidence indirectly supports YES**: Broadie 2008's Table 1 evidences
  material skill-band differences in the underlying *performance metrics*
  (putting-holing distance, sand-save rate, tee-shot distance/dispersion,
  cited in full under item 2 above) that expected-strokes-to-holeout is
  computed from — the paper does not itself report a separate
  expected-strokes-by-distance/lie curve per skill band (see (b) below),
  so this is a defensible inference from verified performance-metric
  differences, not a direct measurement of expected strokes varying by
  ability.
- **(b) Are handicap bands empirically supported?** **Partially** —
  Broadie 2008 divides golfers into discrete skill/score bands and finds
  real differences, but does not itself fit a separate
  expected-strokes-by-distance/lie curve per band (its "fractional par"
  function is fit once, to a scratch baseline). Commercial products
  (Arccos/Shot Scope) claim to do per-band/per-goal-handicap
  benchmarking, but their methodology/data are proprietary and unverified
  this session.
- **(c) How broad are existing amateur samples?** **Narrow** — Broadie
  2008's academic sample is ~130 golfers/6 courses/2005–2007;
  Golfmetrics's current commercial database (~100,000+ shots) is broader
  but proprietary and unverified in composition; DataGolf's "amateur"
  sample is elite/competitive, not representative of CaddAI's target
  population.
- **(d) Does handicap-conditioning appear preferable to a single
  universal baseline?** **YES conceptually** — multiple independent
  sources converge on this.
- **(e) Is there sufficient PUBLIC numeric evidence to construct it
  today?** **NO.**

**The evidence supports the CONCEPT but not the NUMBERS.**

## H.2 Value architecture: separating benchmark, player-adjustment, and strategic risk

**Amendment (dated 2026-09-01, second amendment).** This subsection folds
in a CaddAI Architect review commissioned specifically to resolve a risk
identified in section M's previous "ability-conditioned contract
direction" subsection (now superseded — see section M below): a single
`expected_strokes(state, ability_context?) -> value` contract risks
conflating three genuinely distinct questions into one function and one
number. This subsection separates them explicitly. Nothing here revisits
or weakens section H/H.1/K's verified evidence findings — it only changes
*how that evidence is applied* to a value contract.

### The problem being fixed

A single expected-strokes function that takes an optional ability/handicap
parameter can silently conflate:

1. **The benchmark/reference value of a golf state** — "what is the
   reference expected strokes to hole out from here, against a fixed,
   comparable population?"
2. **How difficult that state is for a SPECIFIC golfer** — "how much
   harder or easier is this state for THIS golfer than the reference
   population?"
3. **What strategic risk/objective should drive a recommendation** —
   "given a distribution of possible outcomes and their values, which
   candidate shot should CaddAI actually recommend, and how much risk
   should it take on?"

These are answerable independently, have different evidence bases
(question 1: section H's Broadie/commercial-product evidence; question 2:
golfer-specific performance history, out of scope for M5; question 3:
belongs to later strategy/M8 risk-policy work), and must not be collapsed
into one function or one number.

### Four conceptual layers

- **Layer A — physical player model.** Already implemented in M4
  (`PlayerShotDistribution` → a distribution of physical shot outcomes).
  Answers "where is THIS golfer likely to hit the ball?" Not redesigned
  here.
- **Layer B — baseline/benchmark state value.** `E_base(state)`. Answers
  "what is the reference expected strokes to hole out from this
  `GolfState`?" Independent of current score, strategic goal, risk
  appetite, or WHS policy — and independent of player identity/handicap
  too: the function itself takes no player/ability parameter, because a
  benchmark needs a fixed, single reference population to remain
  comparable across golfers and over time (matching section H item 2's
  description of Broadie's "fractional par" function, fit once against a
  single scratch-golfer benchmark, not per skill band).
- **Layer C — player-adjusted state value.** `E_player(state,
  player_context) = E_base(state) + Delta(state, player_context)`. Answers
  "how difficult is this state for THIS golfer?" Examples of what `Delta`
  might eventually capture: bunker play, wedge play, recovery play,
  putting strength, rough performance. May be identity/no-op in V0 (see
  below). Handicap is one possible input to a future `Delta`, never
  assumed to be the only or final one (see the evidence-sources
  discussion below).
- **Layer D — strategic objective/risk.** Consumes a distribution of
  player-relative values plus round/scoring/goal/risk context to produce a
  recommendation. Belongs to later strategy/M8 work, not this document.
  Must **not** encode "higher handicap = more/less risk" as a universal
  rule (see the rejected-options note below).

### Three value architectures compared

Labelled **Architecture Option A/B/C** — deliberately distinct from the
Layer A–D labels above and from section I's numbered model-family options
1–6, to avoid confusion between "which conceptual layer" and "which
overall value-architecture shape" and "which numeric model family."

**Architecture Option A — ability-conditioned expected strokes:**
`E(state, ability_context) -> value`, a single function taking both state
and ability context.

- *Conceptual simplicity:* one function, one call site — simplest surface
  area.
- *Fit to verified evidence:* poor — section H's evidence is either
  single-reference-population (Broadie's fractional par) or
  ability-differences at the *performance-metric* level (section H.1),
  never a fitted, combined distance+lie+ability-conditioned expected-
  strokes surface. No verified source publishes this combined shape.
- *Data requirements:* highest — needs a numeric surface conditioned on
  distance, lie, AND ability simultaneously, which is both unresolved
  (section K) and, per the evidence, may not exist publicly at all.
- *Meaning of SG:* forecloses conventional, benchmark-comparable Strokes
  Gained semantics (see the SG discussion below) — SG becomes
  player-relative by construction, with no way to recover the
  conventional benchmark quantity without a second, separate computation.
- *Ability to personalise later:* none needed — already "personalised" by
  construction, but at the cost of losing the neutral benchmark.
- *Coupling risk:* high — couples the benchmark concept and the
  player-adjustment concept into one signature, one data source, and one
  future implementation, so upgrading either independently (e.g.
  refitting the benchmark table without touching player-adjustment, or
  vice versa) is harder than necessary.

**Architecture Option B — neutral baseline + player adjustment:**
`E_base(state) + Delta(state, player_context) = E_player(state)`, two
named, composed functions.

- *Separation:* clean — `E_base` depends only on the neutral `GolfState`
  type; `Delta` depends on golfer-ability data
  (`caddai.player`/`caddai.statistics`, already-approved edges, no new
  edge introduced).
- *Data requirements:* `E_base` needs a single-reference-population
  numeric baseline (unresolved — see the `FOLLOW-ON REQUIRED` block);
  `Delta` needs its own, separately-unresolved ability-conditioned
  evidence/data, gated on its own future decision.
- *SG compatibility:* preserves conventional, benchmark-comparable SG via
  `E_base` alone, while still allowing a distinctly-named
  player-relative SG quantity computed from `E_player` (see below) — both
  available, never conflated.
- *Future personalisation:* `Delta` can be introduced later purely as a
  `Delta`-only change, with no signature break to `E_base` or to any
  consumer already built against it.
- *Contract complexity:* two named interfaces plus one composition layer
  — more surface area than Option A, but each piece stays small and
  independently testable.
- *Replaceability:* excellent — mirrors ADR 0007's `PopulationPrior`
  stable-interface/replaceable-implementation precedent, applied to two
  independently-swappable pieces instead of one.
- *M6/batch portability:* both `E_base` and `Delta` are representable as
  pure array-in/array-out transforms over a fixed scalar/categorical
  schema (see the batch-implications note added to section N below); a
  single fused function (Option A) would hide two independently-
  reimplementable pieces behind one opaque call.

**Architecture Option C — neutral baseline only for V0:**
`E_player(state) = E_base(state)` (i.e. `Delta` is identity/no-op).

- *MVP viability:* good — ships the one piece of evidence-grounded work
  that is actually gated on a resolvable (if still open) baseline
  problem, per section H/K, without waiting on a second, currently
  unfounded ability-adjustment data source.
- *Unavailable data avoided:* yes — no numeric ability-conditioned
  adjustment is invented or licensed prematurely; section H found no
  legally reusable numeric baseline even for the *neutral* benchmark, let
  alone an ability-conditioned one.
- *Known accuracy limitations:* identical resulting states (e.g. same
  bunker, same distance) produce the same expected-strokes value for
  every golfer under Option C, even though a scratch golfer and a
  high-handicap golfer plausibly have different true strokes-to-hole-out
  expectations from that same state — a real, acknowledged limitation,
  not a claim that Option C is fully accurate.
- *Ease of upgrading to B:* high, provided `Delta` is kept as a distinct,
  named, swappable step conceptually from the start (see the V0
  implementation guidance below) rather than fused into `E_base`'s own
  code path.

### Recommendation

**Semantic/long-term architecture: Architecture Option B.**
**V0 implementation: Architecture Option C.**

This is the Architect's reasoned conclusion from the analysis above, not a
forced, pre-decided outcome — a defensible alternative (not adopted here)
would be to skip recording Layer C/`Delta` as a named seam entirely until
Option B is actually justified by data. A human may reach a different
conclusion at the decision gate below; this document records a
recommendation, not an adopted decision.

**Why long-term ≠ V0 is appropriate here:** ability effects on
expected-strokes-relevant performance are real (Broadie 2008's Table 1,
and Arccos'/Shot Scope's shipped handicap-conditioned commercial
products — section H), but reusable, licensable, handicap-conditioned
*state-value* data is currently unavailable (section H/K), while M4
already provides substantial personalisation in outcome *probabilities*
(Layer A, see below) — so Option C's V0 does not mean "no
personalisation," and Option B remains the correct long-term target once
`Delta`'s own evidence/data question is separately resolved.

### M4 already personalises value indirectly

Two golfers evaluated against the **identical** `E_base` function can
still receive **different recommendations** for the same candidate target,
because their `PlayerShotDistribution`s differ:

```
personalised PlayerShotDistribution (Layer A, per-golfer carry/lateral/
bias/scale/correlation/dof)
        v (seeded sampling, per-golfer)
personalised distribution of resulting ShotOutcomes
        v (classification, per candidate shot)
personalised distribution of resulting GolfStates (different fairway/
rough/bunker/green/OB probabilities per golfer)
        v (E_base applied identically to every golfer)
personalised distribution of E_base values -> personalised expected value
/ Strokes Gained for the candidate
```

Two golfers' `PlayerShotDistribution`s differ in carry mean/scale, lateral
bias/scale, correlation, and Student-t tail weight (per ADR 0006), shaped
by ADR 0007's population prior and M4.5's personal partial-pooling update
— this changes the probability mass landing in each lie/hazard category,
which changes the *distribution* of `E_base` values a candidate shot
produces, even though `E_base` itself never asks "who is playing."

**State this explicitly:** A baseline expected-strokes model does NOT
imply a non-personalised CaddAI recommendation. Personalisation under
Option C flows entirely through Layer A (`PlayerShotDistribution`), not
through the state-value function.

`GolfState` itself remains unaffected by this: player/value context is
supplied to the *value function*, never to the state type, under any of
Options A, B, or C (see the amendment note on the `GolfState` ownership
decision gate below).

### Player-state ability is still a real future concern

Option C is **potentially defensible for V0, not necessarily the final
player-value architecture.** Identical resulting states (e.g. the same
greenside bunker at the same distance) may plausibly produce different
true strokes-to-hole-out expectations for a scratch golfer vs. a
high-handicap golfer — a real limitation of Option C, acknowledged and
not hidden, and the reason Option B remains the recorded long-term target
rather than being dismissed.

### Conventional Strokes Gained semantics preserved

`SG_base = E_base(current) - (1 + E_base(resulting))`, using the *same*
single-reference-population function on both sides, is the conventional,
benchmark-comparable Strokes Gained quantity — exactly Broadie 2008's
verified formula `v = f_s - f_e - 1` (one fractional-par function fit once
against one reference population; section H item 2).

A fully personalised `E_player(current) - (1 + E_player(resulting))` is a
**different, not-necessarily-equivalent** quantity: it answers "how many
strokes did this golfer gain relative to their *own* difficulty-adjusted
baseline," not "relative to the conventional scratch/reference
benchmark." These can diverge in sign and magnitude for the same shot
(e.g. a below-average bunker player playing an average bunker shot:
`SG_base` may be strongly negative relative to *scratch*, while a
personalised quantity might be closer to zero because it's roughly what
*that* golfer expected of themselves). Both are legitimate, but **must be
named distinctly and never silently treated as interchangeable.**

Under Option C, `E_player == E_base`, so the two SG quantities are
numerically identical in V0 — this is a coincidence of Option C's
collapse, not a justification for merging the two names/concepts. Keep
distinct naming even when V0's numbers happen to match.

### Proposed terminology (semantic clarity only, not locking exact names)

Candidate names, offered for clarity of discussion — **exact code/type
names are not locked here**, only the discipline of never silently
conflating the concepts they'd represent:

- Layer B's output type: `ExpectedStrokesBaseline` or
  `BenchmarkExpectedStrokes`.
- Layer C's output type: `PlayerAdjustedExpectedStrokes`,
  `PlayerStateValue`, or `PlayerRelativeValue`.
- The Layer-B-derived SG quantity: `BenchmarkStrokesGained` or
  `strokes_gained_base`.
- The Layer-C-derived SG quantity: `PlayerRelativeStrokesValue` or
  `strokes_gained_player_relative`.

### Recommendation-evaluation (M9) vs. strategy dual-use note

A benchmark value function (Layer B) is comparable across players,
comparable across model versions, useful for calibration/evaluation, and
interpretable independently of personal strategy settings — plausibly
useful to a future M9 synthetic-validation/evaluation harness. A
player-adjusted value (Layer C) may be better suited to recommendation
*selection* itself, since it can reflect a specific golfer's individual
weaknesses/strengths. This document only records this potential dual use
for a future milestone's benefit — **no M9 telemetry, evaluation harness,
or metric design is proposed or implemented here.**

### `Delta`'s evidence sources remain open

A future `Delta` should not be narrowly scoped to handicap alone from the
outset. Plausible, non-exhaustive evidence sources for a future `Delta`,
listed to keep the design space open, not to select among them now:
Handicap Index or a broader ability class, learned player history
(per-lie-category performance derived from `ShotRecord` data),
shot-type-specific performance, lie-specific performance, short-game
performance, putting performance, or a population-prior-plus-personal-
learning blend mirroring M4's own architecture (ADR 0006/0007,
`docs/player-model.md`'s population-prior → onboarding → personal
partial-pooling pipeline). **None of these is designed or implemented
here** — this is a list of open evidence sources for a future `Delta`
decision, not a selection among them.

### Rejected note

"Higher handicap = more/less risk" as a universal rule is **rejected** —
it conflates Layer C (a fact about state difficulty for a given golfer)
with Layer D (strategic risk/objective policy, out of scope, belonging to
later M8 strategy work). A handicap-conditioned `Delta` may legitimately
say "this golfer's bunker outcomes are worse than baseline, raising
`E_player` for a bunker-heavy candidate" (Layer C) — it must never
additionally encode "and therefore this golfer should always take the
safer/riskier line" as baked-in universal policy (Layer D).

## I. Expected-strokes V0 options

Evaluated per the brief's required dimensions. **No option here defaults
to ML** — this is a deliberate evaluation choice matching M4.0's own
"should V1 use ML? No." precedent, since the same reasoning applies here:
data availability and licensing clarity are the binding constraint, not
modelling sophistication.

### 1. Lookup/bucket table (discrete distance bands × lie category)

- **Evidence support.** Best-matched to how expected-strokes baselines are
  verified to be published: Broadie 2008's "fractional par" (section H,
  item 2) is itself a distance-and-lie-conditioned table-like quantity
  (illustrative values given for a 140-yd par-3, a 200-yd hole, a 14-ft
  putt), confirming the table shape is a real, precedented methodology —
  though no full published table's exact granularity was found or
  verified this session, and Broadie 2008's own table is fit once against
  a single scratch baseline, not published as a reusable multi-band
  table.
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
- **Licensing.** Verified this session: every specific numeric source
  identified (Broadie 2008/2011, Golfmetrics, Arccos, Shot Scope) is
  either proprietary or never published as a redistributable dataset (see
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

- **Evidence support.** Broadie 2008's "fractional par" concept (section
  H, item 2, verified) confirms expected strokes vs. distance follows a
  smooth, roughly monotonic, diminishing-returns-shaped relationship in
  at least one peer-reviewed source, but fitting a defensible closed-form
  curve requires either (a) access to enough raw or aggregate data points
  to fit against — none were found or verified this session — or (b)
  reusing already-fitted published coefficients (which raises the same
  licensing question as a raw table, since published fitted-curve
  coefficients are themselves a reproducible, potentially copyrighted
  artifact, and no such coefficients were found published openly this
  session).
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
  (confirmed by this amendment's live research: Broadie 2011's ~8-million-
  shot ShotLink dataset is tour-only and access-restricted; Broadie 2008's
  ~40,000-shot amateur dataset was never published as open data;
  Golfmetrics/Arccos/Shot Scope's larger amateur datasets are proprietary
  — mirroring M4.0's own conclusion for the player model: "no verified
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
  physically reasonable prior even without extra data — and one with
  direct peer-reviewed precedent: Broadie 2008's fractional-par values
  (section H, item 2) are themselves monotonically increasing with
  distance in the paper's own illustrative examples.
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
  spike's assessment. This amendment's live-verified research strengthens
  the CONCEPT specifically: Broadie 2008's Table 1 gives real, verified
  quantitative evidence that putting/sand/tee-shot performance differs
  materially by skill band (section H.1), and Arccos's and Shot Scope's
  marketing pages both explicitly, verifiably describe shipping
  handicap-conditioned Strokes Gained benchmarking as a commercial
  product feature today. **However, none of Arccos's, Shot Scope's, or
  Golfmetrics's underlying per-band numeric data is usable or public** —
  all three are proprietary with no public licensing terms found this
  session (section H, items 3/5/6). Evidence for the concept's viability
  is now verified and strong; evidence for a usable per-band numeric
  table is unchanged at zero.
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

> **Reconciled by the second amendment (2026-09-01) — read alongside
> [section H.2](#h2-value-architecture-separating-benchmark-player-adjustment-and-strategic-risk).**
> This section previously combined a distance/lie-conditioned interpolation
> *and* a handicap/ability-band axis into one "V0" candidate. Following the
> value-architecture separation in section H.2, only the distance/lie part
> belongs to V0's neutral `E_base`/Layer B benchmark (Architecture Option
> C). The handicap/ability-band axis belongs to a future, separately-gated,
> **unscheduled** `Delta`/Layer C player-adjustment (Architecture Option
> B) — it is **not** part of this section's V0 candidate any more. This
> section is retitled in substance accordingly: it now describes
> `E_base`'s candidate model family only.

```
Status: LEADING ENGINEERING CANDIDATE (E_base/Layer B model family/contract shape only) — NOT an approved V0, pending a still-unresolved numeric-baseline/data-source decision. The handicap/ability-band axis previously discussed here is now a separate, unscheduled Delta/Layer C follow-on (Architecture Option B), not part of this candidate.
```

**Candidate model family for `E_base`/Layer B (structural only — no
formula, no table values, no implementation):** a **monotonic,
interpolated lookup table, conditioned on distance and lie category only,
with no player-ability/handicap axis** — i.e. **option 5 (monotonic
interpolation)** from [section I](#i-expected-strokes-v0-options),
deliberately **not** options 3/4 (parametric curve / regression), since
both require either data CaddAI does not have or reused published
coefficients whose licensing this amendment's live research found to be
unresolved for every candidate source (section H/K). Option 6
(handicap-conditioned tables) from section I is **not** part of this
V0 candidate — it is the natural candidate shape for a future `Delta`
(Architecture Option B), if and when that separately-gated, currently
unscheduled follow-on is pursued (see the `DECISION REQUIRED:
Expected-Strokes / State-Value Architecture` and the two `FOLLOW-ON
REQUIRED` blocks at the end of this document).

**This is not presented as "recommended" in isolation, and must always be
paired with the status qualifier above.** Why: this amendment's
live-verified research (section H's OVERALL CONCLUSION) found the
underlying **semantic/conditioning structure** — distance + lie +
ability-conditioned expected strokes — strongly supported by multiple
independent, verified sources (section A conclusion). It found **no**
legally reusable public numeric baseline for the actual table/coefficient
values (section B conclusion), for `E_base` or for a future `Delta`. The
`E_base` model family/contract shape is therefore a defensible
**engineering direction to design around now**, but it is **not adopted,
approved, or provisionally accepted as V0** anywhere in this document —
it remains gated on the still-unresolved numeric-baseline/data-source
follow-on (see the `FOLLOW-ON REQUIRED` block at the end of this
document).

No specific numeric table, formula, or coefficient is proposed anywhere in
this document.

## K. Data/licensing table

Every entry below reflects this amendment's live-verified research
(section H) — every classification label below (**reusable**, **likely
reusable with attribution**, **proprietary**, **licensing unclear**,
**methodology only**, **evidence only, not a data source**) is a direct
consequence of a source verified this session, not a placeholder.

| Source/Owner | Contents | Population | Tour vs Amateur | Handicap range known? | Publicly documented? | Raw data/values accessible? | Embeddable/redistributable? | Licensing status | Confidence in reuse conclusion | Relevance to CaddAI |
|---|---|---|---|---|---|---|---|---|---|---|
| Broadie 2011, *Assessing Golfer Performance on the PGA TOUR* (peer-reviewed, PGA TOUR ShotLink, ~8M shots) | Strokes Gained methodology + tour-average baseline | PGA TOUR pros (299 golfers, 2003–2010) | Tour only | No (single tour-average baseline) | Yes (paper is public) | No — underlying ShotLink data is PGA TOUR-restricted, not published | No | **Proprietary** (data) / **methodology only** (paper itself) | High — verified full text this session | Confirms methodology precedent; wrong population for CaddAI's amateur users |
| Broadie 2008, *Assessing Golfer Performance Using Golfmetrics* (peer-reviewed conference proceedings, ~40,000 shots, ~130 golfers, 2005–2007) | "Fractional par" expected-strokes concept + Table 1 skill-band performance data | Pro + amateur (5 skill bands, scratch-benchmarked) | Both, mixed | Partially (5 discrete skill/score bands, not a full handicap continuum) | Yes (paper is public) | Illustrative example values only; no full reusable table published | No | **Evidence only, not a data source** (paper) / dataset never published | High — verified full text this session | Best available amateur-relevant methodology and concept evidence; not a usable numeric source |
| Golfmetrics (commercial app, ~100,000+ amateur shots) | Amateur SG benchmarking across skill levels | Amateur (broad, composition unverified) | Amateur-focused | Unverified | Marketing claims only | No — account-gated commercial app | No | **Proprietary** | High (proprietary status verified) / composition unverified | Confirms concept at scale; not usable as a data source |
| DataGolf, amateur Strokes Gained | SG methodology applied to elite amateur competitions (WAGR/college) | Elite competitive amateur, not recreational | Amateur (elite, non-representative) | No | Yes (blog post public) | No underlying dataset published | No | **Methodology only** | High — verified page this session | Population mismatch for CaddAI's target users |
| Arccos Golf, Strokes Gained Analytics | Handicap/goal-handicap-conditioned SG benchmarking (commercial, GPS-sensor data) | Amateur, handicap-banded | Amateur | Yes (marketed, not published) | Marketing page only | No | No | **Proprietary** | High — verified page this session | Confirms handicap-conditioned SG is a shipping commercial concept; no usable data |
| Shot Scope, Strokes Gained feature | Handicap-benchmark-conditioned SG from GPS-sensor shot data | Amateur, handicap-banded | Amateur | Yes (marketed, not published) | Marketing page + paid ebook | No (ebook is paid, not a raw dataset) | No | **Proprietary** | High — verified page this session | Same conclusion as Arccos; aggregate insights are sold, not given away |
| University of Padova thesis (Briglia, advisor Lisi, 2023–2024 data) | Alternative SG benchmark methodology (per cached abstract snippet only) | Unknown (full text inaccessible) | Unknown | Unknown | Repository listing found; full text blocked (Cloudflare) | No — full text not retrievable this session | Unknown | **Licensing unclear** + **not verified this session** | Low — title/author/abstract snippet only | Potential future lead; requires non-automated follow-up |
| Wikipedia, "Handicap (golf)" / World Handicap System summary | WHS Course/Slope Rating, Stroke Index, Course Handicap mechanics | General golfer population (round/handicap policy, not shot-level) | N/A (round-level, not shot-level) | N/A | Yes (public, well-cited) | Yes, but it is not an expected-strokes-to-holeout numeric source at all | N/A | **Methodology only** | High — verified full section text this session | Confirms M5/M8 separation (WHS is scoring policy, not a shot-level value model); no expected-strokes numbers |
| CaddAI's own future round/decision-journal data (M8+) | Not a currently existing source — a future first-party dataset | CaddAI's actual users | Amateur (CaddAI's target population) | Yes, if collected | N/A (does not exist yet) | Fully owned once collected | Fully embeddable once collected and aggregated | **Reusable** (first-party) | N/A — future only | The only source requiring no licensing verification, but unavailable for V0 |

**Every non-"reusable" status above must be resolved (or the source
abandoned) by the human before any V0 implementation embeds derived
numeric content from it.** This amendment narrows the evidence and
licensing picture; it does not resolve licensing for any external source.

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
  (`baseline_expected_strokes(golf_state) -> float`, illustratively —
  see the naming below) should be
  designed so its initial implementation (a lookup/interpolated table) can
  later be replaced by a refitted table, a regression fit against CaddAI's
  own data, or a richer representation — **without changing the function
  signature or the `GolfState` contract that `strategy`/the decision
  journal/the M9 harness consume.** This mirrors ADR 0007's core
  guarantee almost exactly, applied to a new value-model contract instead
  of a population-prior contract.
- **Value-architecture contract direction (Architect items 2/4/7,
  2026-09-01 second amendment) — SUPERSEDES the previous
  `expected_strokes(state, ability_context?) -> value` signature
  proposal.** A prior version of this subsection proposed a single
  function taking an optional `ability_context` parameter. Following the
  Architect review recorded in full in
  [section H.2](#h2-value-architecture-separating-benchmark-player-adjustment-and-strategic-risk),
  that single-function shape is rejected in favour of two named,
  separately composed interfaces:
  - **Semantic/long-term contract:** a `baseline_expected_strokes(state)
    -> value`-shaped Layer B interface (`E_base`), and a future
    `player_adjusted_state_value(state, baseline_value, player_context)
    -> value`-shaped Layer C interface (`Delta`/`E_player`), composed by
    one composition layer — not a single function with an optional
    parameter that silently switches behaviour, and not two
    independently-owned services. See section H.2 for the full
    Architecture Option A/B/C comparison and the recommendation
    (semantic: Option B; V0: Option C).
  - **V0 implementation ships only the one-parameter function.** V0
    should expose **only** `baseline_expected_strokes(state) -> value` —
    no `ability_context` parameter, inert/always-`None` or otherwise.
    Recording the eventual two-function composition shape now (above) is
    acceptable — an accepted-but-inert parameter wired into V0 code today
    would be a premature-abstraction pattern, inviting a future caller to
    pass something meaningful before `Delta` has any real content behind
    it.
  - **Where ability/handicap lives, if/when `Delta` is implemented — a
    separate parameter to `Delta`, never inside `GolfState`.**
    `GolfState` is physical/course-relative fact independent of who is
    playing; ability/handicap is golfer context passed to `Delta`. This
    mirrors the existing separation between `PlayerShotDistribution`
    (`caddai.statistics`, golfer-specific) and course-relative facts
    (`course`/`simulation`) — the same seam, one layer up. `GolfState`'s
    own invariants (section D) are unaffected by this contract choice.
  - **Dependency-direction concern — none beyond what's already
    documented.** `docs/architecture.md` already states `strategy`/
    `simulation` depend on `course`, `player`, `statistics`, and shared
    domain types. `E_base` needs no `caddai.player`/`caddai.statistics`
    dependency at all; a future `Delta` reading player-ability data would
    depend on those modules — both already-approved, already-diagrammed
    edges, not new ones.
  - **Contract semantics vs. numeric implementation — confirmed
    compatible with ADR 0007's precedent.** Recording a stable
    `baseline_expected_strokes(state)` contract (returning a value +
    explicit unsupported-state signal + model/version provenance, see
    below) without committing to numeric tables/coefficients is
    architecturally sound now — this is ADR 0007's "stable interface,
    replaceable implementation" pattern reapplied. Recording this
    direction in this research document is **not itself the ADR** — a
    separate future ADR is still required for the expected-strokes
    interface at its own implementation time (see
    [section P](#p-adr-requirements)), and a further, separately-gated
    future ADR is anticipated for `Delta`/Layer C if/when it is
    implemented.
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
  data" — never silently presented as validated fact. This amendment's
  live-verified research (section H) narrows *why* this matters: the
  concept is well-evidenced, but no numeric content sourced from Broadie
  2008/2011, Golfmetrics, Arccos, or Shot Scope may be embedded at all
  until licensing is separately resolved (section K) — "provisional" here
  means "CaddAI-authored placeholder," not "an unverified transcription of
  someone else's proprietary table."
- **Applies equally to a future `Delta`/Layer C.** The four provenance/
  no-network/determinism/explicit-provisionality properties above are
  described here in terms of `E_base`/Layer B specifically, since that is
  the piece V0 actually ships (section H.2). They apply equally, without
  modification, to `Delta`/Layer C once/if it is implemented — a future
  `Delta` must carry its own model/version provenance, must remain
  offline/deterministic, and must mark its own numeric content as
  provisional until separately validated, exactly as `E_base` must.

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
  This describes the general shape shared by `SG_base` (using `E_base`
  throughout) and a possible future player-relative quantity (using
  `E_player` throughout, per
  [section H.2](#h2-value-architecture-separating-benchmark-player-adjustment-and-strategic-risk))
  — never a mix of the two on either side of one computation:
  `strokes_gained = expected_strokes(current_state) - (1 +
  expected_strokes(resulting_state))`, where `expected_strokes` is
  consistently `E_base` for `SG_base`, or consistently a future `E_player`
  for a player-relative quantity. This is representable in a fully
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
- **A future `Delta`/Layer C composition remains vectorisable, not just
  `E_base` alone.** Per the [section H.2](#h2-value-architecture-separating-benchmark-player-adjustment-and-strategic-risk)
  value-architecture discussion: when/if `Delta` is eventually
  implemented, it is conditioned on a *single* golfer's `player_context`
  for an entire batch of N simulated outcomes — ability context does not
  vary per Monte Carlo sample within one candidate-shot evaluation — so
  it can be applied as one broadcast adjustment per lie-category cell
  across all N samples. `E_base(states) + Delta(states, player_context)`
  therefore remains a vectorised, O(N) composition, not O(N) stateful
  calls. Batch/vectorisation is preserved under Architecture Option B,
  not only under Option C — this is not a reason to prefer one option
  over the other.

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

## Q.1 Rejected and deferred options — this amendment

### REJECTED NOW

- Blindly using PGA TOUR/ShotLink values as amateur benchmarks (verified:
  ShotLink is tour-only and access-restricted; Broadie 2011 itself only
  covers PGA TOUR players — section H, item 1).
- Copying or reconstructing proprietary Arccos/Shot Scope/Golfmetrics
  numeric values (verified: all three are proprietary commercial products
  with no public licensing terms found — section H, items 3/5/6).
- Building an ML/regression model without a dataset to fit against (no
  dataset was found this session — section I, option 4).
- Pretending licensing is solved for any of the above (explicitly not
  solved — section K).
- Putting `GolfState` inside `strategy` merely for convenience (Architect
  item 1/7 — see [section E](#e-golfstate-ownership-options)'s rejected
  options).

### DEFERRED

- CaddAI-personalised expected-strokes learning.
- Richer handicap-conditioned models beyond a coarse band structure.
- Sophisticated rollout physics.
- Putting-shot simulation (`PUTTER` in the M4 shot-distribution model).
- M8 WHS strategic policy.
- M9 formal Rules behaviour.
- Full verification of the Padova thesis, official USGA/R&A WHS primary
  documentation, and PGA TOUR's explicit ShotLink licensing terms (a
  narrower future research follow-on, not blocking this decision gate —
  see the `FOLLOW-ON REQUIRED` block at the end of this document).

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

## R. M5.0 resolution status (2026-09-02 decision-recording amendment)

This section records what the 2026-09-02 amendment resolved and what it
deliberately left open. It does not redo, weaken, or re-derive anything
above — it only summarises the resolution status on top of the existing
evidence and reasoning.

### Resolved by M5.0

- The `GolfState` semantic architecture direction (course owns geometry;
  neutral `GolfState` owns player-neutral course-relative state
  semantics; `simulation` owns the `ShotOutcome` + shot frame + course
  geometry -> `GolfState` mapping; expected-strokes/value consumes
  `GolfState`; `strategy` consumes distributions of resulting values) —
  **approved**.
- The course-relative mapping responsibility direction (`simulation` may
  own the `ShotOutcome + origin + target/target frame + course geometry
  -> GolfState` operation) — **approved, semantic responsibility only**.
- The benchmark vs. player-adjusted value architecture separation (Layers
  A–D; Architecture Options A/B/C compared in
  [section H.2](#h2-value-architecture-separating-benchmark-player-adjustment-and-strategic-risk))
  — the separation itself, and the comparison, are preserved as the
  basis for the decision below.
- The V0 baseline-only architecture: Architecture Option C **approved for
  V0**; Architecture Option B **approved for the long-term target**;
  Architecture Option A **not selected** as the long-term core value
  architecture.
- The benchmark Strokes Gained semantic boundary: `SG_base =
  E_base(current_state) - (1 + E_base(resulting_state))` is defined and
  preserved as the canonical benchmark-comparable quantity for the M5
  baseline path.

### NOT resolved by M5.0

- The exact `GolfState` API/type design (fields, types, module contract
  details beyond the semantic architecture).
- The `GolfState`/course-relative-state ADR itself — not written by this
  or any prior amendment.
- The numeric expected-strokes baseline/data source (`FOLLOW-ON
  REQUIRED: Expected-Strokes Numeric Baseline / Data Source`, below) —
  still open.
- The exact `E_base` implementation.
- The player-adjustment (`Delta`) model.
- Strokes Gained implementation (code).
- Strategy implementation.

## S. Next work after PR #79 (sequencing guidance only — no issues created)

This section is **sequencing guidance only**. No GitHub issues are
created by this document; detailed M5 planning remains a separate future
task.

- **Stream A — `GolfState` / course-relative domain:** `GolfState` ADR ->
  `GolfState` contract implementation -> course-relative mapping
  implementation.
- **Stream B — Expected-strokes numeric baseline:** bounded numeric-
  baseline/data-source research -> human decision -> expected-strokes
  interface/implementation ADR if required -> `E_base` implementation.
- **Convergence:** `GolfState` + `E_base` -> benchmark SG distributions ->
  baseline expected-value strategy -> recommendation assembly.

The unresolved expected-strokes numeric baseline blocks the value-model
implementation path (Stream B and the convergence step), but it does not
block `GolfState` ADR/domain work (Stream A). These are independent
workstreams that may proceed in parallel. This is an important
consequence of the approved separation above.

Streams A and B correspond to, and refine, the existing
["Likely future M5 implementation decomposition"](#likely-future-m5-implementation-decomposition-proposal-only-not-created-as-issues)
list elsewhere in this document (items 1–2 = Stream A; item 3 = Stream B;
items 4–5 = convergence; item 6 = the later, unscheduled `Delta`
follow-on) — see that list for detail, not duplicated here.

---

```
DECISION REQUIRED: GolfState ownership and course-relative mapping
```

```
HUMAN DECISION: APPROVED (2026-09-02)
```

> The semantic architecture direction is approved:
> ```
> course              owns course geometry/data
> neutral GolfState   owns player-neutral course-relative state semantics
> simulation          owns the mapping operation: ShotOutcome + shot frame + course geometry -> GolfState
> expected-strokes/value   consumes GolfState
> strategy            consumes distributions of resulting values
> ```
> `GolfState` must remain independent of: player identity, Handicap Index,
> risk preference, WHS scoring policy, current round score, and strategic
> goal. This approves the **semantic architecture direction only** — not
> exact Python APIs or implementation details. A dedicated `GolfState`/
> course-relative-state ADR is still required before the foundational
> contract is implemented (**not created by this amendment**); that future
> ADR must resolve/record at least: canonical module/package ownership,
> exact domain contract, dependency direction, classification ownership,
> public API implications, interaction with `course`, interaction with
> `simulation`, interaction with expected-strokes/value, and portability
> implications for M6.
>
> The course-relative mapping ownership is also approved, as **semantic
> responsibility only**: `simulation` may own the operation `ShotOutcome +
> shot origin + actual selected target/target frame + course geometry ->
> GolfState`. This does not approve exact APIs. It preserves the
> requirement that the actual selected target frame is used — CaddAI must
> never automatically substitute the pin, the green centre, or its own
> recommendation when the golfer selected a different target.

> **Amendment note (2026-09-01):** this decision block is otherwise
> unchanged in substance. This amendment's Architect confirmation (see
> sections E/F) **reconfirms — does not reopen** — the recommendation
> below. A second amendment, the same day, separately reconfirmed (per
> [section H.2](#h2-value-architecture-separating-benchmark-player-adjustment-and-strategic-risk)
> item 6) that `GolfState` remains player-neutral under **every**
> expected-strokes value-architecture option (A, B, or C, see the
> `DECISION REQUIRED: Expected-Strokes / State-Value Architecture` block
> below) — none of them requires adding player/ability/handicap/risk
> fields to `GolfState` itself; player/value context is supplied to the
> *value function*, never to the state type. This is a confirmation, not
> a reopening, of the recommendation below.

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
DECISION REQUIRED: Expected-Strokes / State-Value Architecture
```

```
HUMAN DECISION: APPROVED (2026-09-02)
```

> **Long-term = Architecture Option B; V0 = Architecture Option C;
> Architecture Option A is not selected** as the long-term core value
> architecture (not selected, not "impossible forever"). Reasons
> recorded: Option A conflates benchmark expected strokes with
> player-relative state difficulty; makes conventional benchmark Strokes
> Gained semantics less clear; embeds unresolved ability-conditioned data
> requirements in the core baseline; encourages handicap to become the
> permanent personalisation mechanism; and reduces separation among
> benchmark, player ability, and strategic objective.
>
> This decision **approves the value architecture only** — the numeric
> expected-strokes baseline remains unresolved; see the (unchanged)
> `FOLLOW-ON REQUIRED: Expected-Strokes Numeric Baseline / Data Source`
> block below.
>
> The M4-personalisation-role principle is reaffirmed, verbatim: "A
> baseline expected-strokes model does NOT make CaddAI recommendations
> non-personalised." Under V0, the pipeline is:
> `PlayerShotDistribution -> personalised distribution of resulting
> GolfStates -> E_base applied to each state -> personalised distribution
> of outcome values`.
>
> Benchmark Strokes Gained semantics are reaffirmed, verbatim: `SG_base =
> E_base(current_state) - (1 + E_base(resulting_state))` is the canonical
> benchmark-comparable quantity for the M5 baseline path. A future
> `E_player(current) - (1 + E_player(resulting))` is a distinct
> player-relative value metric requiring separate terminology — never
> silently called "Strokes Gained" if benchmark semantics differ.
>
> Player-adjustment ≠ strategic risk is reaffirmed: `Delta` estimates
> player ability from a state; strategic objective/risk remains a later
> strategy/M8 concern. Any universal assumption like "high handicap =
> more risk" or "low handicap = less risk" (or the reverse) is rejected.

> **Amendment note (2026-09-01, second amendment):** this block
> **replaces** the previous `DECISION REQUIRED: Expected-Strokes V0
> Contract Direction` block, which asked whether CaddAI's expected-strokes
> contract should support combined distance + lie/state +
> golfer-ability/handicap conditioning in a single function. That framing
> is superseded — see [section H.2](#h2-value-architecture-separating-benchmark-player-adjustment-and-strategic-risk)
> for why a single combined function risks conflating three distinct
> questions. This block reframes the decision around the separated
> Architecture Option A/B/C comparison instead.

**Question:** Should CaddAI separate benchmark expected strokes (Layer B,
`E_base`) from player-specific state-value adjustment (Layer C, `Delta`)
from strategic risk/objective (Layer D, out of scope, later strategy/M8
work) — i.e. Architecture Option B — rather than a single ability-
conditioned function (Architecture Option A), or should V0 ship only the
neutral baseline with no player-adjustment seam at all (Architecture
Option C)? See [section H.2](#h2-value-architecture-separating-benchmark-player-adjustment-and-strategic-risk)
for the full Architecture Option A/B/C comparison.

**Recommended answer:** this is the **Architect's reasoned recommendation
for human review, not something this document adopts unilaterally**:
- **Semantic/long-term architecture: Architecture Option B** (neutral
  `E_base` + separately named, separately composed `Delta`).
- **V0 implementation: Architecture Option C** (`E_player(state) =
  E_base(state)`; `Delta` is identity/no-op and unimplemented).

**Verified evidence:** two peer-reviewed Broadie papers (2008, 2011) using
real distance+lie+scratch/tour-benchmark data, plus three independently
verified commercial products (Golfmetrics, Arccos, Shot Scope), support
the *concept* that ability materially affects expected-strokes-relevant
performance (section H's VERIFIED EXTERNAL EVIDENCE list, section H.1's
amateur evidence scrutiny) — but no verified source publishes a combined
distance+lie+ability-conditioned expected-strokes numeric surface
(Architecture Option A's specific data need), and Broadie's own
fractional-par methodology (section H, item 2) is itself a
single-reference-population benchmark, i.e. exactly Layer B/Architecture
Option B's `E_base` shape, not Option A's combined shape.

**Alternatives considered:**
- **Architecture Option A** (single ability-conditioned function) —
  rejected as the long-term target: forecloses conventional,
  benchmark-comparable Strokes Gained semantics (section H.2), has no
  supporting evidence for a *combined* numeric surface, and bakes an
  unresolved data/licensing problem into the core value contract instead
  of isolating it behind a swappable `Delta`.
- **Architecture Option C as a permanent architecture** (no player
  adjustment ever) — rejected as a *permanent* end-state: it discards real
  evidence (Broadie 2008's Table 1, Arccos'/Shot Scope's shipped
  handicap-conditioned products) that ability materially affects
  difficulty beyond what Layer A alone captures.
- **Skip recording the Layer C/`Delta` seam entirely until Option B is
  actually justified by data** — a defensible alternative, not adopted:
  the Architect judges recording the seam now costs little and avoids a
  future signature-breaking change (ADR 0007 precedent), but a human
  reviewer may reasonably prefer this simpler alternative instead.

**Consequences:** enables `GolfState`, classification, and rollout design,
plus the V0 `baseline_expected_strokes(state)` contract (section M), to
proceed now; keeps the door open for `Delta`/Layer C to be added later as
an additive, non-breaking change; keeps Strokes Gained semantics
unambiguous (`SG_base` vs. a distinctly-named player-relative quantity,
section H.2).

**Remaining uncertainty:** the numeric baseline for `E_base`/Layer B
itself is **still unresolved regardless of which architecture option is
chosen** — see the `FOLLOW-ON REQUIRED` block below, which this decision
does not resolve. A `Delta`/Layer C numeric/model content question is a
further, separate, even-less-evidenced follow-on, also not resolved here
(see the amended `FOLLOW-ON REQUIRED` block below).

**Licensing implications:** unchanged from the existing analysis — all
specific numeric sources identified this session (Broadie 2008/2011,
Golfmetrics, Arccos, Shot Scope) are proprietary, access-restricted, or
never published as open data (section K); no numeric content from any of
them may be embedded until licensing is separately resolved, which this
decision does not attempt to resolve, for either `E_base` or a future
`Delta`.

**Implementation implications:** the V0 single-parameter
`baseline_expected_strokes(state) -> value` function (section M) can be
designed now, gated on its own future ADR (section P) and on the numeric-
baseline follow-on below. `Delta`/Layer C remains unimplemented, pending
its own future evidence/data question — not designed, scheduled, or
gated on an ADR here.

**What later decision is still required:** the numeric-baseline/data-source
follow-on immediately below, for `E_base`/Layer B; and, separately and
later, `Delta`/Layer C's own evidence/data/implementation question if
Architecture Option B is pursued.

```
FOLLOW-ON REQUIRED: Expected-Strokes Numeric Baseline / Data Source
```

> **Amendment note (2026-09-01, second amendment):** this follow-on is
> specifically about Layer B's (`E_base`'s) numeric baseline — see
> [section H.2](#h2-value-architecture-separating-benchmark-player-adjustment-and-strategic-risk).
> A **second, even-less-evidenced future follow-on** would separately
> cover Layer C's (`Delta`'s) numeric/model content, if/when Architecture
> Option B is pursued — that second follow-on is not designed or
> scheduled by this document at all; it is noted here only so it is not
> forgotten once `E_base`'s own follow-on is eventually resolved.

This follow-on must determine one of:


- a legally reusable public baseline (**none currently identified** —
  section H/K);
- a derived/open baseline CaddAI builds itself;
- an explicitly provisional CaddAI-authored approximation (clearly
  labelled as such, not presented as validated);
- licensed data (e.g. approaching Golfmetrics/Arccos/Shot Scope
  commercially — unverified feasibility/cost);
- or another defensible approach not listed above.

**This is NOT resolved by this amendment and is not automatically started
now.** It remains a separate, explicitly gated future decision — see
[section Q.1](#q1-rejected-and-deferred-options--this-amendment)'s
DEFERRED list for the narrower research items (Padova thesis full text,
USGA/R&A primary WHS documentation, PGA TOUR's explicit ShotLink licensing
terms) that a future pass toward this follow-on might start from.

> **Amendment note (2026-09-02):** the value-architecture `DECISION
> REQUIRED` block above is now `HUMAN DECISION: APPROVED`. This follow-on
> remains the **only** unresolved item blocking `E_base(GolfState)`
> implementation. It does **not** block the `GolfState` ADR/domain work
> (see [section S](#s-next-work-after-pr-79-sequencing-guidance-only--no-issues-created),
> Stream A) — Stream A (`GolfState`) and Stream B (this numeric-baseline
> follow-on) are independent workstreams.

---

## Likely future M5 implementation decomposition (proposal only, not created as issues)

**None of the following are created as GitHub issues by this task.** This
is a candidate ordering only, for the human/Orchestrator to review.

> **Amendment note (2026-09-01, second amendment):** reordered/relabelled
> below to reflect the [section H.2](#h2-value-architecture-separating-benchmark-player-adjustment-and-strategic-risk)
> Layer A–D breakdown. Item 3 is now explicitly scoped to Layer B
> (`E_base`) only. Player-adjustment (Layer C, `Delta`) is listed
> separately at the end as a **later, not-yet-scheduled** item, consistent
> with Architecture Option C being the V0 recommendation.

1. **`GolfState` domain/state contract** — new neutral module, minimal
   fields per section D, gated on an ADR per section P.
2. **Course-relative mapping** — classification + rollout in
   `caddai.simulation`, including the `ROUGH`/generic-penalty-area
   `FeatureType` additions and new point-in-polygon geometric primitives
   identified in section B.
3. **Baseline expected strokes (Layer B, `E_base`)** — the single-
   parameter `baseline_expected_strokes(state) -> value` contract (section
   M), gated on independent human verification of section H/K's sources
   and the `DECISION REQUIRED: Expected-Strokes / State-Value
   Architecture` gate, and separately gated on the `FOLLOW-ON REQUIRED:
   Expected-Strokes Numeric Baseline / Data Source` block's own numeric-
   baseline resolution; not to be opened until both pass.
4. **Strokes Gained (benchmark) distribution-aware candidate evaluation**
   — consumes 1–3 above; produces the full outcome distribution (never a
   single scalar), per the roadmap's explicit requirement; computes
   `SG_base` (section H.2), not a player-relative SG quantity.
5. **Baseline expected-value strategy & recommendation assembly** —
   consumes 1–4; the first structured, trustworthy `strategy`
   recommendation maximising expected Strokes Gained (benchmark) as its
   baseline objective.

**Later, not-yet-scheduled, distinct from the above:**

6. **Player-adjustment (Layer C, `Delta`)** — `player_adjusted_state_value
   (state, baseline_value, player_context) -> value` (section M's future
   contract), gated on its own separate future evidence/data follow-on
   (see the amended `FOLLOW-ON REQUIRED` block above) and its own future
   ADR (section P); not designed, scheduled, or opened by this document.
   Only pursued if Architecture Option B (section H.2) is adopted at the
   decision gate.

Ordering follows strict data dependency (each item consumes the previous).
Item 3's gate is the most consequential sequencing constraint for items
1–5: items 4–5 cannot meaningfully begin before it, and item 3 itself
cannot begin before its own human-verification/decision-gate step
completes. Item 6 is independent of this sequencing — it is a later,
separately-gated addition, not a blocker for items 1–5.
