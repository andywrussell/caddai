# 0002. GPS local projection without Shapely

## Status

Accepted

## Context

`docs/course-engine.md` anticipated using Shapely for all geometric
operations in the `gps`/`course` subsystems, including conversion between
geographic coordinates and course-local planar coordinates. `src/caddai/gps/projection.py`
implements that specific conversion — `to_local` and `to_coordinate` — as a
small-area equirectangular/tangent-plane affine transform between a
`Coordinate` (lat/lon) and a `LocalPoint` (x/y metres).

This operation is a closed-form, two-point trigonometric transform: it
converts a single point to and from local metres relative to a fixed origin.
It performs no polygon construction, no geometric predicate (contains,
intersects, buffer), and no operation that benefits from a geometry engine.
Requiring Shapely here would mean wrapping plain coordinates in
`shapely.Point` objects purely to satisfy an unconditional "use Shapely"
instruction, without ever calling a Shapely geometric operation on them —
an unused-capability dependency for this function specifically.

`docs/backlog.md` had flagged "decide the coordinate-projection approach for
lat/lon → local metres conversion" as a candidate ADR item; this decision
resolves it.

## Decision

`gps.projection`'s point-to-point affine transform (`to_local`,
`to_coordinate`) uses plain trigonometry (Python's `math` module) rather
than Shapely. Shapely is reserved for actual geometry operations —
polygons, hazards, hole boundaries, and other geometric predicates on
course features — starting at milestone M2.3, where it is genuinely needed.

This does not change the Course Engineer's use of Shapely for course
geometry generally; it scopes the "use Shapely for geometric operations"
guidance to operations that actually manipulate or query geometry, not
single-point coordinate arithmetic.

## Consequences

- Positive: `gps.projection` has no dependency on Shapely, keeping the
  point-to-point transform simple, easy to read, and easy to unit test as
  closed-form algebra.
- Positive: clarifies for future work that Shapely's role starts where
  actual geometric operations (polygons, hazards, containment/intersection
  queries) begin, not at the coordinate-conversion boundary.
- Negative: introduces a documented exception to the otherwise-general
  "use Shapely for geometric operations" instruction, which future
  contributors must be aware of when reading `docs/course-engine.md` and
  `.github/agents/course-engineer.agent.md`.

## Alternatives considered

- **Wrap coordinates in `shapely.Point` purely for API consistency**:
  rejected — no geometric operation (predicate, transform, or query) is
  performed on the points; this would add a dependency without using any
  of its capability.
- **Use a general geodesic projection library** (e.g. a full geodesy
  package supporting ellipsoidal projections): rejected as out of scope —
  this transform is an intentionally small-area (≈2 km radius) tangent-plane
  approximation, which plain trigonometry already provides at the required
  accuracy (within 1 cm on round-trip).
