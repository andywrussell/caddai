# Course engine

> Status: planned design for the `course`/`gps` subsystems (milestone M2).
> `src/caddai/gps/` is now implemented (M2.1, issue #3): `Coordinate`,
> `haversine_distance_metres`, and `initial_bearing_degrees`. `src/caddai/course/`
> is now implemented (M2.3, issue #5): `Course`, `Hole`, `Feature`, and
> `FeatureType` — point-position feature models only. GeoJSON parsing is
> now implemented (M2.4, issue #6): `src/caddai/course/geojson.py`'s
> `load_course`/`load_course_from_file` parse a `caddai`-specific GeoJSON
> `FeatureCollection` into `Course`/`Hole`/`Feature`. Polygon/boundary
> geometry is now implemented (M2.4.5, issue #22): `Feature.boundary`
> (single exterior ring only, no interior rings/holes) and
> `polygon_centroid`, backed by Shapely — see
> [ADR 0003](adr/0003-course-boundary-geometry.md). Distance-to-feature
> queries are now implemented (M2.5, issue #7):
> `src/caddai/course/distance.py`'s `green_front_centre_back_distances` and
> `hazard_carry_distance` — see [ADR 0004](adr/0004-distance-query-local-frame.md).

## Purpose

Represent golf course geometry and provide GPS/distance calculations needed
by the strategy engine, without making any strategic decisions itself.

## Owner

Course Engineer (see `.github/agents/course-engineer.agent.md`).

## Planned responsibilities

- Parse and represent course geometry from local GeoJSON fixtures: holes,
  tees, fairways, greens, bunkers, water, out-of-bounds, and landing areas.
- Represent a hole as an ordered composition of these features plus par.
- Coordinate handling: conversion between geographic coordinates
  (latitude/longitude) and course-local planar coordinates (metres).
  Point-to-point conversion (`gps.projection`) is plain trigonometry, not
  Shapely (see [ADR 0002](adr/0002-gps-local-projection-without-shapely.md)).
  Polygon geometry on course features (a `Feature`'s optional `boundary`,
  single exterior ring only) uses Shapely, activated in M2.4.5 (issue #22,
  see [ADR 0003](adr/0003-course-boundary-geometry.md)).
- Distance calculations: point-to-point (`gps.distance`) and
  point-to-feature/along-line-of-play distances
  (`caddai.course.distance`, M2.5, issue #7) are implemented — see
  "Distance-to-feature queries" below.
- Hazard carry/lay-up distance queries (e.g. "distance to carry the
  fairway bunker on this line") as pure geometric queries are implemented
  (`caddai.course.distance.hazard_carry_distance`, M2.5, issue #7) — the
  strategy engine decides what to do with that information.

## Explicit non-goals

- No club selection, target selection, or risk assessment — that is the
  Strategy Engineer's responsibility.
- No dependency on `player`, `strategy`, `simulation`, `llm`, `api`, or `cli`.
- No live/remote course-data fetching in early milestones — local GeoJSON
  only. Any future third-party course-data integration requires an ADR, and
  must fit a download/cache-before-a-round model: reading already-cached
  course geometry is active-round core functionality (`AGENTS.md` §2.2) and
  must not depend on a live network call during a round — see
  [ADR 0005](adr/0005-offline-first-active-round-architecture.md).

## Data format

Course data is represented as a GeoJSON `FeatureCollection` with a
`caddai`-specific `properties` schema, parsed by
`src/caddai/course/geojson.py`'s `load_course`/`load_course_from_file`:

- Top-level object:
  `{"type": "FeatureCollection", "properties": {"name": <course name>,
  "holes": [{"number": <int>, "par": <int>}, ...]}, "features": [...]}`.
  `par` lives once per hole in this top-level metadata (single source of
  truth), not repeated across every point feature on that hole. `name` has
  no natural per-feature home, so it lives at the top-level `properties`
  only.
- Each feature is a GeoJSON `Point` or `Polygon`:
  `{"type": "Feature", "geometry": {"type": "Point", "coordinates":
  [<longitude>, <latitude>]}, "properties": {"hole": <int>, "feature_type":
  "<FeatureType value>"}}`, or `{"type": "Feature", "geometry":
  {"type": "Polygon", "coordinates": [[[<longitude>, <latitude>], ...]]},
  "properties": {...}}`. `feature_type` is one of `FeatureType`'s values
  (tee/fairway/green/bunker/water/out_of_bounds/landing_area) for either
  geometry type — no `FeatureType` is restricted to a particular geometry.
- GeoJSON coordinate order is `[longitude, latitude]`; this is mapped
  explicitly to `Coordinate(latitude=coordinates[1],
  longitude=coordinates[0])` — do not assume `[latitude, longitude]`.
- `geometry.type` may be `"Point"` or `"Polygon"` (issue #22). A `Polygon`
  must have exactly one ring (interior rings/holes are rejected), the ring
  must be closed (first and last positions equal) and have at least 4
  positions, and the parsed `Feature.boundary` drops the duplicated
  closing vertex. `Feature.position` is then the polygon's centroid (via
  `polygon_centroid`) — see
  [ADR 0003](adr/0003-course-boundary-geometry.md) for the full scope and
  the `position`/`boundary` consistency invariant enforced by `Feature`
  itself. Any other `geometry.type` is rejected.
- The loader raises `ValueError` for structural problems (missing
  top-level `properties`, wrong `type` discriminators, unsupported
  `geometry.type`, a malformed Polygon ring, a feature referencing a hole
  number absent from the top-level `holes` metadata) and
  `pydantic.ValidationError` for field-level/domain-model problems (e.g. an
  unrecognized `feature_type`, or a geometrically invalid/inconsistent
  `boundary`).
- See `tests/fixtures/sample_course.geojson` for a documented example
  fixture, including a green and a bunker polygon feature.

## Distance-to-feature queries

`src/caddai/course/distance.py` (M2.5, issue #7) implements pure geometric
point-to-feature distance queries against `Feature.boundary` geometry — no
strategic decision-making, which remains the Strategy Engineer's job (M5+).
See [ADR 0004](adr/0004-distance-query-local-frame.md) for the full design.

- `GreenDistances(front_metres, centre_metres, back_metres)` and
  `green_front_centre_back_distances(player_position, green)` return signed
  distances, in metres, from `player_position` to a green's front/centre/
  back, measured along the player-to-green-centroid line of play. A
  negative value means the player has already passed that point.
- `hazard_carry_distance(player_position, aim_point, hazard)` returns the
  signed carry distance, in metres, to clear a hazard along the
  `player_position`-to-`aim_point` line of play, or `None` if that line
  never crosses the hazard at all.
- **Frame-consistency invariant**: every query re-projects
  `player_position` (the shared local-metre-frame origin), the aim point,
  and every `boundary` vertex together, fresh, per call, via
  `caddai.gps.projection.to_local`. This is independent of, and never mixed
  with, `caddai.course.models._local_polygon`'s unrelated per-feature
  origin (`boundary[0]`), which exists only for a feature's own centroid/
  validity computation. See ADR 0004 for why.
- **Scope limits**: see [Known limitations](#known-limitations) below.

## Known limitations

- No pin/flag position concept — `Hole.pin_position` doesn't exist;
  "centre" (in `green_front_centre_back_distances`) means the green
  polygon's own centroid (per [ADR 0003](adr/0003-course-boundary-geometry.md)),
  not a golf pin/flag location.
- The nearest/farthest-crossing simplification used for front/back/carry
  distances (see [ADR 0004](adr/0004-distance-query-local-frame.md)) is
  only a complete answer for a convex (simple) polygon boundary; a concave
  ring can produce more than two line-of-play crossings, which is an
  explicit, documented non-goal rather than a silently wrong answer.
- No interior rings (holes) are supported in a `Feature.boundary` polygon
  ([ADR 0003](adr/0003-course-boundary-geometry.md) explicit non-goal).

## Units

All geometry and distances are in metres internally, consistent with
`AGENTS.md` §5. GeoJSON's native lat/lon coordinates are converted to a
metre-based local projection for internal calculations by `gps.projection`
(see [ADR 0002](adr/0002-gps-local-projection-without-shapely.md)).
