# 0008. GolfState domain contract and ownership

## Status

Proposed. The semantic direction this ADR elaborates — `course` owns
geometry, a new neutral module owns player-neutral course-relative state,
`simulation` owns the `ShotOutcome` + shot origin + actual selected target +
course geometry -> `GolfState` mapping, expected-strokes/value consumes
`GolfState`, `strategy` consumes distributions of resulting values — was
already explicitly human-approved during the M5.0 research spike (issue
#11: "APPROVED — semantic architecture direction only... A dedicated ADR
(M5.1) is still required before implementation"). This ADR turns that
already-approved direction into a precise, binding contract (exact fields,
types, validators, ownership, and dependency edges); it does not introduce a
materially different, unapproved direction.

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
   collapsed into a single `PENALTY_AREA` member).
3. The exact `GolfState` field set and its validated invariants, including
   the `is_penalty`/`holed` mutual-exclusion rule and the `holed`/
   `lie != UNKNOWN` exclusion.

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
    hole_position: Coordinate
    lie: LieCategory
    is_penalty: bool
    holed: bool
    selected_target: Coordinate
    course_reference: str = Field(min_length=1)
    hole_number: int = Field(gt=0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def distance_to_hole_metres(self) -> float:
        return haversine_distance_metres(self.position, self.hole_position)
```

`# type: ignore[prop-decorator]` matches the existing `computed_field`
precedent in `caddai.player.models` (mypy strict does not yet understand
`@computed_field` stacked on `@property`).

Two implementation notes for whichever issue implements/consumes this:

- `extra="forbid"` combined with a `@computed_field` means
  `GolfState.model_validate(instance.model_dump())` will **not** round-trip
  — `model_dump()` serializes `distance_to_hole_metres` out, but
  `model_validate()` rejects it back in as an unexpected keyword under
  `extra="forbid"`. Any future persistence/replay path (e.g. a decision
  journal, M8) must reconstruct `GolfState` from its *stored* fields only
  (`position`, `hole_position`, ...), never from a full `model_dump()`
  round-trip. Not an issue for M5 itself (no persistence exists yet).
- The `holed=True` requires `position == hole_position` invariant assumes
  the mapper (M5.5) assigns `hole_position`'s exact value to `position` when
  it determines the ball is holed, rather than two independently computed
  `Coordinate`s that could differ at the float level (e.g. rollout landing
  very close to, but not bit-identical to, the pin). Issue #85 must copy
  `hole_position` verbatim into `position` for a holed result, not
  recompute/re-derive it — this ADR states the invariant; #85 is
  responsible for satisfying it exactly.

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
- **`hole_position`** — stored as data, not `distance_to_hole_metres` as a
  precomputed float, structurally eliminating the drift risk between a
  stored distance and `position`: `distance_to_hole_metres` is derived
  on demand (see below), so it is definitionally always consistent with
  whichever `position`/`hole_position` pair is currently stored — there is
  no second value that can go stale. `hole_position` is whichever
  hole-location reference the mapper actually resolved: a true pin
  position if/when `Hole.pin_position` exists, or today's green-centroid
  fallback (`course.distance.green_front_centre_back_distances`'s
  "centre") per `docs/course-engine.md`'s documented gap. `GolfState`
  stores whichever `Coordinate` the mapper used, without needing to know
  or care which — it is computed once by the mapper (`simulation`, M5.5)
  from `course` geometry, exactly as the previous draft's stored distance
  was, just one derivation step earlier. This adds a third nested
  `Coordinate` submodel to `GolfState` (alongside `position`/
  `selected_target`); this is still O(1)/cheap construction, consistent
  with the existing `ShotOutcome`/M4-sampling Monte Carlo precedent of
  constructing small, flat, multi-field value objects (including nested
  `Coordinate`/vector fields) thousands of times per candidate-evaluation
  loop without measurable overhead.
- **`distance_to_hole_metres`** — a Pydantic `@computed_field` property,
  derived via `caddai.gps.distance.haversine_distance_metres(position,
  hole_position)` (an existing, pure `Coordinate -> Coordinate -> float`
  function in the already-approved `caddai.gps` dependency). This makes
  finiteness and non-negativity automatic — given two valid `Coordinate`s,
  the haversine formula always returns a finite value `>= 0` — so no
  separate validator is needed; this removes the "finite, >= 0" comment
  ambiguity a stored-float draft would otherwise require. Haversine, not
  `gps.projection`'s tangent-plane `to_local`/`to_coordinate`, is used
  deliberately: `gps.projection` requires an explicit projection-origin
  decision `GolfState` does not want to own (it is a leaf domain type, not
  a projection-owning one), whereas haversine is origin-independent and
  numerically adequate at golf-hole distances (well under 1 km) —
  consistent with `gps.distance`'s existing role as a leaf-module,
  dependency-free utility already used by `course/distance.py`.
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
- **`is_penalty`** — an explicit `bool`, required by the M5.0 research's
  domain invariant that penalty state must be "an explicit, structured
  field... never a magic distance value or an overloaded lie category" —
  even though it is fully determined by `lie` (`True` iff `lie` is
  `PENALTY_AREA` or `OUT_OF_BOUNDS`, validated at construction, not
  independently settable), it exists so consumers (`E_base`, `strategy`)
  never need embedded golf-domain knowledge of which `lie` values are
  punitive. A future expected-strokes/Strokes-Gained model must still
  condition on `lie` itself (which preserves the `OUT_OF_BOUNDS` vs.
  `PENALTY_AREA` distinction), never treat `is_penalty` as an
  expected-strokes-equivalence shortcut between those two outcomes — under
  the Rules of Golf they have materially different procedures/consequences
  (stroke-and-distance vs. a proximate drop); `is_penalty` exists only as a
  coarse "should this be scored worse than a playable lie" convenience
  signal, not a claim that all penalty outcomes are equivalent.
- **`holed`** — an explicit `bool`, never inferred from distance proximity
  (invariant: `holed=True` requires `position == hole_position` exactly —
  the mapper sets both to the identical `Coordinate` when it determines
  the ball is holed; this is a sanity check on the mapper's output, not an
  inference rule `GolfState` performs itself). `holed=True` and
  `is_penalty=True` are mutually exclusive — rejected at construction as a
  contradictory state. `holed=True` also requires `lie != UNKNOWN` — a
  ball cannot be simultaneously holed and of unknown lie; also rejected at
  construction. No constraint that `holed` implies `lie == GREEN` (a
  hole-in-one from `TEE` is holed with an irrelevant/moot lie). A
  `distance_to_hole_metres == 0.0` with `holed=False` is representable and
  intentionally not forbidden: `GolfState` does not treat "zero remaining
  distance" as implying holed (that would be exactly the "magic zero
  distance" inference this contract explicitly forbids elsewhere) — the
  mapper alone decides `holed`.
- **`selected_target`** — the actual target `Coordinate` the resulting
  `downrange_metres`/`lateral_metres` were measured against for this shot,
  preserved exactly as given, per the M5.0 research's explicit domain
  invariant 5 ("must not be silently reinterpreted as pin or green
  centre"). Required, not optional — the mapping operation always has one.
  Do not remove this field: it is a binding requirement from the M5.0
  research, not optional.
- **`course_reference` / `hole_number`** — a stable-enough identifier pair,
  not an embedded `Course`/`Hole` object graph. Explicitly provisional:
  `course_reference` is expected to be populated from `Course.name` today
  (the only identity `Course` currently exposes) — a known limitation
  pending a real stable course-package identifier/versioning scheme (M7),
  not invented here. `course_reference` is `Field(min_length=1)`, matching
  `Course.name`'s existing `min_length=1` convention exactly — no
  additional whitespace-stripping requirement is imposed. `hole_number` is
  `Field(gt=0)`; that is the only constraint `GolfState` can itself
  enforce or test in isolation, since it holds no `Course`/`Hole` object to
  cross-check against. Saying `hole_number` "matches `Hole.number`" means
  the mapper is expected to populate it from the real `Hole.number` it
  mapped against, not that `GolfState` validates that correspondence
  itself.

**Explicitly excluded from `GolfState`** (must not appear): player
identity, Handicap Index, carry ability, dispersion, bunker skill,
player-state adjustment, risk setting, current score, target score, Course
Handicap, Playing Handicap, WHS scoring policy, round history,
strokes-taken-so-far, wind/elevation/environment conditions at time of shot
(may be captured alongside `GolfState` by a future decision journal, not
inside it), penalty-stroke count, requires-relief/recovery marker (these
belong to a future expected-strokes/Rules-of-Golf-adjacent layer, M9, not
`GolfState`), raw Shapely objects or GeoJSON properties. `extra="forbid"`
on `model_config` enforces this structurally, not just by omission:
constructing `GolfState` with any undocumented keyword (e.g.
`handicap_index=...`) raises a Pydantic validation error, not a silent
drop of the unrecognised field.

### Course-relative mapping responsibility (recorded, not designed here)

`simulation` owns the mapping function (illustrative shape, not a literal
required signature): inputs = shot origin (`Coordinate`), the actual
selected target (`Coordinate` — never substituted with pin/green-centre/a
CaddAI recommendation the golfer didn't select), the resulting position
(post-rollout, from M5.4), and `course` geometry for the hole in play;
output = `GolfState`. It must reuse `gps.projection`'s tangent-plane
convention anchored at the shot origin (ADR 0002/0004 precedent) — no new
projection technique. This ADR does not design the mapping algorithm,
precedence rules for overlapping features, or the boundary-edge convention
— those are M5.5's job (issue #85), operating against this contract.

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
  ("caddai.golf_state", "caddai.gps"), plan_reference=...)`.
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
- A recommended keyword-scan test for `golf_state`'s own source, asserting
  it contains none of: `handicap`, `risk`, `score`, `whs`, `round_`,
  `player` (case-insensitive) — enforcing player-neutrality structurally,
  not just by field-list convention. This should be (a) a separate,
  `golf_state`-scoped identifier tuple, not merged into `simulation`'s
  existing `FORBIDDEN_POLICY_IDENTIFIERS` (the two subsystems' forbidden
  vocabularies are unrelated), and (b) implemented with word-boundary-aware
  matching (e.g. a regex using `\b`) rather than plain substring
  containment, since e.g. `"score"` is a substring of unrelated words such
  as `"underscore"` and a plain-substring check would false-positive.
- `strategy`'s boundary will later gain `caddai.golf_state` (M5.11, not
  this issue).

### Error/unsupported semantics (guidance, not binding on #85)

- Missing/degenerate course geometry input to the mapper: the mapper must
  raise a clear, typed error — never fabricate a "best guess" `GolfState`.
- An ordinary point outside every mapped feature: a valid, well-formed
  `GolfState` with `lie=UNKNOWN`, `is_penalty=False`, `holed=False` — not an
  error. `UNKNOWN` must never be treated as "safe"/fairway-like by
  downstream consumers — this is guidance for M5.9; `GolfState` cannot
  enforce a consumer's behaviour by itself. To make this more than prose
  discipline, M5.9's `E_base` implementation should use an exhaustive
  `match` statement (or equivalent) over `LieCategory` with **no
  catch-all/default branch** (no bare `case _:`), so mypy strict mode
  flags a missing case at type-check time if `LieCategory` ever gains a
  new member without a corresponding `E_base` branch — rather than relying
  on a silent fairway-like default for `UNKNOWN` (or any future member)
  going unnoticed.
- Ambiguous/overlapping feature classification precedence is M5.5's job
  (issue #85) — this ADR only requires that whatever `lie` M5.5 resolves to
  is a single, valid `LieCategory` member; `GolfState` has no opinion on the
  precedence rule itself.
- Malformed state (e.g. `holed=True` and `is_penalty=True` together,
  `holed=True` with `lie == UNKNOWN`) is rejected at construction via
  Pydantic validation — never silently coerced. `distance_to_hole_metres`
  no longer needs its own finiteness/non-negativity validation: as a
  `@computed_field` derived via `haversine_distance_metres`, it is always
  finite and `>= 0` given two valid `Coordinate`s, by construction of the
  haversine formula itself — there is no longer a separate malformed-float
  state to reject.
- `GolfState` no longer needs to verify `distance_to_hole_metres` against
  `position` (the drift risk this required in the previous draft is
  eliminated structurally — see the `hole_position`/`distance_to_hole_metres`
  field rationale above): the value is always recomputed from whichever
  `position`/`hole_position` are currently stored, so there is nothing
  separate for the mapper (M5.5) to keep in sync or for M5.5/M5.6's tests
  to guard against drift on.

### Batch/Monte Carlo considerations

`GolfState` is a small, flat value object (three `Coordinate`s, one
computed float, two `bool`s, one enum, one str, one int) — O(1), no I/O,
no geometry lookups, no provider calls per construction; safe to construct
thousands of times in a Monte Carlo candidate-evaluation loop. A future
batch/vectorised representation (e.g. a NumPy structure-of-arrays mirroring
these same fields) may be introduced later for vectorised `E_base`
evaluation without changing this per-sample semantic contract — not
designed now.

Two Monte Carlo samples with identical resulting golf facts (same
`position`, `hole_position`, `lie`, `is_penalty`, `holed`,
`course_reference`, `hole_number`) but different `selected_target` values
are unequal as `GolfState` values. This is intentional, not an oversight:
`selected_target` is preserved per the binding M5.0 research invariant (see
the `selected_target` field rationale above), not incidental data that
happens to vary. `strategy`'s own candidate aggregation (M5.11's
`CandidateValueDistribution`) must group samples by the caller's own
candidate/target identity externally, not rely on `GolfState` equality or
deduplication for that purpose.

### M6 portability

Every field is a plain scalar/categorical value (float, bool, str, int,
`StrEnum`, or a two-float `Coordinate`) — no Shapely geometry, no embedded
`Course`/`Hole`/`Feature` objects, no Python-specific behaviour baked into
the domain definition. It is directly representable in any future schema
(Protobuf, JSON Schema, a Rust struct) without redesign. No serialization
format, FFI mechanism, or schema-version field is chosen here — that is a
future, narrower decision if/when `GolfState` crosses a language/process
boundary (M6).

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
`is_penalty`/`holed` explicit, validated fields — rather than leaving them
derivable or optional — directly encodes the M5.0 research's domain
invariants (no silent `FAIRWAY` default, no proximity-based holed
inference, no overloaded lie-as-penalty-signal) as Pydantic-enforced
constraints instead of conventions a future contributor could accidentally
violate.

## Consequences

- Positive: `simulation`, a future expected-strokes/value module (M5.8),
  and `strategy` can all be implemented against one stable, tested contract
  — `GolfState`'s shape does not change as those consumers are built.
- Positive: the closed `LieCategory` enum and validated `is_penalty`/
  `holed` fields make impossible/ambiguous states (e.g. "holed and in a
  penalty area", "holed with an unknown lie") unrepresentable at
  construction, not just discouraged by convention. (A zero computed
  `distance_to_hole_metres` with `holed=False` remains representable and is
  intentionally not forbidden — see the `holed` field rationale above; this
  is a deliberate design choice, not a gap.)
- Positive: `GolfState`'s single outgoing dependency (`caddai.gps`) and
  flat, plain-scalar field shape make it trivially portable to a future M6
  language/schema boundary without redesign.
- Positive: module ownership (Strategy Engineer) matches the two
  subsystems most coupled to this type's lifecycle. `simulation` is the
  sole mapping owner by convention and by which module actually performs
  classification — like `ShotOutcome`/`WindComponents` today, `GolfState`
  is an ordinary public Pydantic model, so nothing structurally prevents
  another approved consumer (e.g. `strategy`, once M5.11 adds that
  dependency edge) from constructing one directly; this is a documented
  convention, not an enforced guarantee, consistent with how every other
  foundational value type in this codebase already works.
- Negative: `course_reference`/`hole_number` are explicitly provisional
  identifiers (`Course.name` has no real stable versioning yet); any future
  course-package identity scheme (M7) will need a follow-up migration of
  this field's semantics, not just its type. This is not only a future
  churn risk: today, neither `Course.name` nor `Hole.number` is validated
  as unique (`src/caddai/course/models.py` only enforces `min_length=1` on
  `Course.name` and `gt=0` on `Hole.number`), so the `(course_reference,
  hole_number)` pair is not a fully reliable identifier even now — a
  limitation a future M7 course-identity scheme must resolve, not
  something issue #82 can fix.
- Negative: `hole_position`/`distance_to_hole_metres` will initially
  resolve against green-centroid distance, not a true pin distance,
  because `Hole.pin_position` does not exist yet — a semantic
  approximation every M5.4/M5.5 consumer and any downstream
  expected-strokes evaluation must be aware of until pin data is added.
  This is purely a *semantic* limitation of what `hole_position` currently
  refers to, not a structural risk: because `distance_to_hole_metres` is a
  `@computed_field` derived from `position`/`hole_position` rather than a
  separately stored float, the earlier drift/verification risk between a
  stored distance and `position` is eliminated structurally, not merely
  mitigated.
- Negative: collapsing `WATER`/generic `PENALTY_AREA` into a single
  `LieCategory.PENALTY_AREA` value means V0's expected-strokes model cannot
  distinguish water-specific outcomes from other penalty areas without a
  future, non-breaking enum addition.

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
   with a derived, validated `is_penalty` convenience flag has no such gap.
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
   `hole_position: Coordinate` and deriving `distance_to_hole_metres` as a
   `@computed_field`. The stored-float approach left `GolfState` structurally
   unable to verify the distance against `position` (it holds no course
   geometry), an acknowledged drift risk between two values that must
   otherwise be kept in sync by convention. Deriving the distance from a
   stored `hole_position` instead makes drift definitionally impossible —
   there is only one source of truth (`position`/`hole_position`), not two
   independently-settable values — at the cost of one extra nested
   `Coordinate` field, which is O(1)/cheap per the `ShotOutcome`/
   M4-sampling Monte Carlo precedent (see the `hole_position` field
   rationale above). This is the option ultimately adopted.

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
The provisional nature of `course_reference` (`Course.name`) and
`hole_position` (green-centroid fallback, pending `Hole.pin_position`) are
recorded here precisely so a future M7 course-identity change and a future
pin-data addition each know exactly which field's *semantics* — not
necessarily its type — will need revisiting, without another
`GolfState`-shape ADR being required for that alone if the field type
itself is unchanged (`hole_position` remains a `Coordinate` whether it
holds a green-centroid or a true pin position; only what it *means*
changes). `GolfState`'s all-scalar/categorical field shape (no Shapely
geometry, no embedded provider objects) is deliberately chosen so a future
M6 language/process boundary can represent it in another schema (Protobuf,
JSON Schema, a Rust struct) without a redesign of the contract itself —
only a serialization mapping. A `@computed_field` (`distance_to_hole_metres`)
is a Pydantic/Python-specific convenience for consumers within this
codebase; a future M6 schema representation would recompute it from
`position`/`hole_position` on the far side of the boundary rather than
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
every domain invariant the spike's section D identified (explicit
lie/penalty/holed fields, no silent `FAIRWAY` default, `selected_target`
preserved exactly) as concrete Pydantic field/validator decisions. Section
D's distance-to-hole row favoured "storing it as a resolved scalar... [so]
every consumer [avoids] needing course-geometry access just to read a
distance" over deriving it on demand; this ADR honours that intent — no
consumer needs course-geometry access to read `distance_to_hole_metres` —
by storing `hole_position` (itself a resolved point, requiring the same
course-geometry access the spike anticipated) and deriving the distance
from it via a dependency-free, course-geometry-free `haversine_distance_metres`
call, rather than storing the distance as an independent scalar that could
drift from `position`/`hole_position`. It does not revisit or re-decide the
already-approved semantic architecture direction itself, and it leaves the
spike's separate, still-unresolved expected-strokes numeric-baseline
follow-on entirely untouched.
