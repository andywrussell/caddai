# 0004. Distance query local frame

## Status

Accepted

## Context

M2.5 (issue #7) needs point-to-feature distance queries against the M2.4.5
boundary geometry: green front/centre/back distances, and hazard-carry
distance along a line of play. Both require projecting a player position, an
aim point, and a feature's `boundary` vertices together into one planar
local-metre frame before doing any line/polygon geometry, since geographic
(lat/lon) coordinates cannot be used directly for Euclidean distance or
Shapely line/polygon intersection.

[ADR 0003](0003-course-boundary-geometry.md) already introduced a local
projection for a feature's own boundary, but explicitly deferred this exact
decision: "a shared course-/hole-level local-projection origin... is an open
question, intentionally deferred to M2.5, which is better placed to know
what shared frame those queries need." This ADR resolves that deferral.

## Decision

1. **No shared/durable origin; fresh per-query projection using
   `player_position`.** Every function in `src/caddai/course/distance.py`
   projects `player_position`, the aim point, and every relevant `boundary`
   vertex together, freshly, for that one call, via
   `caddai.gps.projection.to_local`, using `player_position` as the local
   frame's origin. No origin is computed once and reused across calls, and
   no canonical hole- or course-level origin is introduced.
   `player_position` is the natural choice: every value this module reports
   is a distance *from the player*, so anchoring the frame there matches
   the intuition directly, and avoids introducing state ADR 0003 explicitly
   declined to add.

2. **Invariant: never mixed with `_local_polygon`'s per-feature origin.**
   `caddai.course.models._local_polygon`/`polygon_centroid` project a
   feature's own `boundary` using that boundary's first vertex
   (`boundary[0]`) as an ad hoc, transient origin, solely to compute that
   one feature's centroid/validity. This is a *different, unrelated, local
   frame* from the one this module uses. `distance.py` never reads, reuses,
   or mixes local coordinates computed by `_local_polygon`/
   `polygon_centroid` with its own `player_position`-anchored projections.
   Every distance query in this module re-projects `boundary` itself, fresh,
   from `player_position`. This is enforced structurally (each query
   function calls `to_local` directly, not the `course/models.py` helpers)
   and is covered by a regression test
   (`test_green_front_centre_back_distances_is_independent_of_boundary_vertex_rotation`
   in `tests/test_course_distance.py`) that would fail if a
   `boundary[0]`-anchored frame were used instead.

3. **"Centre" is the green polygon's centroid, not a pin.** `green_front_
   centre_back_distances`'s aim point is `green.position` -- the green
   polygon's own centroid, per ADR 0003 -- not a pin/flag location, since no
   `Hole.pin_position` concept exists yet. This is a known simplification,
   flagged as a likely follow-up once pin data is available.

4. **Signed distance via vector projection; formal front/back/carry
   definitions.** Given a `player_position`, an `aim_point`, and a feature's
   `boundary`, the unit direction vector $\hat{u}$ points from the local
   player point $(0, 0)$ toward the local aim point. For any point $p$ with
   local offset $\vec{p}$ from the player, its *signed distance* is
   $\vec{p} \cdot \hat{u}$: positive ahead of the player in the aim
   direction, negative behind. The line through the player and aim point is
   intersected with the boundary polygon's exterior; every resulting
   crossing point's signed distance is computed this way.
   - **Front** = the minimum (nearest) signed distance among the green
     boundary's crossings.
   - **Back** = the maximum (farthest) signed distance among the green
     boundary's crossings.
   - **Centre** = the signed distance to the aim point itself (the green's
     centroid), along the same direction -- equal to the plain player-to-
     centroid distance, since it is the aim direction itself.
   - **Carry** (hazard) = the maximum (farthest) signed distance among the
     hazard boundary's crossings -- the point beyond which the hazard has
     been fully cleared.

5. **Concave-polygon non-goal; degenerate crossing-count behaviour.**
   Nearest/farthest crossing is not a complete answer for a concave
   (non-convex) boundary ring, which can produce more than two crossings;
   full concave multi-crossing modelling is an explicit non-goal. Exact
   behaviour by crossing count:
   - **0 crossings, hazard query**: normal/expected -- `hazard_carry_
     distance` returns `None` ("not in play" for this line).
   - **0 crossings, green query**: should be geometrically impossible (the
     aim point is the green's own interior centroid) -- raised as an
     internal `ValueError`, defensive only.
   - **Exactly 1 crossing** (a tangent line): both front/back, or the single
     carry value, equal that one signed distance.
   - **>2 crossings** (possible only for a concave ring): front/carry is the
     minimum, back/carry is the maximum, among *all* crossings found -- an
     explicit, documented scope limitation, not a silently wrong answer.
   `green.boundary`/`hazard.boundary` being `None`, and
   `player_position == aim_point` (an undefined direction), both raise
   `ValueError` in every function.

## Consequences

- Positive: distance queries are correct regardless of which vertex happens
  to be `boundary[0]` in a stored `Feature.boundary` tuple -- the frame used
  depends only on `player_position` and the query's own inputs, never on
  incidental storage order. Verified by a dedicated regression test (see
  point 2 above).
- Positive: no new durable state, no cache invalidation concern, no
  course-/hole-level origin lifecycle to manage.
- Negative: each query re-projects every participating coordinate from
  scratch; for a query pattern that repeatedly evaluates many features from
  the same player position, this repeats work that a shared origin could
  avoid. This is intentionally not optimized yet, consistent with ADR
  0003's own precedent of leaving this as a deferred concern until a real
  performance need is demonstrated.
- Negative: ADR 0002's small-area accuracy caveat still applies -- this
  projection is a tangent-plane approximation valid only within roughly a
  2 km radius of `player_position`; a query where the aim point or a
  feature's boundary lies meaningfully beyond that radius is out of this
  module's validated accuracy envelope (not expected in a single golf shot's
  distance queries, but worth remembering if this module is ever reused for
  a coarser-grained query).
- Negative: the nearest/farthest-crossing simplification is only fully
  correct for a convex boundary; a concave green or bunker ring can yield a
  front/back/carry value that does not match what a human would consider
  the "true" front/back/carry edge. Not currently a problem for this
  project's course fixtures (verified convex by a dedicated fixture sanity
  test), but a future concave-boundary feature would need a follow-up
  design.

## Alternatives considered

- **A canonical, durable hole- or course-level local-projection origin**
  (computed once, stored, reused by every query against that hole/course):
  rejected -- this is exactly the option ADR 0003 flagged and deferred to
  this decision. It would introduce new durable state (an origin's
  lifecycle, invalidation if course data changes) for a benefit (avoiding
  repeated projection) that is not a demonstrated bottleneck; every query
  result would also become dependent on an origin choice unrelated to the
  actual query (the player's position), which is a worse fit for "distance
  from here" semantics than anchoring on the player directly.
- **The aim point as the local-frame origin** (instead of
  `player_position`): rejected -- the player's position is the natural
  frame for a "distance from here" query; anchoring on the aim point instead
  would make the signed-distance-to-self trivially and confusingly always
  zero for the primary point of interest, and offers no accuracy or
  simplicity benefit over anchoring on the player.
- **Reusing `_local_polygon`'s `boundary[0]`-anchored origin** for this
  module's queries: rejected, and structurally prevented -- see point 2.
  This origin is unrelated to a player's position or an aim direction; using
  it here would make results depend on which vertex happens to be stored
  first in a `Feature.boundary` tuple, a latent correctness bug this ADR's
  invariant is designed to rule out entirely, not just avoid by convention.
