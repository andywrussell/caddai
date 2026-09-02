# 0008. GolfState domain contract and ownership

## Status

Proposed. This is the **second revision** of this same ADR (same ADR
number, still PR #96) — it shrinks the `GolfState` field contract further,
in response to Adversarial Review scrutiny of the first draft, before any
human sign-off has been given. It is not a new ADR, and it does not hide
the first draft's content: the first draft's now-superseded choices
(`selected_target`, `is_penalty`, the `holed`/exact-coordinate-equality
invariant, `course_reference`/`hole_number`) are preserved, explained, and
formally rejected in [Alternatives considered](#alternatives-considered)
below, per this project's convention of recording ADR history rather than
hiding it.

The semantic direction this ADR elaborates — `course` owns geometry, a new
neutral module owns player-neutral course-relative state, `simulation`
owns the `ShotOutcome` + shot origin + actual selected target + course
geometry -> `GolfState` mapping, expected-strokes/value consumes
`GolfState`, `strategy` consumes distributions of resulting values — was
already explicitly human-approved during the M5.0 research spike (issue
#11: "APPROVED — semantic architecture direction only... A dedicated ADR
(M5.1) is still required before implementation"). This ADR turns that
already-approved direction into a precise, binding contract (exact fields,
types, validators, ownership, and dependency edges); it does not introduce a
materially different, unapproved direction — see
[Relationship to M5.0 research](#relationship-to-m50-research) for how this
revision specifically relates to that approval.

However, the M5.0 approval was explicitly scoped to "semantic architecture
direction only... exact Python APIs/implementation details are not approved
by this." The following specific decisions in this ADR go beyond that prior
approval and require the human's explicit sign-off at PR review before this
ADR can move to **Accepted**:

1. The `AGENTS.md` §4 module-maintainer assignment of
   `src/caddai/golf_state/` to the **Strategy Engineer** — `AGENTS.md` §14
   lists changing module ownership as a condition requiring a human
   decision.
2. The exact `LieCategory` enum membership and collapsing choices (no
   distinct `RECOVERY` category; `WATER` and generic `PENALTY_AREA`
   collapsed into a single `PENALTY_AREA` member; the enum's broadened
   "resulting-state/location category" scope, deliberately mixing playable
   and non-playable/unmapped categories — see the Rules/penalty boundary
   section below).
3. The exact `GolfState` field set and its validated invariants: four
   stored fields (`position`, `hole_reference_position`, `lie`, `holed`)
   plus the computed `distance_to_hole_metres`; the relaxed `holed`
   invariant (no exact-coordinate-equality requirement against
   `hole_reference_position`, but now requiring `holed=True ⇒ lie not in
   {OUT_OF_BOUNDS, PENALTY_AREA, UNKNOWN}` — see the `holed` field
   rationale below); and Option B — course/hole identity is supplied by
   surrounding context, not stored on `GolfState`.

A human reviewing the PR for this ADR should either approve these specific
items — at which point a follow-up commit or PR note may update this ADR's
status to **Accepted** — or request changes. This ADR does not silently
self-promote to `Accepted`; per the standard Orchestrator -> Architect
review -> Adversarial review -> Integrator pipeline, that promotion is a
human decision made at PR review, consistent with how ADRs 0001–0007 were
each accepted only once the human had approved that specific direction in
conversation.

## Context

[docs/research/m5-golf-state-expected-strokes.md](../research/m5-golf-state-expected-strokes.md)
(the M5.0 spike) established that milestone M5 needs a player-neutral,
course-relative representation of "where the ball ended up and what that
means" — `GolfState` — sitting between `simulation`'s M4 forward
shot-production pipeline (which produces a target-line-relative
`ShotOutcome`, not a course-relative result) and a future expected-strokes/
value layer. The spike's semantic architecture direction (module identity
`caddai.golf_state`, `simulation` as the mapping owner, expected-strokes as
a pure function of `GolfState`) is approved; the exact type contract is not,
which is why this ADR (M5.1, issue #81) exists as the first Stream A item in
[docs/plans/m5-detailed-implementation-plan.md](../plans/m5-detailed-implementation-plan.md).

Three existing types bound this decision:

- `caddai.course.models` (`FeatureType`, `Feature`, `Hole`, `Course`):
  `FeatureType` currently has `TEE, FAIRWAY, GREEN, BUNKER, WATER,
  OUT_OF_BOUNDS, LANDING_AREA` — no `ROUGH`/`PENALTY_AREA` yet (issue #83's
  job, independent of this ADR). `Hole` has `number: int` (`gt=0`),
  `par: int`, `features: list[Feature]` — no stable id/version field, no
  `pin_position`. `Course` has `name: str` (`min_length=1`), `holes`. No
  point-in-polygon primitive exists yet (also #83's job).
- `caddai.simulation.models.ShotOutcome`: frozen Pydantic,
  `downrange_metres`/`lateral_metres` only — target-line-relative, not
  course-relative.
- `caddai.gps.models.Coordinate`: `latitude`/`longitude` in decimal degrees,
  WGS84, an existing leaf domain type with zero other `caddai.*` imports.

`AGENTS.md` §2.1 (deterministic strategy: `strategy`/`simulation` decide,
`llm` may only explain) and §2.2 (offline-first active round: shot
simulation and strategy/recommendation must remain locally executable, no
network request on the critical path) both bound any new type these
subsystems produce or consume. §3/§4/§5/§9/§13 (subsystem table, module
ownership, SI units, approved dependencies, ADR triggers) apply directly:
this decision is a new module, a new dependency edge, and a new
multi-subsystem public type contract, which is exactly what §13 requires an
ADR for.

## Decision

### Module ownership

Introduce a new top-level module `caddai.golf_state`
(`src/caddai/golf_state/__init__.py` + `src/caddai/golf_state/models.py`),
following the existing per-subsystem file-layout convention. `AGENTS.md` §4
is updated so `src/caddai/golf_state/` is maintained by the **Strategy
Engineer** — the agent already owning `simulation` (the mapping owner) and
`strategy` (a consumer), the two subsystems most directly coupled to this
type's lifecycle. Maintenance ownership (who edits the code) is a distinct
question from dependency direction (which subsystems may import it):
`golf_state` remains import-neutral — a leaf domain module any approved
consumer may depend on — regardless of who maintains it.

### Dependency direction

Stated as a directed edge list:

- `caddai.golf_state` depends on: `caddai.gps` only (it reuses
  `caddai.gps.models.Coordinate` for its position/target fields), plus
  stdlib and Pydantic. Zero dependency on `course`, `player`, `statistics`,
  `simulation`, `strategy`, `api`, `cli`, `llm`.
- `caddai.course` must **not** depend on `caddai.golf_state`. `course`
  stays geometry/provider-only — no golfer strategy, no player-specific
  state, no recommendation policy — and a dependency on `golf_state` would
  invert the approved direction.
- `caddai.simulation` depends on `caddai.golf_state` (it constructs
  instances as the mapping owner), `caddai.course` (geometry), and
  `caddai.gps` (projection). These are the edges M5.4/M5.5 will add to
  `tests/test_architecture_boundaries.py`'s `simulation` allow-list; this
  ADR confirms they are the correct, minimal set.
- A future expected-strokes/value module (M5.8) should depend on
  `caddai.golf_state` only — not on `course`, `player`, `statistics`, or
  `simulation` — to preserve its own neutrality (`E_base(state)` must stay
  a pure function of `GolfState`). This is a constraint this ADR recommends
  M5.8 honour, not something this ADR can bind a future, not-yet-designed
  module to.
- `caddai.strategy` depends on `caddai.golf_state` (already anticipated by
  M5.11's planned allow-list addition) and on the future value module's
  output (a distribution over evaluated `GolfState`s) — never the reverse.
- A future M8 round/decision-journal module depends on `caddai.golf_state`,
  read-only, never the reverse.
- No circular dependencies: `golf_state` has exactly one outgoing edge
  (`caddai.gps`); every other named edge points *into* it.

### GolfState semantic contract (V0)

A frozen (`ConfigDict(frozen=True, extra="forbid")`) Pydantic `BaseModel`:

```python
class LieCategory(StrEnum):
    TEE = "tee"
    FAIRWAY = "fairway"
    ROUGH = "rough"
    BUNKER = "bunker"
    GREEN = "green"
    PENALTY_AREA = "penalty_area"
    OUT_OF_BOUNDS = "out_of_bounds"
    UNKNOWN = "unknown"


class GolfState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    position: Coordinate
    hole_reference_position: Coordinate
    lie: LieCategory
    holed: bool

    @computed_field  # type: ignore[prop-decorator]
    @property
    def distance_to_hole_metres(self) -> float:
        return haversine_distance_metres(self.position, self.hole_reference_position)
```

`# type: ignore[prop-decorator]` matches the existing `computed_field`
precedent in `caddai.player.models` (mypy strict does not yet understand
`@computed_field` stacked on `@property`).

This is a smaller contract than this ADR's first draft: `is_penalty`,
`selected_target`, `course_reference`, and `hole_number` are removed
entirely (not deferred — see each field's "Removed from this draft"
rationale below and the corresponding new entries in
[Alternatives considered](#alternatives-considered)), and `hole_position`
is renamed to `hole_reference_position`. Four stored fields, one enum, one
computed property.

One implementation note for whichever issue implements/consumes this:

- `extra="forbid"` combined with a `@computed_field` means
  `GolfState.model_validate(instance.model_dump())` will **not** round-trip
  — `model_dump()` serializes `distance_to_hole_metres` out, but
  `model_validate()` rejects it back in as an unexpected keyword under
  `extra="forbid"`. Any future persistence/replay path (e.g. a decision
  journal, M8) must reconstruct `GolfState` from its *stored* fields only
  (`position`, `hole_reference_position`, `lie`, `holed`), never from a
  full `model_dump()` round-trip. Not an issue for M5 itself (no
  persistence exists yet).

Field-by-field rationale (stored vs. derived vs. excluded), following
[docs/research/m5-golf-state-expected-strokes.md](../research/m5-golf-state-expected-strokes.md)
section D's requirements table:

- **`position`** — the resulting ball position, as a `Coordinate` (lat/lon,
  WGS84), not a local-metre point relative to an unstated origin. A
  local-metre `LocalPoint` is only meaningful alongside the anchor
  `Coordinate` it was projected from (ADR 0002/0004 precedent); storing that
  anchor too would double the position data for no benefit, whereas a plain
  `Coordinate` is self-contained, portable (M6), and consistent with
  `course.Feature.position`'s existing convention. Any consumer needing a
  local-metre frame re-projects on demand via `gps.projection`, exactly as
  `course/distance.py` already does per-call (ADR 0004's frame-consistency
  invariant) — `GolfState` does not cache a stale local frame.
- **`hole_reference_position`** (renamed from `hole_position`) — stored as
  data, not `distance_to_hole_metres` as a precomputed float, structurally
  eliminating the drift risk between a stored distance and `position`:
  `distance_to_hole_metres` is derived on demand (see below), so it is
  definitionally always consistent with whichever `position`/
  `hole_reference_position` pair is currently stored — there is no second
  value that can go stale. Renamed from `hole_position` because that name
  risked implying an exact, known, verified physical cup position, which
  CaddAI does not have — M2 currently exposes only green geometry/centroid
  semantics, no authoritative daily pin model (`docs/course-engine.md`'s
  documented gap). `hole_reference_position` makes clear this is *a*
  reference point used to compute a benchmark distance — which may come
  from a known pin/cup location, a green-centre approximation (today's
  actual source), or another explicit caller-provided hole reference —
  without claiming precision it doesn't have. No provenance/confidence
  field is added to encode which kind of reference it is: that is
  caller/context metadata, not foundational state, so it is documented
  here in prose only. It is computed once by the mapper (`simulation`,
  M5.5) from `course` geometry, exactly as the previous draft's stored
  distance was, just one derivation step earlier. This is `GolfState`'s
  only other nested `Coordinate` submodel alongside `position` (the first
  draft's `selected_target` made it a third; removing that field, see
  below, leaves two) — still O(1)/cheap construction, consistent with the
  existing `ShotOutcome`/M4-sampling Monte Carlo precedent of constructing
  small, flat, multi-field value objects (including nested `Coordinate`
  fields) thousands of times per candidate-evaluation loop without
  measurable overhead. Issue #82's actual `golf_state/models.py`
  implementation should repeat this "not an authoritative pin location,
  may be a green-centroid approximation" warning inline in the field's own
  docstring, not only in this ADR — a future engineer reading the type
  definition directly won't necessarily cross-reference ADR 0008.
- **`distance_to_hole_metres`** — a Pydantic `@computed_field` property,
  derived via `caddai.gps.distance.haversine_distance_metres(position,
  hole_reference_position)` (an existing, pure `Coordinate -> Coordinate ->
  float` function in the already-approved `caddai.gps` dependency). This
  makes finiteness and non-negativity automatic — given two valid
  `Coordinate`s, the haversine formula always returns a finite value
  `>= 0` — so no separate validator is needed. Haversine, not
  `gps.projection`'s tangent-plane `to_local`/`to_coordinate`, is used
  deliberately: `gps.projection` requires an explicit projection-origin
  decision `GolfState` does not want to own (it is a leaf domain type, not
  a projection-owning one), whereas haversine is origin-independent and
  numerically adequate at golf-hole distances (well under 1 km) —
  consistent with `gps.distance`'s existing role as a leaf-module,
  dependency-free utility already used by `course/distance.py`. It is
  **not** special-cased to `0.0` when `holed=True` — see the `holed`
  rationale immediately below for why, and the corresponding rejected
  alternative in [Alternatives considered](#alternatives-considered).
- **`lie`** — a single closed `LieCategory` enum describing the surface/
  situation of the resulting position, including `PENALTY_AREA` and
  `OUT_OF_BOUNDS` as legitimate final-state values (the ball's final
  position *is* in that feature) — never silently `FAIRWAY` for unmapped
  geometry; `UNKNOWN` is the explicit fallback. No distinct `RECOVERY`
  category in V0 (unlike `strategy.LieType.RECOVERY`) — no current course
  geometry evidence backs a distinct recovery surface; `ROUGH` already
  serves as the conservative "difficult but playable" fallback, and
  `UNKNOWN` covers "unmapped/indeterminate." `PENALTY_AREA` deliberately
  collapses `course.FeatureType`'s (post-#83) `WATER` and generic
  `PENALTY_AREA` distinction — V0's expected-strokes model does not need
  water-specific treatment; a finer future split is a non-breaking-in-spirit
  enum addition, not designed now. See
  [docs/backlog.md](../backlog.md)'s existing item that putting is a
  behaviourally distinct shot regime not to be pooled with full-swing
  dispersion — relevant to how a future `E_base` must treat `GREEN` states,
  not a defect in `GolfState` itself.

  `LieCategory` is deliberately used broadly to mean "resulting-state/
  location category," not strictly "a lie the golfer plays a stock shot
  from." It mixes genuinely playable lies (`TEE`/`FAIRWAY`/`ROUGH`/
  `BUNKER`/`GREEN`) with non-playable resulting-location categories
  (`PENALTY_AREA`/`OUT_OF_BOUNDS`) and the unmapped fallback (`UNKNOWN`).
  Membership in this enum implies nothing about playability, nothing
  about whether a penalty stroke applies, and nothing about a Rules
  procedure — see "Rules/penalty boundary" below. This is a deliberate,
  simplest-defensible-V0 choice: a separate `PenaltyCategory`/Rules-state
  hierarchy was considered and rejected (see Alternatives) as unwarranted
  complexity for M5.
- **`holed`** — an explicit `bool`, never inferred from distance proximity
  or from coordinate equality against `hole_reference_position` — that
  direction remains forbidden. Unlike the first draft, `GolfState` no
  longer requires the *converse*: it does not require
  `position == hole_reference_position` when `holed=True`. Exact WGS84
  coordinate equality is too strong a proof of "holed" for real-world use
  — GPS endpoints are noisy, and `hole_reference_position` is itself only
  an approximation (green-centroid today, not a verified physical cup
  position); requiring bit-identical coordinates would make `GolfState`
  reject a golfer-asserted holed shot merely because two independently
  recorded points differ at the float level. `holed` remains an explicit,
  independently asserted fact — a future mapper/factory *may choose* to
  canonicalise a simulated holed result's `position` to
  `hole_reference_position` as an implementation strategy (issue #85's
  choice to make, not this ADR's), but `GolfState` itself no longer
  enforces that they match. The invariant this ADR **keeps, and this
  revision extends**: `holed=True` requires `lie` to be one of `TEE,
  FAIRWAY, ROUGH, BUNKER, GREEN` — i.e. `lie not in {OUT_OF_BOUNDS,
  PENALTY_AREA, UNKNOWN}`. The original rule (`lie != UNKNOWN`) already
  forbade holed-with-unknown-lie; this revision adds a QA-identified gap:
  `holed=True` combined with `lie=OUT_OF_BOUNDS` or `lie=PENALTY_AREA` is
  equally physically nonsensical — a ball resting out of bounds or in a
  penalty area is by definition not "in the hole." None of these three
  exclusions depend on coordinate equality and all remain sound under the
  relaxed invariant. No constraint that `holed` implies `lie == GREEN` (a
  hole-in-one from `TEE` is holed with an irrelevant/moot lie, and `TEE`
  remains a permitted `holed=True` lie). A
  `distance_to_hole_metres` value that is non-zero alongside `holed=True`
  is representable and intentionally not forbidden — `distance_to_hole_metres`
  is always computed via `haversine_distance_metres(position,
  hole_reference_position)` regardless of `holed`'s value, and is never
  special-cased to `0.0`. This is a **binding consumer contract, not a
  `GolfState`-internal one**: `holed=True` implies expected-strokes-
  remaining is semantically zero, and any consumer (`E_base`, Strokes
  Gained) **must** check `holed` first and short-circuit to zero — it must
  **never** read `distance_to_hole_metres`'s numeric value as a proxy for
  terminal status, regardless of what that value happens to be. Stated
  plainly: distance must not be used to infer `holed=True` (already true —
  `holed` is independently stored), **and** a non-zero
  `distance_to_hole_metres` alongside `holed=True` must not be treated by
  any consumer as evidence against `holed`'s own explicit value — `holed`
  is authoritative. A non-zero discrepancy is, if anything, a useful
  data-quality signal for a future decision journal (e.g. a golfer's
  recorded position was 2m from the recorded hole reference when they
  marked the shot holed), not a defect to hide by forcing the computed
  value to `0.0`. See "Error/unsupported semantics" below for the
  required `E_base` implementation shape and mandatory test this ADR now
  places on M5.9 to mitigate the consumer-side risk this relaxation
  introduces (recorded in "Consequences" below).
- **Removed from this draft — `is_penalty`**: the first draft stored an
  explicit `is_penalty: bool`, fully derived from `lie`. Removed because it
  conflated two different things: a resulting state being geometrically
  `PENALTY_AREA`/`OUT_OF_BOUNDS` does not by itself mean a penalty stroke
  was taken, that a specific Rules procedure occurred, or what happens
  next — the Rules of Golf permit playing a ball as it lies within a
  penalty area without penalty (Rule 17.1). See "Rules/penalty boundary"
  below and [Alternatives considered](#alternatives-considered). A future
  consumer wanting a convenience "is this a punitive location" predicate
  may compute `lie in {PENALTY_AREA, OUT_OF_BOUNDS}` itself.
- **Removed from this draft — `selected_target`**: the first draft
  required `selected_target: Coordinate`, the actual target the resulting
  `downrange_metres`/`lateral_metres` were measured against, citing the
  M5.0 research's domain invariant 5. It is required by the *mapper* to
  perform that transform, but it is not a property of the *resulting*
  state itself: two shots arriving at the same physical/course-relative
  state should compare equal as `GolfState` values regardless of what they
  were aimed at. This mirrors an existing, direct precedent already in
  this codebase: `caddai.player.models.ShotRecord`'s docstring explicitly
  documents that "`ShotRecord` stores only the resulting target-line-
  relative coordinates, never the target itself," for exactly this reason
  — a golfer's deliberate aim away from a recommended target must never be
  misread as player dispersion/bias by a future learning step; the same
  logic applies here: a shot's resulting `GolfState` must not encode what
  it was aimed at. The M5.0 research's domain invariant 5 is **not
  weakened** by this removal — it becomes a binding requirement on the
  **mapper's contract** (`simulation`, M5.4/M5.5), not on `GolfState`'s
  stored fields; see "Course-relative mapping responsibility" below. Now
  explicitly on the player/round exclusion list too. Future round/
  decision-journal work (M8) owns preserving selected-vs-recommended
  target context for traceability — outside `GolfState`.
- **Removed from this draft — `course_reference` / `hole_number`**: the
  first draft stored a `course_reference: str` / `hole_number: int` pair
  as a provisional stable-enough identifier. Removed in favour of Option B
  — course/hole identity is supplied by the surrounding context, not
  stored on `GolfState` — see "Course/hole identity: Option A vs Option B"
  below and [Alternatives considered](#alternatives-considered).

**Explicitly excluded from `GolfState`** (must not appear): player
identity, Handicap Index, carry ability, dispersion, bunker skill,
player-state adjustment, risk setting, current score, target score, Course
Handicap, Playing Handicap, WHS scoring policy, round history,
strokes-taken-so-far, wind/elevation/environment conditions at time of shot
(may be captured alongside `GolfState` by a future decision journal, not
inside it), penalty-stroke count, requires-relief/recovery marker (these
belong to a future expected-strokes/Rules-of-Golf-adjacent layer, M9, not
`GolfState`), **`is_penalty`** (newly excluded in this revision — see the
field rationale above; was a required field in the first draft),
**`selected_target`/selected-target context** (newly excluded in this
revision — see the field rationale above; was a required field in the
first draft), **`course_reference`** (newly excluded in this revision —
see the field rationale above; was a required field in the first draft),
**`hole_number`** (newly excluded in this revision — see the field
rationale above; was a required field in the first draft), raw Shapely
objects or GeoJSON properties. `extra="forbid"`
on `model_config` structurally prevents constructing `GolfState` with any
undocumented keyword (e.g. `handicap_index=...`), which raises a Pydantic
validation error rather than silently dropping the unrecognised field —
**but this only proves "no unexpected keyword arguments were passed at
construction time," not "this type is player-neutral."** Player-neutrality
is proven by (a) the declared field list above containing no player/round
concepts, and (b) the architecture-boundary/keyword-scan test recommended
for issue #82 (which scans `golf_state`'s actual source for forbidden
identifiers), not by `extra="forbid"` alone.

### Rules/penalty boundary

A new architectural principle, made explicit by removing `is_penalty`:

```
geometric/resulting state ≠ Rules procedure ≠ penalty strokes applied ≠ next playable state
```

`GolfState.lie` records where the ball physically ended up. It does not,
and must not be read to, record: whether a Rules procedure applies (e.g.
Rule 17.1 explicitly permits playing a ball as it lies within a penalty
area without penalty), whether a penalty stroke was actually incurred, or
what the golfer's next playable state/position will be after any required
relief/drop. These are genuinely distinct facts, not one derived from the
other, and none of them belong on `GolfState` — a resulting location is
not a ruling. A future consumer that wants a coarse "is this a punitive
location" shorthand may compute `lie in {PENALTY_AREA, OUT_OF_BOUNDS}`
itself; that is the consumer's own convenience, not a stored `GolfState`
truth.

### Course-relative mapping responsibility (recorded, not designed here)

`simulation` owns the mapping function (illustrative shape, not a literal
required signature): inputs = shot origin (`Coordinate`), the actual
selected target (`Coordinate`), intended target-line orientation, the
signed M4 `downrange_metres`/`lateral_metres` outcome, the resulting
position (post-rollout, from M5.4), and `course` geometry for the hole in
play; output = `GolfState`. It must reuse `gps.projection`'s tangent-plane
convention anchored at the shot origin (ADR 0002/0004 precedent) — no new
projection technique. This ADR does not design the mapping algorithm,
precedence rules for overlapping features, or the boundary-edge convention
— those are M5.5's job (issue #85), operating against this contract.

**Binding on the mapper, even though `selected_target` is not stored on
`GolfState`:** the M5.0 research's domain invariant 5 — the selected-target
frame must be preserved and never silently reinterpreted as pin, green
centre, or a CaddAI recommendation — is not weakened by removing
`selected_target` from `GolfState`'s stored fields (see the field
rationale above). It relocates to a binding requirement on **this mapper's
contract**: the mapper must receive and correctly use the actual shot
origin, the actual selected target the golfer aimed at (never substituted
with pin/green-centre/a CaddAI recommendation the golfer didn't select),
the intended target-line orientation, and the signed M4 downrange/lateral
values to compute the resulting `position` — regardless of the fact that
`GolfState` itself does not echo the target back out. Preserving
selected-vs-recommended target context for traceability across a whole
round is a future round/decision-journal concern (M8), outside
`GolfState`. Issue #85's own test suite should include a test case where
the actual selected target differs from CaddAI's recommendation, verifying
the mapper computes `position` from the real selected target and does not
silently substitute the recommendation — this is exactly the class of bug
a `GolfState`-level test cannot catch, since `selected_target` is no
longer a stored `GolfState` field.

### Course/hole identity: Option A vs Option B (Option B selected)

The first draft of this ADR stored `course_reference: str` / `hole_number:
int` on `GolfState` as a provisional stable-enough identifier pair. This
revision removes both fields and adopts **Option B**.

- **Option A — `GolfState` carries stable identity.** Would require
  defining a genuinely stable, unique opaque domain reference now — not
  the known-non-unique `Course.name`/`Hole.number` the first draft used
  (confirmed by reading `src/caddai/course/models.py`: `Course.name` is
  only constrained `min_length=1`, `Hole.number` only `gt=0` — neither is
  validated unique). Defining a real identity scheme prematurely belongs
  to a future M7 course-package/identity ADR, not this one — inventing one
  here would mean committing to an interim scheme before that ADR exists,
  and likely a second breaking change to this contract once it does.
  Rejected.
- **Option B — identity supplied by surrounding context (SELECTED).**
  `GolfState` contains only state/value-relevant physical semantics
  (`position`, `hole_reference_position`, `lie`, `holed`,
  `distance_to_hole_metres`). Course/hole identity remains with:
  - the mapping input/context — the caller already supplies `course`/
    `Hole` geometry as an *input* to the mapper per "Course-relative
    mapping responsibility" above, so it already has that identity in hand
    both before and after calling the mapper;
  - a future round state, a future decision journal, a future simulation
    scenario, or later product context, all of which can correlate that
    identity with each resulting `GolfState` externally.

  Justification against every anticipated consumer:
  - **Expected-strokes (`E_base`) needs**: only state characteristics —
    position, distance-to-hole, lie, holed — not which physical course/
    hole this is in a leaderboard/navigation sense.
  - **Strokes Gained needs**: the same.
  - **Simulation needs**: the mapper already receives `course`/`Hole` as
    an input; it does not need `GolfState` to echo an identifier back to
    itself.
  - **Synthetic validation needs**: a future harness's scenario/round
    context already tracks which hole is in play; it can correlate that
    externally with each resulting `GolfState` without `GolfState` needing
    to carry it (see "Expected-strokes, SG, and closed-loop simulation
    implications" below).
  - **Round model**: M8 owns round/hole navigation identity, not
    `GolfState`.
  - **M6 portability**: fewer, more stable fields, and no premature
    identity scheme to migrate later.
  - **Public contract stability**: avoids committing to any interim
    identifier scheme before a real M7 course-identity ADR exists, and
    the second breaking change to this contract that would otherwise
    entail.

### Rollout boundary (recorded only, not designed here)

The approved seam: M4 landing/carry-space `ShotOutcome` -> optional
replaceable rollout/final-position transform -> course-relative
classification -> `GolfState`. `GolfState` is agnostic to whether rollout
was identity/no-op or a coarse approximation (M5.4's job, issue #84) — no
rollout parameter, model version, or provenance marker belongs on
`GolfState` itself (that belongs on the rollout function's own output/
signature, internal to `simulation` before classification).

### Immutability

`GolfState` is `frozen=True`, matching `ShotOutcome`/`WindComponents`/
`EnvironmentInput`/`PlayerShotDistribution` precedent: safe sharing across
`simulation`/value/`strategy` batch evaluation, reproducibility, no
accidental mutation risk in Monte Carlo loops, consistent with every other
foundational value type in the codebase.

### Architecture invariants for `test_architecture_boundaries.py` (guidance for issue #82)

This ADR does not modify `tests/test_architecture_boundaries.py`; it
records the following as guidance for issue #82 to implement:

- A new `SubsystemBoundary(name="golf_state", source_files=(.../golf_state/
  __init__.py, .../golf_state/models.py), allowed_caddai_prefixes=
  ("caddai.golf_state", "caddai.gps"), plan_reference='GitHub issue #82
  ("M5.2 — GolfState domain contract implementation")')`. Stated
  explicitly: `golf_state` must not import `player`, `strategy`, or any
  round/product/mobile/cloud package — already implied by this allow-list
  containing only `caddai.golf_state`/`caddai.gps`, called out here in
  prose too.
- `simulation`'s boundary gains `caddai.golf_state` (already planned,
  M5.5) — this ADR confirms `caddai.golf_state` is the correct name.
- `course`'s boundary allow-list must remain `("caddai.course",
  "caddai.gps")` — it must **never** gain `caddai.golf_state`; that would
  be the dependency-direction violation this ADR explicitly rejects. This
  is enforced by *not modifying* `course`'s existing `SubsystemBoundary`
  `allowed_caddai_prefixes` entry when issue #82 lands — the already-
  existing parametrized boundary test structurally covers this once the
  new `golf_state` boundary is added elsewhere; no new dedicated test is
  required beyond leaving that entry unchanged.
- **Selected-target context must not be stored in `golf_state`.** New,
  given this revision's removal of `selected_target` (see the field
  rationale above). It is structurally enforced by the field list itself
  plus `extra="forbid"` — no additional `golf_state`-scoped forbidden-
  identifier keyword is needed for it.
- **Course identity/provider objects must not leak into `golf_state`**
  unless a future ADR explicitly chooses a stable neutral reference — this
  ADR does not (Option B, see above).
- A **required** keyword-scan test for `golf_state`'s own source (not
  merely a recommendation), asserting it contains none of: `handicap`,
  `risk`, `score`, `whs`, `round_`, `player` (case-insensitive) —
  enforcing player-neutrality structurally, not just by field-list
  convention. This mirrors the existing, mandatory
  `test_simulation_contains_no_rules_of_golf_policy_identifiers` precedent
  already in `tests/test_architecture_boundaries.py`: issue #82 must add
  an equivalent, non-optional test for `golf_state`, not treat it as an
  optional nice-to-have. `player`/`round_` already cover the concepts this
  revision newly excludes (`selected_target`, `course_reference`,
  `hole_number`) — no new keyword is needed for those; their absence is
  enforced structurally by the field list itself plus `extra="forbid"`,
  not by this keyword scan. This should be (a) a separate, `golf_state`-
  scoped identifier tuple, not merged into `simulation`'s existing
  `FORBIDDEN_POLICY_IDENTIFIERS` (the two subsystems' forbidden
  vocabularies are unrelated), and (b) implemented with word-boundary-aware
  matching (e.g. a regex using `\b`) rather than plain substring
  containment, since e.g. `"score"` is a substring of unrelated words such
  as `"underscore"` and a plain-substring check would false-positive. The
  `round_` identifier needs particular care: because `_` is itself a regex
  word character, `\bround_\b` would **not** match `round_number`/
  `round_id` (there is no word boundary between `_` and the following
  letter) — the intended pattern is `\bround_` (a leading word boundary,
  deliberately with no trailing `\b`), which correctly matches
  `round_number`, `round_id`, and similar identifiers.
- `strategy`'s boundary will later gain `caddai.golf_state` (M5.11, not
  this issue); a future value module consumes `caddai.golf_state` (M5.8,
  not this issue) — `simulation` may consume `course` + `golf_state`.

### Error/unsupported semantics (guidance, not binding on #85)

- Missing/degenerate course geometry input to the mapper: the mapper must
  raise a clear, typed error — never fabricate a "best guess" `GolfState`.
- An ordinary point outside every mapped feature: a valid, well-formed
  `GolfState` with `lie=UNKNOWN`, `holed=False` — not an error. `UNKNOWN`
  must never be treated as "safe"/fairway-like by downstream consumers —
  this is guidance for M5.9; `GolfState` cannot enforce a consumer's
  behaviour by itself. To make this more than prose discipline, M5.9's
  `E_base` implementation should use an exhaustive `match` statement (or
  equivalent) over `LieCategory` with **no catch-all/default branch** (no
  bare `case _:`), so mypy strict mode flags a missing case at type-check
  time if `LieCategory` ever gains a new member without a corresponding
  `E_base` branch — rather than relying on a silent fairway-like default
  for `UNKNOWN` (or any future member) going unnoticed.
- **`holed` short-circuit is required, not merely documented** (this
  directly mitigates the consumer-side regression recorded in
  "Consequences" below): M5.9's `E_base` implementation must make
  bypassing the `holed` check awkward by construction, not just avoid it
  by convention. `E_base`'s own function body must check `state.holed` as
  its literal first statement and short-circuit to `0.0` before touching
  `lie` or `distance_to_hole_metres` at all — never compute a distance- or
  lie-based value first and special-case `holed` afterward. M5.9 **must**
  include a parametrized unit test asserting `E_base` returns exactly
  `0.0` for `holed=True` across multiple arbitrary, non-zero
  `distance_to_hole_metres` values — not a single near-zero-distance case,
  which would pass even if the short-circuit were absent and the result
  were merely incidentally correct. This test is required, not optional,
  exactly like the exhaustive-`match`/no-catch-all requirement for
  `UNKNOWN` immediately above.
- Ambiguous/overlapping feature classification precedence is M5.5's job
  (issue #85) — this ADR only requires that whatever `lie` M5.5 resolves to
  is a single, valid `LieCategory` member; `GolfState` has no opinion on the
  precedence rule itself.
- Malformed state (`holed=True` with `lie` in `{UNKNOWN, OUT_OF_BOUNDS,
  PENALTY_AREA}`) is rejected at construction via Pydantic validation —
  never silently coerced; see the `holed` field rationale above for why
  all three exclusions are physically required, not just the original
  `UNKNOWN` case. This revision removes the first draft's other
  malformed-state rule (`holed=True` and `is_penalty=True` together) along
  with `is_penalty` itself. `distance_to_hole_metres` no longer needs its
  own finiteness/
  non-negativity validation: as a `@computed_field` derived via
  `haversine_distance_metres`, it is always finite and `>= 0` given two
  valid `Coordinate`s, by construction of the haversine formula itself —
  there is no separate malformed-float state to reject.
- `GolfState` does not verify `distance_to_hole_metres` against `position`
  (the drift risk this would require is eliminated structurally — see the
  `hole_reference_position`/`distance_to_hole_metres` field rationale
  above): the value is always recomputed from whichever `position`/
  `hole_reference_position` are currently stored. This revision also drops
  the first draft's requirement that the mapper copy
  `hole_reference_position` verbatim into `position` for a holed result —
  see the `holed` field rationale above: a mapper *may* still choose to
  canonicalise a holed result's `position` this way, but `GolfState` no
  longer requires or checks it.

### Batch/Monte Carlo considerations

`GolfState` is a small, flat value object (two `Coordinate`s, one computed
float, one `bool`, one enum) — O(1), no I/O, no geometry lookups, no
provider calls per construction; safe to construct thousands of times in a
Monte Carlo candidate-evaluation loop. A future batch/vectorised
representation (e.g. a NumPy structure-of-arrays mirroring these same
fields) may be introduced later for vectorised `E_base` evaluation without
changing this per-sample semantic contract — not designed now.

Because `selected_target` is no longer a `GolfState` field (see above),
two Monte Carlo samples with identical resulting golf facts (same
`position`, `hole_reference_position`, `lie`, `holed`) now compare equal as
`GolfState` values regardless of what each was aimed at — there is no
longer a hidden field that would otherwise make two physically-identical
resulting states compare unequal. `strategy`'s own candidate aggregation
(M5.11's `CandidateValueDistribution`) must still group samples by the
caller's own candidate/target identity externally, since `GolfState` itself
carries no target/candidate identity to group by.

### M6 portability

Every field is a plain scalar/categorical value (float, bool, `StrEnum`, or
a two-float `Coordinate`) — no Shapely geometry, no embedded `Course`/
`Hole`/`Feature` objects, no Python-specific behaviour baked into the
domain definition. It is directly representable in any future schema
(Protobuf, JSON Schema, a Rust struct) without redesign. No serialization
format, FFI mechanism, or schema-version field is chosen here — that is a
future, narrower decision if/when `GolfState` crosses a language/process
boundary (M6).

This revision shrinks the contract further than the first draft: from 8
fields (3 `Coordinate`s, 2 `bool`s, 1 enum, 1 `str`, 1 `int`, 1 computed
`float`) to 4 stored fields (2 `Coordinate`s, 1 enum, 1 `bool`) plus 1
computed `float`. The result is even smaller, carries no unstable
identifiers (`course_reference`/`hole_number` removed), and carries no
mapper-input history (`selected_target` removed) — still no Python-
specific semantics beyond the enum/computed-field convenience.

### Public API ownership

`caddai.golf_state`'s public surface in V0 is exactly `GolfState` and
`LieCategory` — a pure data contract, no mapping/classification functions,
no factory helpers. Construction is via ordinary Pydantic keyword
construction, performed by `simulation`'s mapper (M5.5) — `golf_state` does
not expose a builder function, keeping the module strictly
data-contract-only.

## Rationale

`GolfState` sits at the exact seam AGENTS.md §2.1 and §3 already require: a
deterministic, course-relative fact, produced by `simulation` and consumed
by expected-strokes/`strategy`, never influenced by an LLM or a network
call. Making it a small, neutral, dependency-light module rather than
folding it into `simulation` or `strategy` keeps it reusable by every
current and anticipated consumer (expected-strokes/value, `strategy`, a
future decision journal, a future synthetic validation harness) without
forcing any of them to import an unrelated subsystem merely for a type, and
keeps its own M6 portability timeline independent of whichever subsystem is
likeliest to be reimplemented first. Closing the `lie` enum and making
`holed` an explicit, validated field — rather than leaving it derivable or
optional — directly encodes the M5.0 research's domain invariants (no
silent `FAIRWAY` default, no proximity-based holed inference) as
Pydantic-enforced constraints instead of conventions a future contributor
could accidentally violate.

This revision shrinks the contract on the principle that `GolfState`
should store only facts that are properties of the *resulting state
itself*, not facts about how that state was reached or what surrounding
identity context it belongs to. `selected_target` is a mapper input, not a
resulting-state property — this mirrors `caddai.player.models.ShotRecord`'s
existing, explicit precedent of storing only target-line-relative
coordinates, never the target itself. `is_penalty` conflated a location
category with a Rules/scoring consequence, which are genuinely distinct
facts (`geometric/resulting state ≠ Rules procedure ≠ penalty strokes
applied ≠ next playable state`, see "Rules/penalty boundary" above) —
removing it keeps `GolfState` a pure statement of *where the ball ended up
and what that location category is*, leaving Rules/scoring interpretation
to its consumers. `course_reference`/`hole_number` were a premature
identity scheme; Option B keeps `GolfState` value-only and defers identity
to context that already has it.

## Consequences

- Positive: `simulation`, a future expected-strokes/value module (M5.8),
  and `strategy` can all be implemented against one stable, tested contract
  — `GolfState`'s shape does not change as those consumers are built.
- Positive: the closed `LieCategory` enum and the validated `holed`/
  `lie not in {OUT_OF_BOUNDS, PENALTY_AREA, UNKNOWN}` rule make the
  remaining impossible/ambiguous states ("holed with an unknown lie",
  "holed while out of bounds", "holed while in a penalty area")
  unrepresentable at construction, not just discouraged by convention. A
  non-zero computed `distance_to_hole_metres` alongside `holed=True`
  remains representable and is intentionally not forbidden — see the
  `holed` field rationale above; this is a deliberate design choice (a
  data-quality signal, not a defect), not a gap.
- Positive: removing `is_penalty` eliminates a field whose value was fully
  derivable from `lie` and that risked conflating a location category with
  a Rules/scoring consequence — see "Rules/penalty boundary" above.
  Consumers that want a coarse punitive-location shorthand compute it
  themselves from `lie`.
- Positive: removing `selected_target` means two shots that reach the same
  physical/course-relative state now compare equal as `GolfState` values
  regardless of what they were aimed at — matching the `ShotRecord`
  precedent and removing a field most consumers (expected-strokes, Strokes
  Gained) never needed.
- Positive: removing `course_reference`/`hole_number` (Option B) avoids
  committing to a premature, non-unique identity scheme now — see
  "Course/hole identity: Option A vs Option B" above — and removes the
  churn/migration risk the first draft's negative consequence below
  described.
- Positive: `GolfState`'s single outgoing dependency (`caddai.gps`) and
  flat, plain-scalar field shape make it trivially portable to a future M6
  language/schema boundary without redesign — now an even smaller surface
  than the first draft's (see "M6 portability" above).
- Positive: module ownership (Strategy Engineer) matches the two
  subsystems most coupled to this type's lifecycle. `simulation` is the
  sole mapping owner by convention and by which module actually performs
  classification — like `ShotOutcome`/`WindComponents` today, `GolfState`
  is an ordinary public Pydantic model, so nothing structurally prevents
  another approved consumer (e.g. `strategy`, once M5.11 adds that
  dependency edge) from constructing one directly; this is a documented
  convention, not an enforced guarantee, consistent with how every other
  foundational value type in this codebase already works.
- Negative: `hole_reference_position`/`distance_to_hole_metres` will
  initially resolve against green-centroid distance, not a true pin
  distance, because `Hole.pin_position` does not exist yet — a semantic
  approximation every M5.4/M5.5 consumer and any downstream
  expected-strokes evaluation must be aware of until pin data is added.
  This is purely a *semantic* limitation of what `hole_reference_position`
  currently refers to, not a structural risk: because
  `distance_to_hole_metres` is a `@computed_field` derived from
  `position`/`hole_reference_position` rather than a separately stored
  float, drift/verification risk between a stored distance and `position`
  is eliminated structurally, not merely mitigated.
- Negative: collapsing `WATER`/generic `PENALTY_AREA` into a single
  `LieCategory.PENALTY_AREA` value means V0's expected-strokes model cannot
  distinguish water-specific outcomes from other penalty areas without a
  future, non-breaking enum addition.
- Negative: relaxing the `holed` invariant means `GolfState` can no longer
  itself catch a mapper bug that produces a holed result whose `position`
  is far from `hole_reference_position` — that check, if wanted, is now
  the mapper's (#85) own responsibility, not something `GolfState`'s
  constructor enforces.
- Negative: relaxing the `holed` invariant also introduces a new
  *consumer*-side foot-gun that the first draft's exact-coordinate-
  equality rule prevented for free. Under the first draft,
  `holed=True ⇒ position == hole_position` meant `distance_to_hole_metres`
  was structurally `0.0` whenever `holed=True`, so even a naive `E_base`
  that forgot to check `holed` first got the right answer (zero remaining
  strokes) by accident. That safety net is gone: a naive `E_base` that
  reads `distance_to_hole_metres` instead of checking `holed` first will
  now silently compute a wrong, nonzero expected-strokes value, with zero
  structural signal that anything is wrong — unlike the `UNKNOWN`-handling
  guidance above, where an exhaustive `match` with no catch-all lets mypy
  strict catch a missing case, this is not a missing `LieCategory` case at
  all, so the type checker cannot catch it. See "Error/unsupported
  semantics" above for the required `E_base` implementation shape and
  mandatory parametrized test this ADR now places on M5.9 to mitigate it.

## Expected-strokes, SG, and closed-loop simulation implications

- The amended, smaller `GolfState` still supports a future `E_base(state)`
  for `FAIRWAY`/`ROUGH`/`BUNKER`/`GREEN`/`UNKNOWN` and, with caveats, for
  `PENALTY_AREA`/`OUT_OF_BOUNDS`. For location categories where a V0 value
  model cannot legitimately produce a number without Rules-transition
  semantics that don't exist yet (M9) — most plausibly `OUT_OF_BOUNDS` and
  possibly `PENALTY_AREA` — `E_base` must be explicitly permitted to return
  an **unsupported/requires-transition** signal rather than inventing a
  numeric value. This is guidance for M5.8/M5.9, not decided here.
- Not every mapper output can immediately enter
  `SG_base = E_base(current) - (1 + E_base(result))` — some resulting
  classifications may first require a round/Rules transition (e.g. a drop,
  a replay) that does not exist as a modelled concept yet. This is an
  explicit, acknowledged architectural gap for M5.7–M5.11 to resolve — it
  is not implemented or resolved here.
- Closed-loop synthetic validation (`GolfState -> recommendation -> shot ->
  resulting state -> next decision`) composes cleanly without `GolfState`
  carrying course/hole identity: the surrounding scenario/round context
  already knows which hole is in play (it's what fed geometry into the
  mapper) and can correlate that identity with each resulting `GolfState`
  itself, externally — `GolfState` not carrying identity does not break
  this loop, per "Course/hole identity: Option A vs Option B" above.

## Alternatives considered

1. **`GolfState` owned by `caddai.simulation`** — rejected: over-scopes
   `simulation`, forces every non-simulation consumer (a future round
   model, decision journal, synthetic validation harness) to import an
   irrelevant subsystem merely for a type, and ties the type's
   portability/M6 migration timeline to whichever subsystem is likeliest to
   be reimplemented first.
2. **`GolfState` owned by `caddai.strategy`** — rejected: would force
   `simulation` to import `strategy` to construct/return the type it
   produces, inverting the documented `strategy -> simulation` direction
   (`AGENTS.md` §3/§13) — a structural dependency-direction violation, not
   a style preference.
3. **State spread across ad-hoc existing types** (e.g. adding lie/penalty/
   holed fields directly to `simulation.ShotOutcome`, or to
   `course.Feature`) — rejected: conflates a forward-modelled,
   target-line-relative physics outcome (`ShotOutcome`) with a
   course-relative semantic fact; would force `course.Feature` (a
   geometry/provider type) to carry golfer-outcome fields, violating
   `course`'s own documented non-goals (no golfer strategy, no
   player-specific state).
4. **Deferring `GolfState` entirely until the M8 round/scoring model
   exists**, and evaluating expected strokes against that instead —
   rejected: couples M5 (a single-shot/candidate evaluation concern) to an
   undesigned future milestone, would embed round/score/WHS context into
   what must remain a neutral per-candidate evaluation state, and stalls
   the entire milestone on unrelated round-lifecycle design.
5. **A separate optional `penalty: PenaltyCategory | None` field** instead
   of a single closed `lie` enum containing `PENALTY_AREA`/
   `OUT_OF_BOUNDS` — rejected: leaves `lie` undefined/ambiguous during a
   penalty state, exactly the kind of "impossible/ambiguous combination"
   this contract should make hard to represent; a single closed `lie` enum
   already carries `PENALTY_AREA`/`OUT_OF_BOUNDS` as ordinary members with
   no such gap (see "Rules/penalty boundary" above for why no derived
   `is_penalty`-style convenience flag is stored either).
6. **Storing `position` as a local-metre point** (`gps.projection.
   LocalPoint`) relative to the shot origin, instead of a `Coordinate` —
   rejected: only meaningful alongside the anchor origin, which would then
   also need storing; a plain `Coordinate` is self-contained, matches
   `course.Feature.position`'s existing convention, and is more portable.
7. **Embedding a live `Course`/`Hole` object reference** instead of
   `course_reference`/`hole_number` — rejected: couples `GolfState` to a
   mutable provider object graph, breaks portability, and violates the
   "not an embedded mutable Course/Hole graph" invariant from the M5.0
   research.
8. **A distinct `RECOVERY` lie category** (mirroring `strategy.LieType`) —
   rejected for V0: no current course geometry evidence backs a distinct
   recovery surface; revisit only if real evidence/consumer need emerges.
9. **Storing `distance_to_hole_metres` as a precomputed float field**,
   computed once by the mapper from `course` geometry + `position` — this
   was this ADR's original draft, and is now rejected in favour of storing
   `hole_reference_position: Coordinate` and deriving
   `distance_to_hole_metres` as a `@computed_field`. The stored-float
   approach left `GolfState` structurally unable to verify the distance
   against `position` (it holds no course geometry), an acknowledged drift
   risk between two values that must otherwise be kept in sync by
   convention. Deriving the distance from a stored `hole_reference_position`
   instead makes drift definitionally impossible — there is only one
   source of truth (`position`/`hole_reference_position`), not two
   independently-settable values — at the cost of one extra nested
   `Coordinate` field, which is O(1)/cheap per the `ShotOutcome`/
   M4-sampling Monte Carlo precedent (see the `hole_reference_position`
   field rationale above). This is the option ultimately adopted.
10. **Storing `selected_target: Coordinate` on `GolfState`** — this ADR's
    own first draft, required per the M5.0 research's domain invariant 5.
    Now rejected: it is a mapper input, not a property of the resulting
    state — two shots reaching the same physical/course-relative state
    should compare equal as `GolfState` values regardless of what they
    were aimed at, mirroring `caddai.player.models.ShotRecord`'s existing
    precedent of storing only resulting target-line-relative coordinates,
    never the target itself. The underlying domain invariant is preserved,
    relocated to a binding mapper-contract requirement instead (see
    "Course-relative mapping responsibility" above).
11. **Storing `is_penalty: bool` on `GolfState`** — this ADR's own first
    draft, added so consumers never need embedded knowledge of which `lie`
    values are punitive. Now rejected: it was fully derivable from `lie`
    (redundant), and it conflated a resulting location category with a
    Rules/scoring consequence, which are genuinely distinct — a ball in
    `PENALTY_AREA` may be played without penalty under Rule 17.1. See
    "Rules/penalty boundary" above. A consumer wanting this shorthand
    computes it itself from `lie`.
12. **Requiring `holed=True ⇒ position == hole_position` exact coordinate
    equality** — this ADR's own first draft's invariant. Now rejected:
    exact WGS84 coordinate equality is too strong a proof of "holed" given
    noisy GPS endpoints and an approximate `hole_reference_position`; it
    would make `GolfState` reject a golfer-asserted holed shot merely
    because two independently recorded points differ at the float level.
    See the `holed` field rationale above.
13. **Forcing `distance_to_hole_metres` to `0.0` when `holed=True`** —
    considered as part of this revision (an alternative to the invariant
    in #12) and rejected in favour of the consumer-contract approach:
    forcing the computed distance to `0.0` whenever `holed` is true would
    hide a genuine, potentially useful geometric discrepancy (e.g. a
    data-quality signal for a future decision journal) and would
    reintroduce exactly the kind of "magic override tied to a boolean"
    this contract otherwise avoids. Instead, consumers must check `holed`
    first and never read `distance_to_hole_metres` as a proxy for terminal
    status — see the `holed` field rationale above.
14. **Option A — `GolfState` carries stable course/hole identity** — this
    ADR's own first draft's `course_reference`/`hole_number` fields. Now
    rejected in favour of Option B: defining a genuinely stable, unique
    identity scheme now is premature and belongs to a future M7
    course-package/identity ADR; today neither `Course.name` nor
    `Hole.number` is even validated unique, an acknowledged weakness of
    the first draft's approach that Option B moots entirely by removing
    the fields. See "Course/hole identity: Option A vs Option B" above.

## Dependency implications

`caddai.golf_state` adds exactly one new outgoing edge to the dependency
graph (`golf_state -> caddai.gps`) and three new incoming edges this ADR
authorises (`simulation -> golf_state`, a future M5.8 value module ->
`golf_state`, `strategy -> golf_state`), plus one edge this ADR explicitly
forbids (`course -> golf_state`). No existing approved dependency
(`AGENTS.md` §9: Pydantic v2, NumPy, Shapely, FastAPI, Typer / pytest,
Ruff, mypy) changes — `golf_state` needs only Pydantic v2 and stdlib. This
does not, by itself, modify `tests/test_architecture_boundaries.py`; that
allow-list change is scoped to issue #82.

## Migration and portability implications

No production code exists yet, so there is no migration of existing data.
The provisional nature of `hole_reference_position` (green-centroid
fallback, pending `Hole.pin_position`) is recorded here precisely so a
future pin-data addition knows exactly which field's *semantics* — not its
type — will need revisiting, without another `GolfState`-shape ADR being
required for that alone (`hole_reference_position` remains a `Coordinate`
whether it holds a green-centroid or a true pin position; only what it
*means* changes). Course/hole identity now has no field to migrate at all
(Option B, see above) — a future M7 course-identity ADR is free to design
whatever scheme it needs without any `GolfState` migration. `GolfState`'s
all-scalar/categorical field shape (no Shapely geometry, no embedded
provider objects) is deliberately chosen so a future M6 language/process
boundary can represent it in another schema (Protobuf, JSON Schema, a Rust
struct) without a redesign of the contract itself — only a serialization
mapping. A `@computed_field` (`distance_to_hole_metres`) is a Pydantic/
Python-specific convenience for consumers within this codebase; a future
M6 schema representation would recompute it from `position`/
`hole_reference_position` on the far side of the boundary rather than
needing to serialize it as a stored field.

## Non-goals

This ADR does not: design the course-relative classification/mapping
algorithm, feature-overlap precedence, or boundary-edge convention (M5.5,
issue #85); design the rollout/final-position transform (M5.4, issue #84);
design the expected-strokes numeric model, its data source, or the
`E_base`/`Delta` split (M5.7–M5.9, gated by its own separate `HUMAN
DECISION REQUIRED`); modify `tests/test_architecture_boundaries.py` (issue
#82); add `ROUGH`/`PENALTY_AREA` to `course.FeatureType` or a
point-in-polygon primitive (issue #83); or design a batch/vectorised
`GolfState` representation for Monte Carlo performance. It also does not
change any already-Accepted ADR (0001–0007).

## Relationship to M5.0 research

This ADR operationalises
[docs/research/m5-golf-state-expected-strokes.md](../research/m5-golf-state-expected-strokes.md)
sections D (`GolfState` requirements) and E (`GolfState` ownership options)
into a binding contract: it adopts the spike's recommended Option (a) — a
new neutral top-level module — as `caddai.golf_state`, confirms `simulation`
as the mapping owner per the spike's already-approved decision, and encodes
the spike's section D domain invariants (explicit `lie`/`holed` fields, no
silent `FAIRWAY` default) as concrete Pydantic field/validator decisions.
Section D's distance-to-hole row favoured "storing it as a resolved
scalar... [so] every consumer [avoids] needing course-geometry access just
to read a distance" over deriving it on demand; this ADR honours that
intent — no consumer needs course-geometry access to read
`distance_to_hole_metres` — by storing `hole_reference_position` (itself a
resolved point, requiring the same course-geometry access the spike
anticipated) and deriving the distance from it via a dependency-free,
course-geometry-free `haversine_distance_metres` call, rather than storing
the distance as an independent scalar that could drift from `position`/
`hole_reference_position`. It does not revisit or re-decide the
already-approved semantic architecture direction itself, and it leaves the
spike's separate, still-unresolved expected-strokes numeric-baseline
follow-on entirely untouched.

This revision refines, rather than reopens, the M5.0-approved direction.
The spike's domain invariant 5 (the selected-target frame must be
preserved, never silently reinterpreted as pin/green-centre) is still
fully honoured — it is simply relocated from a stored `GolfState` field to
a binding mapper-contract requirement (see "Course-relative mapping
responsibility" above), following the same `ShotRecord`
target-line-relative-coordinates-only precedent cited there. The removed
`course_reference`/`hole_number` fields were the M5.0 research's own
tentative "yes, in shape" recommendation for identity; this ADR, now with
the benefit of Adversarial Review scrutiny of its own first draft, revises
that recommendation to Option B (identity supplied by surrounding
context). This is a legitimate contract refinement within this ADR's own
scope — it narrows the exact field set the spike left for this ADR to
decide precisely — not a reopening of `course`/`simulation`/`golf_state`/
value/`strategy`'s ownership responsibilities or dependency direction,
which remain exactly as this ADR's Decision section already stated.
