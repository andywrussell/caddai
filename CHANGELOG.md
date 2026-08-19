# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/) once a
first public API is published.

## [Unreleased]

### Added

- Course/hole/feature domain models (M2.3, issue #5): a new `caddai.course`
  subsystem (`__init__.py`, `models.py`) with `FeatureType` (a `StrEnum` of
  `TEE`, `FAIRWAY`, `GREEN`, `BUNKER`, `WATER`, `OUT_OF_BOUNDS`,
  `LANDING_AREA`), `Feature` (a point-position course feature built on
  `caddai.gps.models.Coordinate`), `Hole` (`number`/`par`/ordered
  `features`), and `Course` (`name`/ordered `holes`) — all Pydantic v2
  models with full strict type hints. Feature geometry is point-based only
  for now; polygon/boundary geometry backed by Shapely is deferred per
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

- Migrated CI/collaboration infrastructure from GitLab to GitHub: removed
  `.gitlab-ci.yml`; updated `AGENTS.md`, `README.md`,
  `docs/development-workflow.md`, `.github/copilot-instructions.md`, and the
  Orchestrator/Integrator agent definitions to reference GitHub Actions CI
  and GitHub pull requests as the standard mechanisms.
