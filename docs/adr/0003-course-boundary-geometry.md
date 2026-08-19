# 0003. Course boundary geometry

## Status

Accepted

## Context

`src/caddai/course/models.py`'s `Feature` (M2.3, issue #5) and
`src/caddai/course/geojson.py`'s loader (M2.4, issue #6) represented every
course feature as a single point (`position`). M2.5 (issue #7) needs real
boundary geometry to query against — green front/centre/back distances and
hazard-carry-along-line-of-play both require a polygon, not just a point.
GitHub issue #22 ("M2.4.5 — Polygon/boundary course geometry and GeoJSON
Polygon support") scopes the minimum boundary representation needed to
unblock that work.

This decision has two independent ADR triggers: (a) a public API/contract
change (`Feature`'s schema, and `load_course`'s accepted GeoJSON geometry
types and error contract), and (b) the first real activation of Shapely,
which [ADR 0002](0002-gps-local-projection-without-shapely.md) explicitly
deferred to "when genuinely needed" — polygon construction and validity/
centroid queries are exactly that need.

## Decision

1. **`Feature.boundary` shape and `position` as centroid.** `Feature` gains
   `boundary: tuple[Coordinate, ...] | None = Field(default=None,
   min_length=3)` — an exterior polygon ring stored as distinct lat/lon
   vertices, with no duplicated closing vertex. `position` remains a
   required `Coordinate` on every `Feature` (point-only features are
   unaffected). When `boundary` is present, `position` is the polygon's
   centroid, computed by a new module-level `polygon_centroid` helper. A
   polygon centroid is a convenience representative point only: it is
   **not** guaranteed to lie inside a concave/non-convex polygon, and it is
   not a substitute for front/centre/back distance semantics — that
   remains M2.5's job.

2. **Enforced `position`/`boundary` consistency.** This is not left as a
   documented convention: `Feature` has a Pydantic `model_validator(mode=
   "after")` that, whenever `boundary` is not `None`, recomputes the
   expected centroid via `polygon_centroid` and rejects (`ValueError`, which
   Pydantic converts to `ValidationError`) any `Feature` whose `position`
   differs from it by more than 0.01 metres (1 cm) in local-metre terms.
   This tolerance matches ADR 0002's stated round-trip accuracy for
   `gps.projection`. The validator runs regardless of how the `Feature` is
   constructed — including direct construction, not only via the GeoJSON
   loader — so an inconsistent `Feature` always fails loudly.

3. **Single exterior ring only; no interior rings/holes.** This issue
   accepts exactly one ring per `Feature.boundary`. Interior rings (holes in
   a polygon) are an explicit, documented non-goal, not a silent gap:
   `caddai.course.geojson._parse_feature` raises a distinct `ValueError`
   when a GeoJSON `Polygon`'s `coordinates` contains zero or more than one
   ring.

4. **Ring validation contract, split by concern.** GeoJSON-structural
   concerns are validated in `geojson.py` and raise plain `ValueError`:
   ring closure (first and last positions must be equal) and minimum
   vertex count (≥4 positions, i.e. ≥3 distinct vertices plus the closing
   duplicate). Domain-model concerns are validated in `models.py`'s
   `Feature` validator and raise `ValidationError`: geometric validity via
   `shapely.geometry.Polygon.is_valid` (rejects self-intersecting/bowtie
   rings) and non-degeneracy via `polygon.area > 0` (rejects collinear/
   zero-area rings), plus the `position`/centroid consistency invariant
   from point 2. `geojson.py` does not duplicate the geometric-validity
   check — it constructs the `Feature` and lets the model's own validator
   catch it.

5. **Transient, per-feature, ad hoc local-projection origin.** Both
   `polygon_centroid` and `Feature`'s validator project `boundary`'s
   vertices to local metres via `gps.projection.to_local`/`to_coordinate`,
   using the ring's own first vertex (`boundary[0]`) as the projection
   origin, purely to construct a `shapely.geometry.Polygon` and compute its
   centroid/validity. This local-metre representation is not persisted or
   exposed anywhere — it exists only for the duration of the computation.
   A shared course-/hole-level local-projection origin (needed for M2.5's
   cross-feature distance queries, e.g. front/centre/back or hazard-carry
   lines spanning multiple features) is an open question, intentionally
   deferred to M2.5, which is better placed to know what shared frame those
   queries need. This is a deliberate deferral, not an oversight.

6. **Relationship to ADR 0002.** This decision activates, but does not
   change, ADR 0002's original point-to-point projection decision. `gps.
   projection.to_local`/`to_coordinate` continue to be plain trigonometry,
   unchanged; ADR 0002's scoping of "Shapely is reserved for actual
   geometry operations" is now realized here for the first time. ADR 0002
   is not superseded.

## Consequences

- Positive: M2.5 (green front/centre/back, hazard-carry queries) now has
  real polygon geometry to query against, without a discriminated point/
  polygon union that would force type-narrowing on every existing
  `Feature` consumer.
- Positive: an inconsistent `Feature` (mismatched `position`/`boundary`, a
  self-intersecting ring, a degenerate ring) fails at construction time,
  everywhere, not only through the GeoJSON loader.
- Positive: the GeoJSON-structural vs. domain-model validation split keeps
  `ValueError`/`ValidationError` usage consistent with the existing
  precedent in `geojson.py` and `models.py`.
- Negative: `Feature.position` is only a convenience centroid when
  `boundary` is present; consumers must not assume it lies inside a
  concave polygon or treat it as a green's "centre" in the golf sense —
  this must be kept in mind until M2.5 introduces real front/centre/back
  semantics.
- Negative: interior rings (holes) are unsupported; any future course
  feature genuinely requiring a hole-in-polygon representation (e.g. a
  green with an internal bunker cut into a single feature) will need a
  follow-up issue and likely a new ADR.
- Negative: the ad hoc per-feature local-projection origin means repeated
  projections are done independently per feature; this is intentionally
  not optimized or unified yet, deferred to M2.5.

## Alternatives considered

- **Discriminated point/polygon union type** (e.g. `Feature` as a tagged
  union of a point variant and a polygon variant): rejected — higher churn
  for existing point-only consumers, which would all need to type-narrow;
  the optional `boundary` field achieves the same representational goal
  with lower disruption.
- **Document `position`/`boundary` consistency as a convention only, not
  enforce it**: rejected per Architect review — silent inconsistency
  between `position` and `boundary` would be a latent bug source for M2.5's
  distance queries; enforcing it in a `model_validator` costs little and
  fails loudly at the point of construction.
- **Support interior rings (holes) now**: rejected as out of scope for this
  issue — no current feature requires it, and it adds meaningful geometric
  complexity (multi-ring validity, containment checks) without a concrete
  use case driving it.
- **Introduce a durable shared course-/hole-level local-projection origin
  now**: rejected — this issue only needs a transient origin for
  single-polygon validity/centroid checks; a shared origin's requirements
  are best determined by M2.5's actual cross-feature distance queries,
  not guessed at here.
