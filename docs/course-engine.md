# Course engine

> Status: planned design for the `course`/`gps` subsystems (milestone M2).
> `src/caddai/gps/` is now implemented (M2.1, issue #3): `Coordinate`,
> `haversine_distance_metres`, and `initial_bearing_degrees`. `src/caddai/course/`
> is now implemented (M2.3, issue #5): `Course`, `Hole`, `Feature`, and
> `FeatureType` — point-position feature models only. GeoJSON parsing is
> now implemented (M2.4, issue #6): `src/caddai/course/geojson.py`'s
> `load_course`/`load_course_from_file` parse a `caddai`-specific GeoJSON
> `FeatureCollection` into `Course`/`Hole`/`Feature`. Shapely polygon
> geometry and hazard carry queries remain planned and are not yet
> implemented.

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
  Shapely (see [ADR 0002](adr/0002-gps-local-projection-without-shapely.md));
  geometric operations on course features (polygons, hazards, hole
  boundaries) will use Shapely starting at M2.3.
- Distance calculations: point-to-point, point-to-feature (e.g. distance to
  the front/centre/back of the green), and along-line-of-play distances.
- Hazard carry/lay-up distance queries (e.g. "distance to carry the
  fairway bunker on this line") as pure geometric queries — the strategy
  engine decides what to do with that information.

## Explicit non-goals

- No club selection, target selection, or risk assessment — that is the
  Strategy Engineer's responsibility.
- No dependency on `player`, `strategy`, `simulation`, `llm`, `api`, or `cli`.
- No live/remote course-data fetching in early milestones — local GeoJSON
  only. Any future third-party course-data integration requires an ADR.

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
- Each feature is a GeoJSON `Point`:
  `{"type": "Feature", "geometry": {"type": "Point", "coordinates":
  [<longitude>, <latitude>]}, "properties": {"hole": <int>, "feature_type":
  "<FeatureType value>"}}`. `feature_type` is one of `FeatureType`'s values
  (tee/fairway/green/bunker/water/out_of_bounds/landing_area).
- GeoJSON coordinate order is `[longitude, latitude]`; this is mapped
  explicitly to `Coordinate(latitude=coordinates[1],
  longitude=coordinates[0])` — do not assume `[latitude, longitude]`.
- Only `geometry.type == "Point"` is supported; polygon/boundary geometry
  is deferred (see the module docstring in `course/models.py`).
- The loader raises `ValueError` for structural problems (missing
  top-level `properties`, wrong `type` discriminators, unsupported
  `geometry.type`, a feature referencing a hole number absent from the
  top-level `holes` metadata) and `pydantic.ValidationError` for
  field-level problems (e.g. an unrecognized `feature_type`).
- See `tests/fixtures/sample_course.geojson` for a documented example
  fixture.

## Units

All geometry and distances are in metres internally, consistent with
`AGENTS.md` §5. GeoJSON's native lat/lon coordinates are converted to a
metre-based local projection for internal calculations by `gps.projection`
(see [ADR 0002](adr/0002-gps-local-projection-without-shapely.md)).
