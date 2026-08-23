# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/) once a
first public API is published.

## [Unreleased]

### Changed

- Redefined roadmap milestone M4 from a narrow "candidate-shot generation
  and Monte Carlo simulation" framing to **"M4 — Probabilistic golfer
  modelling & shot outcome simulation"**, and added a preceding research/
  architecture milestone, **M4.0 — Research and define the CaddAI
  probabilistic golfer model**, that must be resolved before the detailed
  M4 implementation backlog is created. Rationale: shot-outcome sampling
  (Monte Carlo) is not the fundamental modelling problem — the more
  important problem is a defensible, evidence-based probabilistic
  representation of the shots a given golfer is likely to produce,
  initialised from an evidence-based population model personalised by
  onboarding information (handicap, self-reported carry, shot shape, common
  miss), and progressively updated from observed `ShotRecord` data over
  time. M5's purpose is unchanged. Documentation-only change — no
  production code, no new dependency, no M4 implementation issues created.
  Updated [docs/roadmap.md](docs/roadmap.md),
  [docs/prd.md](docs/prd.md), [docs/strategy-engine.md](docs/strategy-engine.md),
  [docs/player-model.md](docs/player-model.md), and
  [docs/backlog.md](docs/backlog.md) for consistency. CaddAI Architect
  subagent confirmed no ADR is required for this roadmap-level change; any
  new shared `player`/`statistics` abstraction (e.g.
  `PlayerShotDistribution`) or new runtime dependency M4.0 identifies as
  necessary will require its own ADR before M4 implementation begins. See
  [docs/plans/m4-roadmap-redefinition.plan.md](docs/plans/m4-roadmap-redefinition.plan.md).

### Fixed

- Reject non-finite values in `ShotRecord` measurements (M3.x, GitHub issue
  #43) in [src/caddai/player/models.py](src/caddai/player/models.py):
  `ShotRecord.achieved_carry_metres` and `ShotRecord.lateral_offset_metres`
  now use a `field_validator` (`math.isfinite`) to reject NaN and
  `+inf`/`-inf`, which previously satisfied the existing `ge=0` constraint
  on `achieved_carry_metres` and the unconstrained sign of
  `lateral_offset_metres`. No change to field names, types, or existing
  constraints for valid finite input. Added parametrized NaN/`+inf`/`-inf`
  rejection tests for both fields in
  [tests/test_player_models.py](tests/test_player_models.py). Follow-up to
  the equivalent hardening of `caddai.statistics` in GitHub issue #38. See
  [docs/plans/m3.x-reject-non-finite-shotrecord.plan.md](docs/plans/m3.x-reject-non-finite-shotrecord.plan.md).

- Reject non-finite values in `caddai.statistics` domain models (M3.x,
  GitHub issue #38) in
  [src/caddai/statistics/models.py](src/caddai/statistics/models.py):
  `CarryDistribution.mean_metres`/`stddev_metres` and
  `DirectionalDispersion.lateral_stddev_metres`/`lateral_bias_metres` now
  use a `field_validator` (`math.isfinite`) to reject NaN and `+inf`/`-inf`,
  which previously satisfied the existing `gt=0`/`ge=0` numeric constraints
  and could otherwise reach future `simulation`/`strategy` code undetected.
  No change to field names, types, or existing constraints for valid finite
  input. Added parametrized NaN/`+inf`/`-inf` rejection tests for all four
  fields in
  [tests/test_statistics_models.py](tests/test_statistics_models.py) and
  nested-validation-propagation tests through `Club` in
  [tests/test_player_models.py](tests/test_player_models.py). Architect
  confirmed no ADR is required — `caddai.statistics` remains a leaf module
  with no new `caddai.*` imports. See
  [docs/plans/m3.x-enforce-finite-statistics-values.plan.md](docs/plans/m3.x-enforce-finite-statistics-values.plan.md).

### Added

- Extended the developer demo (M3.7, GitHub issue #31) in
  [src/caddai/strategy/demo.py](src/caddai/strategy/demo.py):
  `build_demo_request()` now constructs each demo `Club` directly (rather
  than via `Club.with_expected_carry()`), giving every club a realistic,
  non-degenerate `CarryDistribution` (non-zero `stddev_metres`), a
  realistic `DirectionalDispersion` (non-zero `lateral_stddev_metres` and
  `lateral_bias_metres`, including a negative/left bias on the 5 Iron —
  the club the fixed demo scenario selects), and a real `ClubCategory`
  (`IRON`/`HYBRID`/`FAIRWAY_WOOD`) instead of `OTHER`. `main()` now prints
  an additional, clearly separated
  "Player-model context (informational only — not used in club
  selection):" section after `Reasons:`, showing the selected club's
  category, expected carry, carry variability (stddev), lateral
  dispersion (stddev), and lateral bias (with an explicit `+`/`-` sign and
  a "left"/"right" label preserving the established sign convention).
  **`recommend_club()` was not modified** — selection, confidence, and
  reasons logic is untouched; the new lines are purely informational
  presentation output and are not used by the decision logic. Added
  test-first coverage (already present in
  [tests/test_strategy_demo.py](tests/test_strategy_demo.py)) asserting
  the new output against the real `recommend_club(build_demo_request())`
  result, never hardcoded numbers. Added `caddai.statistics` to
  `strategy`'s `allowed_caddai_prefixes` in
  [tests/test_architecture_boundaries.py](tests/test_architecture_boundaries.py)
  for `demo.py`'s new `CarryDistribution`/`DirectionalDispersion` import
  (Architect-approved, no ADR required — no dependency, API, unit, or
  ownership change).
- Added `ShotRecord` (M3.5, GitHub issue #30) in
  [src/caddai/player/models.py](src/caddai/player/models.py): a new
  data-model-only, manually entered, observed shot outcome with
  `club_name` (non-empty string, a plain snapshot rather than an embedded
  `Club`), `achieved_carry_metres` (`ge=0`, so a whiffed/topped shot is
  representable, unlike `CarryDistribution.mean_metres`), a signed
  `lateral_offset_metres` (same sign convention as
  `DirectionalDispersion.lateral_bias_metres`: negative is left of the
  intended target line, zero is on-line, positive is right — independent
  of player handedness), and optional free-text `notes` (defaulting to
  `None`). `Player` gains `shot_history: list[ShotRecord]` defaulting to
  an empty list, with no cross-validation against `Player.clubs`. This
  change introduces no aggregation, distribution/dispersion fitting, or
  persistence — `shot_history` is in-memory only; deriving statistics from
  it is deferred to a future round-history/learning milestone (see
  `docs/backlog.md`). No ADR required (Architect review): the change adds
  no dependency, doesn't cross a module-ownership or dependency-direction
  boundary, and doesn't touch canonical units or a public API contract.
  `ShotRecord` is exported from `caddai.player.__init__`. Added
  construction, defaulting, validation (rejecting a negative
  `achieved_carry_metres`, an empty/missing `club_name`, and missing
  required fields), and `Player.shot_history` ordering/coercion/
  independence tests to
  [tests/test_player_models.py](tests/test_player_models.py). Updated
  [docs/player-model.md](docs/player-model.md)'s status note accordingly.
- Added `ClubCategory` taxonomy (M3.4, GitHub issue #29) in
  [src/caddai/player/models.py](src/caddai/player/models.py): a `StrEnum`
  with members `DRIVER`, `FAIRWAY_WOOD`, `HYBRID`, `IRON`, `WEDGE`,
  `PUTTER`, `OTHER`. `Club` gains a required `category: ClubCategory`
  field (no default, consistent with every other domain `StrEnum` field in
  the codebase), and `Club.with_expected_carry(...)` gains an optional
  `category: ClubCategory = ClubCategory.OTHER` parameter so existing call
  sites in `strategy/demo.py` and the test suite remain unchanged.
  `ClubCategory` is exported from `caddai.player.__init__`. Category is
  metadata only — no `caddai.strategy` behaviour keys off it in this
  change; no ADR required (Architect review). Added parametrized
  construction tests for every `ClubCategory` value, an invalid-category
  `ValidationError` test, and default/override tests for
  `with_expected_carry(...)` to
  [tests/test_player_models.py](tests/test_player_models.py). Updated
  [docs/player-model.md](docs/player-model.md)'s status note accordingly.
- Evolved `Club` (M3.3, GitHub issue #28) in
  [src/caddai/player/models.py](src/caddai/player/models.py) to compose a
  `CarryDistribution` and a `DirectionalDispersion` (both from
  `caddai.statistics`) instead of a bare `expected_carry_metres` scalar.
  `Club.expected_carry_metres` is now a computed field derived from
  `carry_distribution.mean_metres`, so existing readers (`recommend_club()`)
  are unchanged. Added `Club.with_expected_carry(name,
  expected_carry_metres)`, a convenience constructor that builds a
  degenerate (zero-variance, zero-bias) distribution and dispersion for
  call sites without a measured distribution yet — used by
  `strategy/demo.py` and the existing player/strategy tests.
  `recommend_club()` itself (`src/caddai/strategy/recommend.py`) was not
  modified; its behaviour for equivalent inputs is unchanged. Added a
  `player` `SubsystemBoundary` entry to
  `tests/test_architecture_boundaries.py`
  (`allowed_caddai_prefixes=("caddai.player", "caddai.statistics")`).
  Updated [docs/player-model.md](docs/player-model.md)'s status note to
  describe the new `Club` shape.
- Added `caddai.statistics.DirectionalDispersion` (M3.2, GitHub issue #27):
  a new model in [src/caddai/statistics/models.py](src/caddai/statistics/models.py)
  alongside `CarryDistribution`, with `lateral_stddev_metres` (`ge=0`) and
  a signed, unconstrained `lateral_bias_metres`. Adopts permanently the
  lateral-offset sign convention: negative is left of the intended target
  line, zero is on-line, and positive is right of the intended target
  line, independent of player handedness. `statistics` remains a leaf
  subsystem with no dependency on other `caddai.*` modules; no ADR
  required (Architect review). Updated
  [docs/player-model.md](docs/player-model.md)'s status note and
  "Directional dispersion" bullet to document the sign convention.
- Added the `caddai.statistics` subsystem (M3.1, GitHub issue #26): a new
  leaf module [src/caddai/statistics/](src/caddai/statistics/) with
  `CarryDistribution` (`mean_metres` gt 0, `stddev_metres` ge 0), depending
  on no other `caddai.*` module. Added its architecture-boundary coverage
  to `tests/test_architecture_boundaries.py` and updated
  [docs/player-model.md](docs/player-model.md)'s status note accordingly.
- Integrated `docs/prfaq.md` into the agent context system with selective,
  role-appropriate consultation rules (no code change). `AGENTS.md` now
  documents an explicit hierarchy — PRFAQ (customer/product experience),
  PRD (requirements/scope), roadmap (sequencing), architecture.md + ADRs
  (technical design), AGENTS.md (operating rules) — plus a "read only the
  documentation necessary for the task" context-efficiency principle.
  `.github/copilot-instructions.md` gained a matching concise note.
  `.github/agents/orchestrator.agent.md`, `architect.agent.md`, and
  `reviewer.agent.md` each gained explicit, role-specific triggers for when
  to consult the PRFAQ (and, for the Orchestrator, responsibility for
  routing documentation to specialists). `course-engineer.agent.md`,
  `player-engineer.agent.md`, `strategy-engineer.agent.md`, and
  `qa-engineer.agent.md` each gained a narrow rule confirming they do not
  read the PRFAQ by default. The PRFAQ still must never silently override
  an explicit ADR, architectural constraint, or accepted issue
  requirements — conflicts are escalated, not resolved silently.
- Added the approved CaddAI PRFAQ v0.1 as a first-class product document,
  [docs/prfaq.md](docs/prfaq.md) — the long-term customer-experience and
  product-principles north star. Documentation-only change; no production
  code modified. Updated `AGENTS.md` §12 documentation map, condensed
  cross-references in [docs/prd.md](docs/prd.md) and
  [docs/roadmap.md](docs/roadmap.md), a discoverability link in
  [README.md](README.md), and a concise instruction in
  `.github/copilot-instructions.md` to check significant product decisions
  against the PRFAQ. The PRFAQ never overrides an explicit ADR or
  architectural constraint; conflicts are escalated, not silently resolved.
- Roadmap and product documentation update for the approved long-term
  product direction: two new roadmap milestones appended after M9 — M10
  "Mobile software prototype (real-round validation)" (software-only,
  existing consumer devices, field-proves real-round usability before any
  dedicated hardware) and M11 "Hardware / on-device intelligence research"
  (exploratory only; hardware inputs — camera lie assessment, GNSS, IMU,
  compass, barometer, microphone — must produce canonical domain inputs
  such as `Lie`/`Position`/elevation/`Wind`, never golf strategy logic;
  dedicated hardware must not be committed to until M10 has validated
  real-round usage). New PRD "Product & commercial principles" section:
  the core product should remain usable without an ongoing subscription;
  recurring cloud costs should preferentially be recovered via optional
  paid rounds, prepaid usage credits, or optional premium cloud features,
  not by gating core GPS/strategy functionality behind a subscription; no
  prices or payment infrastructure selected. Reinforced that cloud LLM
  functionality is optional enrichment whose failure/exhaustion must never
  prevent a deterministic recommendation (already established by
  [ADR 0001](docs/adr/0001-deterministic-strategy-engine.md) and
  [ADR 0005](docs/adr/0005-offline-first-active-round-architecture.md); no
  new ADR required — confirmed with the CaddAI Architect). Documentation
  updated across `docs/roadmap.md`, `docs/prd.md`, `docs/architecture.md`
  (new "Future hardware/sensor adapters" section), `docs/vision.md`,
  `docs/backlog.md`, and `AGENTS.md`. No production code changed.

- Offline-first active-round architectural principle: network connectivity
  is optional during an active round; active-round core functionality
  (positioning, course geometry access, player profile access, distance
  calculations, shot simulation, strategy/recommendation, recording
  decisions/outcomes) must remain capable of local execution, while
  connectivity-enhanced functionality (course-data downloads, profile/
  round-history sync, cloud analytics, weather refresh, optional cloud LLM
  enhancement, etc.) may degrade gracefully offline but never become a
  prerequisite. Recorded in new
  [ADR 0005](docs/adr/0005-offline-first-active-round-architecture.md),
  complementary to (not a replacement for)
  [ADR 0001](docs/adr/0001-deterministic-strategy-engine.md). `AGENTS.md`
  §2 is now "Non-negotiable architectural principles" with §2.1
  (deterministic strategy) and §2.2 (offline-first active round); a new
  roadmap milestone, M5.5 "Runtime & Offline Architecture" (research spike,
  not implementation), is added between M5 and M6. Documentation updated
  across `AGENTS.md`, `.github/copilot-instructions.md`,
  `docs/architecture.md`, `docs/prd.md`, `docs/roadmap.md`,
  `docs/strategy-engine.md`, `docs/course-engine.md`,
  `docs/player-model.md`, `docs/decision-journal.md`, `docs/vision.md`,
  `docs/development-workflow.md`, and the custom agent definitions under
  `.github/agents/`. No production code changed.


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
