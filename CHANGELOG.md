# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/) once a
first public API is published.

## [Unreleased]

### Added

- Point-to-feature distance queries (M2.5, issue #7):
  `caddai.course.distance` adds `GreenDistances`,
  `green_front_centre_back_distances`, and `hazard_carry_distance` — signed
  distance queries (green front/centre/back, and hazard carry distance
  along a line of play) computed by projecting the player position, the
  aim point, and the feature's `boundary` into one common local-metre
  frame, freshly, per call, via `caddai.gps.projection.to_local`, anchored
  at `player_position` — never mixed with `caddai.course.models
  ._local_polygon`'s per-feature, ad hoc origin from M2.4.5. Degenerate
  cases are explicit: a player already past the feature yields negative
  signed distances; a player standing on the boundary yields a near-zero
  (not exact-zero) distance; a line of play that misses a hazard entirely
  returns `None`; a tangent line returns a single value for both
  front/back or the carry distance. The nearest/farthest-crossing
  simplification used for front/back/carry is only a complete answer for a
  convex boundary — a concave ring can yield more than two crossings,
  which is a documented scope limitation, not a silently wrong answer.
  New [ADR 0004](docs/adr/0004-distance-query-local-frame.md) records the
  local-frame decision — it extends, and does not supersede, ADR 0002/
  0003. `docs/course-engine.md` is updated accordingly.
- Polygon/boundary course geometry and GeoJSON `Polygon` support (M2.4.5,
  issue #22): `caddai.course.models.Feature` gains an optional `boundary:
  tuple[Coordinate, ...] | None` field (a single exterior polygon ring,
  e.g. for a green or a bunker), with `position` enforced as its centroid
  via a new `Feature` `model_validator` (rejects a mismatched `position`,
  or a self-intersecting/degenerate ring, with a 0.01 m tolerance matching
  ADR 0002's stated round-trip accuracy) regardless of how the `Feature`
  is constructed. A new `polygon_centroid` helper computes a boundary
  ring's centroid via a transient, per-feature, ad hoc local-projection
  origin (the ring's own first vertex; a durable shared course-/hole-level
  origin is deferred to M2.5). `caddai.course.geojson.load_course` now
  also accepts `geometry.type == "Polygon"`: a single exterior ring only
  (interior rings/holes are explicitly rejected), with ring-closure and
  minimum-vertex-count checked as GeoJSON-structural concerns
  (`ValueError`), and geometric validity/degeneracy and the
  `position`/`boundary` centroid invariant checked as domain-model
  concerns (`pydantic.ValidationError`) by `Feature` itself.
  `tests/fixtures/sample_course.geojson` gained a green polygon on hole 1
  and a bunker polygon on hole 2. New [ADR 0003](docs/adr/0003-course-boundary-geometry.md)
  records this decision — it extends, and does not supersede, ADR 0002,
  and is the first real activation of Shapely. `docs/course-engine.md` is
  updated accordingly. This unblocks M2.5 (issue #7)'s distance-to-feature
  queries.
- Local GeoJSON course fixture parsing (M2.4, issue #6): `caddai.course.geojson`'s
  `load_course` (parses an already-decoded `FeatureCollection` dict) and
  `load_course_from_file` (reads and JSON-decodes a fixture file, then
  delegates to `load_course`), plus `tests/fixtures/sample_course.geojson`,
  a documented example fixture. Parses a `caddai`-specific GeoJSON
  `properties` schema (top-level `name`/`holes` metadata carrying `number`
  and `par` once per hole, per-feature `hole`/`feature_type` properties)
  into `Course`/`Hole`/`Feature` domain models. `geometry.type == "Point"`
  was the only supported geometry at the time; `"Polygon"` support was
  added later (M2.4.5, issue #22). Raises `ValueError` for structural
  problems (missing top-level `properties`, wrong `type` discriminators,
  unsupported `geometry.type`, duplicate hole numbers in the top-level
  `holes` metadata, or a feature referencing an undeclared hole number)
  and `pydantic.ValidationError` for field-level problems (e.g. an
  unrecognized `feature_type`). `tests/test_architecture_boundaries.py`'s
  `course` boundary now also covers `geojson.py`, and `docs/course-engine.md`
  documents the schema.
- Course/hole/feature domain models (M2.3, issue #5): a new `caddai.course`
  subsystem (`__init__.py`, `models.py`) with `FeatureType` (a `StrEnum` of
  `TEE`, `FAIRWAY`, `GREEN`, `BUNKER`, `WATER`, `OUT_OF_BOUNDS`,
  `LANDING_AREA`), `Feature` (a point-position course feature built on
  `caddai.gps.models.Coordinate`), `Hole` (`number`/`par`/ordered
  `features`), and `Course` (`name`/ordered `holes`) — all Pydantic v2
  models with full strict type hints. Feature geometry was point-based
  only at the time; polygon/boundary geometry backed by Shapely was added
  later (M2.4.5, issue #22) per
  [ADR 0002](docs/adr/0002-gps-local-projection-without-shapely.md).
  `course` depends only on `caddai.gps` (`Coordinate`), consistent with the
  `COURSE --> GPS` edge in `docs/architecture.md` and `AGENTS.md` §4's Course
  Engineer ownership of both subsystems; `AGENTS.md` §3's `course`
  dependency cell was corrected to say `gps` explicitly.
  `tests/test_architecture_boundaries.py` gained a `course` entry
  restricting it to `caddai.course`/`caddai.gps` imports only.
- Course-local planar coordinate projection (M2.2, issue #4):
  `caddai.gps.projection` (`LocalPoint`, `to_local`, `to_coordinate`), a
  small-area equirectangular/tangent-plane affine transform between a
  `Coordinate` (lat/lon) and course-local metres relative to a fixed origin.
  Uses plain trigonometry rather than Shapely — see
  [ADR 0002](docs/adr/0002-gps-local-projection-without-shapely.md), which
  also updates `docs/course-engine.md`, `docs/backlog.md`, and
  `.github/agents/course-engineer.agent.md` accordingly.
  `tests/test_architecture_boundaries.py` continues to confirm `gps` has
  zero dependencies on other `caddai.*` subsystems.
- GPS coordinate and great-circle distance/bearing primitives (M2.1, issue
  #3): `caddai.gps` (`Coordinate`, `haversine_distance_metres`,
  `initial_bearing_degrees`). `gps` is a leaf domain module with zero
  dependencies on other `caddai.*` subsystems, consistent with `AGENTS.md`
  §3/§4. `tests/test_architecture_boundaries.py` was generalized to cover
  `gps` alongside `strategy`.
- Developer recommendation demo (M1.1, issue #16):
  `src/caddai/strategy/demo.py`, runnable via
  `uv run python -m caddai.strategy.demo`, a thin presentation wrapper that
  runs the real `recommend_club()` on a fixed, deterministic scenario and
  prints a human-readable recommendation. Adds no new business logic.
- Core domain model and deterministic recommendation vertical slice (M1):
  `caddai.player` (`Club`, `Player`) and `caddai.strategy` (`WindDirection`,
  `Wind`, `LieType`, `RecommendationRequest`, `RecommendationResult`,
  `recommend_club`). The recommendation logic is an intentionally primitive
  placeholder — closest-expected-carry club selection with arbitrary
  wind/lie adjustment constants — proving the end-to-end architecture and
  dependency direction, not a real golf strategy model. See
  `docs/plans/m1-core-domain-vertical-slice.plan.md`.
- Repository bootstrap (M0): project structure, documentation set, multi-agent
  development team (`.github/agents/`), quality-gate tooling, `uv`-managed
  `pyproject.toml`, and the minimal `caddai` package skeleton.
- GitHub Actions CI workflow (`.github/workflows/ci.yml`) running the quality
  gate on pull requests targeting `main` and on pushes to `main`.
- `.github/PULL_REQUEST_TEMPLATE.md` and a feature/milestone request issue
  template (`.github/ISSUE_TEMPLATE/feature_request.md`).

### Changed

- Course-engine documentation consolidation for the now-complete M2
  milestone (M2.6, issue #8): `docs/roadmap.md`'s M2 entry is marked
  `*(complete)*` with a summary linking to `docs/course-engine.md` and
  ADRs 0002–0004; `docs/architecture.md`'s status banner is corrected for
  both the M2 staleness (it claimed `course`/`gps` weren't implemented)
  and the pre-existing M1 staleness (it claimed only the bootstrap
  package existed); `docs/backlog.md`'s completed GeoJSON-schema
  candidate item is removed and two new M2.5 test-coverage-gap follow-up
  items are added (line-of-play/polygon-edge overlap, and the `1e-6` m
  Shapely precision-snap boundary); `docs/course-engine.md` gains a new
  `## Known limitations` section consolidating the three permanent M2.5
  design limitations (no pin/flag position, convex/simple-polygon
  assumption with no concave multi-crossing support, no interior
  rings/holes), with redundant inline restatements trimmed to a pointer.
  Documentation-only — no new production code, tests, or ADR. This
  completes milestone M2 (M2.1–M2.5, M2.4.5, M2.6 all done).
- Migrated CI/collaboration infrastructure from GitLab to GitHub: removed
  `.gitlab-ci.yml`; updated `AGENTS.md`, `README.md`,
  `docs/development-workflow.md`, `.github/copilot-instructions.md`, and the
  Orchestrator/Integrator agent definitions to reference GitHub Actions CI
  and GitHub pull requests as the standard mechanisms.
