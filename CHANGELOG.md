# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/) once a
first public API is published.

## [Unreleased]

### Added

- Implemented **M4.5 — personal partial-pooling player-model updater**
  (GitHub issue #53), CaddAI's first personal-learning mechanism: a
  deterministic, closed-form partial-pooling (empirical-Bayes-style
  shrinkage) update that moves a `PlayerShotDistribution` from its current
  value (population-prior or onboarding-derived, per ADR 0006/ADR 0007
  precedent) toward personal `ShotRecord` evidence — no RNG/Monte Carlo.
  Split across two modules per the Architect's review
  (see [docs/plans/m4.5-personal-partial-pooling-updater.plan.md](docs/plans/m4.5-personal-partial-pooling-updater.plan.md)):
  the pure shrinkage math lives in a new
  [src/caddai/statistics/personalisation.py](src/caddai/statistics/personalisation.py)
  (`shrink_shot_distribution`, `PersonalisationConfig`,
  `WeightedObservations`, `WeightedJointObservations`,
  `DimensionUpdateOutcome`, `ShotDistributionUpdateResult`) — a leaf
  module with no `caddai.player` import — and the `ShotRecord`
  history-to-evidence glue lives in a new
  [src/caddai/player/personalisation.py](src/caddai/player/personalisation.py)
  (`build_shot_distribution_update_inputs`,
  `update_shot_distribution_from_history`,
  `MEASUREMENT_QUALITY_WEIGHTS`). Each `PlayerShotDistribution` dimension
  shrinks at its own rate: `carry_location_metres`/`lateral_bias_metres`
  (location) update fastest — pooled with the weighted sample mean of
  evidence via a pseudo-count-weighted convex combination, with no
  minimum-evidence gate beyond `n == 0`; `carry_scale_metres`/
  `lateral_scale_metres` (dispersion) and `correlation` each require a
  configurable minimum effective-observation-count (`sum(weights)`) before
  moving away from the prior at all, reported per-dimension via
  `DimensionUpdateOutcome`
  (`UPDATED`/`INSUFFICIENT_EVIDENCE`/`NO_EVIDENCE`/`HELD_FIXED_BY_POLICY`);
  `degrees_of_freedom` is never learned in V1 — always retained unchanged
  (`HELD_FIXED_BY_POLICY`). `ShotRecord.final_downrange_metres` is never
  used as carry evidence — only genuinely observed
  `observed_carry_metres` updates carry-space parameters.
  **Architect Decision A:** `lateral_offset_metres` (the shot's *final
  resting position*, not its carry-point lateral offset) is used as an
  explicitly documented, replaceable V1 approximation for the lateral
  dimension, since `PlayerShotDistribution`'s lateral parameters are,
  strictly, about intrinsic carry-point lateral shot production.
  **Architect Decision B:** measurement quality (`ShotMeasurementQuality`)
  is used as an explicit, named, provisional numeric weight
  (`MEASUREMENT_QUALITY_WEIGHTS`), not a record filter, with `UNKNOWN`
  contributing zero weight by default. All config values
  (`PersonalisationConfig`/`DEFAULT_PERSONALISATION_CONFIG`,
  `MEASUREMENT_QUALITY_WEIGHTS`) are explicit, versioned
  (`m4.5-provisional-v1`), and provisional pending calibration data,
  mirroring `population_prior_config.py`'s/`onboarding.py`'s own
  precedent. No ADR required — no new dependency, public API contract
  break, unit/ownership/dependency-direction change, or
  deterministic-strategy-principle change (see the plan doc's Architect
  decision record). Documented in
  [docs/player-model.md](docs/player-model.md); tests added in
  [tests/test_statistics_personalisation.py](tests/test_statistics_personalisation.py)
  and [tests/test_player_personalisation.py](tests/test_player_personalisation.py).
  **Pre-merge refinement:** the ambiguous `prior` parameter was renamed to
  `baseline_distribution` across `shrink_shot_distribution`,
  `update_shot_distribution_from_history`, and
  `build_shot_distribution_update_inputs` to make explicit that the update
  is a **batch recompute from full history, not an incremental update** —
  calling it repeatedly with the same inputs is idempotent, and the
  result from re-running over accumulated history matches applying the
  same shrinkage in one pass. Docstrings and new tests document this
  contract directly (Architect-approved, no ADR required — unreleased,
  unmerged code with zero external consumers).

- Implemented **M4.4 — `ShotRecord` provenance and measurement-quality
  fields** (GitHub issue #52), reworked around an evidence-only
  observation contract: normal on-course CaddAI use cannot directly
  observe true carry (the ball's first landing point), only shot
  start/finish position. In
  [src/caddai/player/models.py](src/caddai/player/models.py),
  `ShotRecord.achieved_carry_metres` is **renamed and re-scoped** (via an
  intermediate `total_distance_metres`) to `final_downrange_metres`
  (required, a signed coordinate — specifically the downrange component
  of the final resting position along the intended target line, not the
  straight-line start-to-finish distance; may be negative for a genuine
  severe outcome finishing behind the shot's start position, so no
  `ge=0` constraint is enforced — see the round-4 addendum below);
  `lateral_offset_metres` is unchanged in name but now explicitly
  documented as the lateral offset at the *final resting position*. A new
  optional `observed_carry_metres: float | None` (`ge=0`, finite-validated
  when present) captures true carry only when a suitable direct-measurement
  source (e.g. a launch monitor) genuinely measured it — it is `None` for
  the overwhelming majority of on-course shots and must never be
  auto-populated from an estimate. This is a deliberate breaking rename of
  an **unreleased, unconsumed-outside-`caddai.player.models`** field, not a
  preserved-compatibility change — no ADR required (see
  [docs/plans/m4.4-shotrecord-provenance-quality.plan.md](docs/plans/m4.4-shotrecord-provenance-quality.plan.md)
  for the Architect's full round-2 review); ADR 0006
  (`PlayerShotDistribution`) is unaffected, since it governs the golfer's
  intrinsic forward shot-production model, not this observation type.
  Measurement provenance/quality is **per-quantity, not record-level**: a
  new `ShotMeasurementMetadata` submodel (`source: ShotMeasurementSource`
  — `LAUNCH_MONITOR`/`GPS_DEVICE`/`MANUAL`/`UNKNOWN`; `quality:
  ShotMeasurementQuality` — `UNKNOWN`/`LOW`/`MODERATE`/`HIGH`) is composed
  once as `endpoint_measurement` (always present, defaults to
  `UNKNOWN`/`UNKNOWN`, and covering both `final_downrange_metres` and
  `lateral_offset_metres` as one shared final-position observation) and
  once as `observed_carry_measurement` (`None`
  unless `observed_carry_metres` is set), so a GPS-derived downrange
  distance and an absent/measured carry never share one falsely-uniform
  source/quality. A `model_validator` enforces that
  `observed_carry_metres`/`observed_carry_measurement` are null-paired (both
  present or both absent). No cross-field `observed_carry_metres <=
  final_downrange_metres` consistency check is enforced — `ShotRecord`
  records evidence, not physics consistency, and the two quantities may
  come from independent instruments that can legitimately disagree.
  `ShotMeasurementSource` remains a new, `ShotRecord`-specific enum,
  distinct from `caddai.player.onboarding.CarryProvenance` (a one-off
  onboarding cold-start self-report trust axis, not a historical-shot
  measurement provenance axis). No field on `ShotRecord` is consumed by any
  `CarryDistribution`/`DirectionalDispersion`/`PlayerShotDistribution`
  statistics/distribution math in this issue. `club_name` and `notes` are
  unchanged. The shape does not structurally assume every shot has
  meaningful carry — a `ClubCategory.PUTTER` shot naturally has
  `observed_carry_metres=None` with no forcing. Updated
  [src/caddai/player/__init__.py](src/caddai/player/__init__.py) to export
  `ShotMeasurementMetadata`/`ShotMeasurementSource`/`ShotMeasurementQuality`
  and rewrote [tests/test_player_models.py](tests/test_player_models.py)'s
  `ShotRecord` coverage for the new shape (construction, optionality,
  null-pairing, every enum member, invalid values, independent per-quantity
  metadata, large/severe values still accepted, serialization).
  Documented in [docs/player-model.md](docs/player-model.md); deferred
  follow-ups (a player-domain lie/context type, a penalty/OB/lost-ball
  flag, intended-shot-type/target-line context, an
  `observed_carry_lateral_metres` counterpart, and an
  attempted-but-rejected-measurement concept) recorded in
  [docs/backlog.md](docs/backlog.md).

  **Round-4 addendum (same issue):** `final_downrange_metres`/
  `lateral_offset_metres` are now documented as relative to the golfer's
  own **selected/accepted** intended target line for the shot — never
  automatically the pin, green centre, hole centreline, or a
  CaddAI-recommended target unless the golfer actually accepted it — so a
  deliberate aim away from a recommendation is never misread as player
  dispersion/bias by a future learning step. Constructing the
  target-line-relative coordinates, and recording which target was
  actually selected, is future upstream round/decision-journal
  responsibility, not implemented here — no new field was added.
  `final_downrange_metres` also lost its `ge=0` constraint: it is a
  **signed coordinate** along the target line, not an unsigned distance,
  since a genuine severe outcome (e.g. a deflection off an obstruction)
  can finish behind the shot's start position; `observed_carry_metres`
  correctly keeps `ge=0`, being a genuine scalar physical carry
  measurement, not a coordinate. Tests added for positive/zero/negative
  downrange, a negative-downrange-plus-large-lateral severe outcome, and
  `observed_carry_metres` still rejecting negative values.

- Documentation-only clarification of a product/strategy requirement ahead
  of M5 planning: CaddAI's strategy layer must ultimately support
  risk/reward evaluation, not only lowest-mean-expected-strokes selection,
  and risk preference must remain distinct from strategic situation
  without changing the underlying golfer/shot probability model. Updated
  [docs/prfaq.md](docs/prfaq.md) ("Will CaddAI tell everyone to play
  conservatively?" and "How will CaddAI model shots?") and
  [docs/roadmap.md](docs/roadmap.md) (M5) accordingly. No production code,
  ADR, or M5 implementation introduced; the concrete utility/risk
  architecture is deferred to the M5 planning/architecture pass.

- Implemented **M4.3 — Onboarding personalisation of
  `PlayerShotDistribution`** (GitHub issue #51). Added
  [src/caddai/player/onboarding.py](src/caddai/player/onboarding.py):
  `personalise_shot_distribution(*, handicap_index, club_category,
  reported_carry_metres, carry_provenance, common_miss, shot_shape=
  ShotShape.STRAIGHT) -> OnboardingPersonalisationResult`, the cold-start
  step (per `docs/research/m4-probabilistic-golfer-model.md`'s "Cold-start
  initialization and personal learning" section) that composes
  `resolve_population_prior` (ADR 0007) with onboarding information to
  build a golfer-specific `PlayerShotDistribution` (ADR 0006) for a single
  club. `carry_location_metres` is taken directly from the validated
  `reported_carry_metres` input; `lateral_bias_metres` is derived as
  `common_miss`'s sign times a new provisional dimensionless
  `ONBOARDING_COMMON_MISS_BIAS_STRENGTH` constant times the resolved
  club's `lateral_scale_metres`, so bias magnitude scales with the
  club/ability-specific lateral scale rather than being a flat metres
  constant across all clubs; `carry_scale_metres`,
  `lateral_scale_metres`, `correlation`, and `degrees_of_freedom` are
  copied verbatim from `resolve_population_prior(...).parameters` —
  mechanically enforcing the aleatoric/epistemic separation the issue
  requires. Added `CarryProvenance` (`MEASURED`/`GPS_ESTIMATE`/
  `PERSONAL_ESTIMATE`), a self-report-trust axis distinct from
  `caddai.statistics.population_prior`'s own confidence/provenance enums,
  mapped internally to a metadata-only `CarryConfidence`
  (`LOW`/`MODERATE`/`HIGH`) that never feeds into any
  `PlayerShotDistribution` scale/correlation/dof field. Added `ShotShape`
  (`STRAIGHT`/`DRAW`/`FADE`), accepted and recorded but not consumed by
  bias logic in this issue. Added the additive
  `OnboardingPersonalisationResult` (`shot_distribution`,
  `carry_provenance`, `carry_confidence`, `population_prior`, `shot_shape`,
  `onboarding_config_version`), precedented
  by `PopulationPriorResult`'s ADR 0007 "adjacent type" allowance. Added
  `ONBOARDING_CONFIG_VERSION` (`m4.3-provisional-v2`) and
  `ONBOARDING_COMMON_MISS_BIAS_STRENGTH` (dimensionless), both explicitly
  provisional pending calibration data, mirroring
  `population_prior_config.py`'s own provisional numbers.
  `ONBOARDING_COMMON_MISS_BIAS_STRENGTH` has no fitted/calibrated
  statistical meaning of its own (a convenience heuristic only) and
  deliberately couples onboarding bias magnitude to `caddai.statistics`'s
  population-prior `lateral_scale_metres` — recalibrating that config also
  changes onboarding bias magnitude for the same `common_miss` input.
  `resolve_population_prior`'s own `ValueError`/
  `PopulationPriorUnsupportedCategoryError` (`PUTTER`=`DEFERRED`,
  `OTHER`=`NOT_MODELABLE`) propagate unmodified; invalid/non-finite
  `reported_carry_metres` raises a plain `ValueError`. No RNG, `sample()`,
  Monte Carlo logic, or network calls; `caddai.statistics` is untouched and
  remains a leaf module. Updated
  [src/caddai/player/__init__.py](src/caddai/player/__init__.py) to export
  the new public names and
  [tests/test_architecture_boundaries.py](tests/test_architecture_boundaries.py)
  to cover the new file. Added
  [tests/test_player_onboarding.py](tests/test_player_onboarding.py) and
  documented in [docs/player-model.md](docs/player-model.md).
- Implemented **M4.2 — `PopulationPrior` population parameter model**
  (GitHub issue #50), the ADR 0007 stable/replaceable handicap/
  club-category population-prior contract. Migrated `ClubCategory`'s
  canonical definition from `caddai.player.models` to
  `caddai.statistics.models` (so `caddai.statistics` remains a leaf
  module, per module ownership) — `caddai.player` still re-exports
  `ClubCategory` unchanged, so every existing import path and serialized
  `StrEnum` value is preserved. Added
  [src/caddai/statistics/population_prior.py](src/caddai/statistics/population_prior.py):
  `PopulationPriorParameters` (`family`, `carry_scale_metres`,
  `lateral_scale_metres`, `correlation`, `degrees_of_freedom`, mirroring
  `PlayerShotDistribution`'s own field bounds), `PopulationPriorConfidence`
  (`StrEnum`: `LOW`/`MODERATE`/`HIGH`), `PopulationPriorProvenance`
  (`StrEnum`: `EVIDENCE_INFORMED_PROVISIONAL_CONFIG`/`CADDAI_CALIBRATION`/
  `FITTED_MODEL`), `PopulationPriorResult`, and
  `resolve_population_prior(handicap_index,
  club_category) -> PopulationPriorResult`, which validates
  `handicap_index` (finite, in `[-10.0, 54.0]`) and `club_category` (one of
  the 5 supported full-swing categories — `PUTTER`/`OTHER` rejected) and
  raises `ValueError` on violation. Deliberately does **not** construct a
  `PlayerShotDistribution` directly — `carry_location_metres`/
  `lateral_bias_metres` require M4.3 onboarding data, not a
  handicap/club-category lookup. Added
  [src/caddai/statistics/population_prior_config.py](src/caddai/statistics/population_prior_config.py),
  a small, explicit, versioned (`m4.2-provisional-v1`) lookup table backing
  the contract, with every cell uniformly marked
  `confidence=PopulationPriorConfidence.LOW` and
  `provenance=PopulationPriorProvenance.EVIDENCE_INFORMED_PROVISIONAL_CONFIG`
  — explicitly provisional CaddAI configuration, not validated population
  data, per the unresolved evidence/calibration gaps identified in
  [docs/research/m4-probabilistic-golfer-model.md](docs/research/m4-probabilistic-golfer-model.md).
  `FAIRWAY_WOOD`/`HYBRID` share identical values in every band (the
  research doc groups them together). Flipped
  [ADR 0006](docs/adr/0006-player-shot-distribution-bivariate-student-t.md)
  and [ADR 0007](docs/adr/0007-population-prior-replaceability.md) status
  from Proposed to Accepted. No new runtime dependency; no `sample()`/RNG/
  Monte Carlo logic; `caddai.statistics` remains a leaf module. Added
  [tests/test_population_prior.py](tests/test_population_prior.py) and
  updated [tests/test_player_models.py](tests/test_player_models.py),
  [tests/test_architecture_boundaries.py](tests/test_architecture_boundaries.py),
  and documented in [docs/player-model.md](docs/player-model.md) and
  [docs/architecture.md](docs/architecture.md).
  Refined the `PUTTER`/`OTHER` rejection: added
  `ClubCategorySupportStatus` (`SUPPORTED`/`DEFERRED`/`NOT_MODELABLE`),
  `CLUB_CATEGORY_SUPPORT_STATUS`, and `club_category_support_status()` to
  `population_prior.py`, and replaced the previous single generic
  `ValueError` with `PopulationPriorUnsupportedCategoryError` (a
  `ValueError` subclass carrying `.club_category`/`.status`) so
  `ClubCategory.PUTTER` — a valid category whose own model is merely
  deferred, since putting is a distinct shot regime from full swings — is
  no longer indistinguishable from `ClubCategory.OTHER`'s genuinely
  not-modelable catch-all. No `PUTTER` row was added to
  `POPULATION_PRIOR_CONFIG`.
  Pre-merge contract correction: `HandicapBand` is now a private
  implementation detail of
  [src/caddai/statistics/population_prior_config.py](src/caddai/statistics/population_prior_config.py)
  (renamed `_HandicapBand`, alongside a private `_band_for_handicap_index`
  helper) rather than part of the public `caddai.statistics` contract.
  `PopulationPriorResult` no longer has a `handicap_band` field —
  `resolve_population_prior` now passes `handicap_index` straight through
  to `population_prior_config.lookup(handicap_index, club_category)`,
  which resolves the internal band itself. `PopulationPriorResult`'s final
  field list is `parameters`, `confidence`, `provenance`, `config_version`,
  `club_category`, `handicap_index` — the continuous `handicap_index` is
  the only handicap-related field a future fitted/learned population-prior
  model (ADR 0007) needs to consume directly, without depending on today's
  bucket scheme.
- Implemented **M4.1 — `PlayerShotDistribution` domain type** (GitHub
  issue #49), the ADR 0006 bivariate Student-t shot-production
  representation. Added
  [src/caddai/statistics/shot_distribution.py](src/caddai/statistics/shot_distribution.py):
  `ShotDistributionFamily` (`StrEnum`, currently only
  `BIVARIATE_STUDENT_T`) and `PlayerShotDistribution` (`family`,
  `carry_location_metres`, `lateral_bias_metres`, `carry_scale_metres`,
  `lateral_scale_metres`, `correlation`, `degrees_of_freedom`), all
  finite-value validated via the existing `_require_finite` pattern.
  `carry_scale_metres`/`lateral_scale_metres` are strictly positive (zero
  rejected, diverging intentionally from M3's stddev fields),
  `correlation` is constrained to the open interval `(-1, 1)`, and
  `degrees_of_freedom` must be strictly greater than 2 — per the CaddAI
  Architect's confirmed boundary decisions recorded in
  [docs/plans/m4.1-player-shot-distribution.plan.md](docs/plans/m4.1-player-shot-distribution.plan.md),
  ADR 0006, and ADR 0007. Added computed properties
  `implied_covariance_metres_sq`, `implied_carry_stddev_metres`, and
  `implied_lateral_stddev_metres`, applying the `nu/(nu-2)`
  covariance-scaling factor, with docstrings explicit that the scale
  parameters are not standard deviations or a covariance matrix.
  `PlayerShotDistribution` holds independent joint parameters — it does
  not compose with or derive from M3's `CarryDistribution`/
  `DirectionalDispersion` in this issue (Option B; composition is M4.6),
  and it stores no ADR 0007 provenance/confidence metadata (deferred to
  the future `PopulationPrior` type, M4.2). No `sample()`, RNG, or Monte
  Carlo logic — construction remains deterministic and side-effect free,
  and `caddai.statistics` remains a leaf module with no new runtime
  dependency. Re-exported from `caddai.statistics.__init__`, added to
  `tests/test_architecture_boundaries.py`'s `statistics` boundary
  `source_files`, and documented in
  [docs/player-model.md](docs/player-model.md).
- Completed the **M4.0 — Research and define the CaddAI probabilistic
  golfer model** research spike (GitHub issue #47). Added the Deep Research
  report at
  [docs/research/m4-probabilistic-golfer-model.md](docs/research/m4-probabilistic-golfer-model.md),
  reviewed it with the CaddAI Architect subagent against M3
  `player`/`statistics`, `docs/roadmap.md`, `docs/architecture.md`,
  existing ADRs, and `docs/prfaq.md`, and recorded the final CaddAI
  recommendation in that document: a bivariate Student-t
  `PlayerShotDistribution` shot-production representation with an
  evidence-derived but explicitly provisional population prior, onboarding
  personalisation informed by reported-carry provenance, and partial-
  pooling/empirical-Bayes personal learning — no new runtime dependency.
  Added [ADR 0006](docs/adr/0006-player-shot-distribution-bivariate-student-t.md)
  (bivariate Student-t `PlayerShotDistribution` as the V1 shot-production
  representation) and [ADR 0007](docs/adr/0007-population-prior-replaceability.md)
  (population-prior replaceability contract, preserving the offline-first
  active-round constraint). No production code, no M4 implementation
  issues created — see the research document's "Proposed M4 implementation
  backlog" for the follow-up issue breakdown, to be created after this
  review.

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
- Reconciled M3 documentation with the completed implementation (M3.8,
  GitHub issue #32). Marked M3 complete in the status banners of
  [docs/roadmap.md](docs/roadmap.md) and
  [docs/architecture.md](docs/architecture.md), and corrected
  [docs/domain-model.md](docs/domain-model.md)'s stale "no domain types are
  implemented yet" line. Rewrote
  [docs/player-model.md](docs/player-model.md)'s status note to describe
  every implemented M3 capability — `CarryDistribution`,
  `DirectionalDispersion`, `Club` (with `category`), `Player.shot_history`,
  `ShotRecord`, and the finite-value validation added in issues #38 and
  #43 — and added explicit M3 boundary statements: no fitting/learning of
  distributions from `shot_history`, no Monte Carlo simulation, `dispersion`/
  `category` are not read by strategy decisions, and no persistence or
  runtime technology decision has been made. Added a
  [docs/backlog.md](docs/backlog.md) item about `ShotRecord.club_name`
  identity/history semantics (a plain string snapshot with no referential
  integrity against `Player.clubs`). No source code changes — this is pure
  documentation reconciliation for M3 completion. See
  [docs/plans/m3.8-m3-docs-status-completion.plan.md](docs/plans/m3.8-m3-docs-status-completion.plan.md).

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
