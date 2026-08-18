# Course engine

> Status: planned design for the `course`/`gps` subsystems (milestone M2).
> `src/caddai/gps/` is now implemented (M2.1, issue #3): `Coordinate`,
> `haversine_distance_metres`, and `initial_bearing_degrees`. `src/caddai/course/`
> remains planned and does not exist in the repository yet.

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
  (latitude/longitude) and course-local planar coordinates (metres), using
  Shapely for geometric operations.
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

## Data format (planned)

Course data is represented as GeoJSON `FeatureCollection`s with a
`caddai`-specific `properties` schema (feature type: tee/fairway/green/
bunker/water/OB/landing-area; hole number; par). The exact schema will be
defined and versioned when M2 begins.

## Units

All geometry and distances are in metres internally, consistent with
`AGENTS.md` §5. GeoJSON's native lat/lon coordinates are converted to a
metre-based local projection for internal calculations; the conversion
approach is an implementation detail of `gps`, documented here once decided.
