# Player model

> Status: M3 is complete — `player`/`statistics` are implemented, not
> planned. [src/caddai/statistics/models.py](../src/caddai/statistics/models.py)
> defines `CarryDistribution` (`mean_metres`/`stddev_metres`, finite-value
> validated per issue #38) and `DirectionalDispersion` (lateral stddev +
> signed lateral bias, finite-value validated per issue #38, with a fixed
> sign convention independent of player handedness — negative left, zero
> on-line, positive right of the intended target line).
> [src/caddai/player/models.py](../src/caddai/player/models.py) defines
> `Club` (free-text `name`, a `category: ClubCategory` taxonomy,
> `carry_distribution`, `dispersion`, a computed `expected_carry_metres`
> field derived from `carry_distribution.mean_metres`, and a
> `with_expected_carry(...)` constructor building a placeholder/degenerate
> zero-variance, zero-bias `Club` from a bare expected-carry scalar for
> callers without a measured distribution), `Player` (`clubs`,
> `shot_history`), and `ShotRecord` (a `club_name` snapshot,
> `final_downrange_metres`, `lateral_offset_metres`, optional `notes`,
> finite-value validated per issue #43; see the M4.4 paragraph below for
> the evidence-only shape, including `observed_carry_metres` and
> per-quantity measurement metadata). `ShotRecord.club_name` is a plain
> string snapshot only — it is **not** cross-validated against
> `Player.clubs`; renaming or removing a club from a player's bag does not
> update or invalidate existing shot records (see `docs/backlog.md`).
>
> M3 boundaries: only manually-supplied statistical parameters are stored —
> no fitting/learning of `CarryDistribution`/`DirectionalDispersion` from
> `shot_history` exists; no Monte Carlo simulation exists (that's M4);
> `dispersion`/`category` are not read by strategy decisions —
> `recommend_club()` only reads `expected_carry_metres`; no persistence/
> storage technology has been selected; and no mobile/cloud runtime
> decision has been made.
>
> M4.1 (issue #49) added
> [src/caddai/statistics/shot_distribution.py](../src/caddai/statistics/shot_distribution.py):
> `PlayerShotDistribution`, the ADR 0006 bivariate Student-t shot-production
> domain type (`family: ShotDistributionFamily`, `carry_location_metres`,
> `lateral_bias_metres`, `carry_scale_metres`, `lateral_scale_metres`,
> `correlation`, `degrees_of_freedom`, all finite-value validated), plus
> computed `implied_covariance_metres_sq`/`implied_carry_stddev_metres`/
> `implied_lateral_stddev_metres` properties applying the `nu/(nu-2)`
> covariance-scaling factor. It coexists with, and is independent of,
> `CarryDistribution`/`DirectionalDispersion` — it does not compose with or
> derive from either M3 type; composition is deferred to M4.6. Its numeric
> hyperparameters remain provisional pending calibration data per ADR
> 0006/ADR 0007, and it stores no ADR 0007 provenance/confidence metadata
> (deferred to the future `PopulationPrior` type, M4.2). No sampling/RNG/
> Monte Carlo logic exists in this type.
>
> M4.2 (issue #50) added
> [src/caddai/statistics/population_prior.py](../src/caddai/statistics/population_prior.py):
> `resolve_population_prior(handicap_index, club_category) ->
> PopulationPriorResult`, the ADR 0007 `PopulationPrior` contract. It does
> **not** construct a `PlayerShotDistribution` directly — it returns
> `PopulationPriorParameters` covering only `carry_scale_metres`/
> `lateral_scale_metres`/`correlation`/`degrees_of_freedom`, since
> `carry_location_metres`/`lateral_bias_metres` require onboarding data
> (M4.3) that a handicap/club-category lookup alone cannot supply.
> `PopulationPriorResult` also carries `confidence`
> (`PopulationPriorConfidence`), `provenance` (`PopulationPriorProvenance`),
> and `config_version` for traceability. Internal handicap banding
> (`_HandicapBand`) is a private implementation detail of
> [src/caddai/statistics/population_prior_config.py](../src/caddai/statistics/population_prior_config.py)'s
> lookup table only — it is not part of the public `caddai.statistics`
> contract. `PopulationPriorResult` only ever exposes the continuous
> `handicap_index` (float), so a future fitted/learned population-prior
> model (ADR 0007) can consume it directly without depending on today's
> bucket scheme. Backing data lives in
> [src/caddai/statistics/population_prior_config.py](../src/caddai/statistics/population_prior_config.py)
> (version `m4.2-provisional-v1`) — a small, explicit, versioned table that
> is **explicitly provisional CaddAI configuration**, not validated
> population data: every cell is marked `confidence=LOW` and
> `provenance=EVIDENCE_INFORMED_PROVISIONAL_CONFIG`, pending the
> calibration data described in
> [docs/research/m4-probabilistic-golfer-model.md](research/m4-probabilistic-golfer-model.md)'s
> "Unresolved evidence/calibration gaps". This issue also migrated
> `ClubCategory`'s canonical definition from `caddai.player` to
> `caddai.statistics.models` (so `caddai.statistics` remains a leaf module)
> — `caddai.player` still re-exports it unchanged, so every existing import
> path and serialized value is preserved.
>
> `resolve_population_prior` distinguishes `ClubCategory.PUTTER` — a valid
> category whose own probabilistic model is deferred, since putting is a
> behaviourally distinct shot regime from full swings — from
> `ClubCategory.OTHER`, an intentional catch-all with no modelable
> mechanics. Both raise `PopulationPriorUnsupportedCategoryError` (a
> `ValueError` subclass, so existing `pytest.raises(ValueError)`-style
> callers remain compatible), distinguishable via its `status` attribute
> (`ClubCategorySupportStatus.DEFERRED` vs `NOT_MODELABLE`,
> `club_category_support_status()`/`CLUB_CATEGORY_SUPPORT_STATUS` expose
> the mapping for all 7 `ClubCategory` members).
>
> M4.3 (issue #51) added
> [src/caddai/player/onboarding.py](../src/caddai/player/onboarding.py):
> `personalise_shot_distribution(*, handicap_index, club_category,
> reported_carry_metres, carry_provenance, common_miss, shot_shape=
> ShotShape.STRAIGHT) -> OnboardingPersonalisationResult`, the cold-start
> step that builds a golfer-specific `PlayerShotDistribution` for a single
> club from `resolve_population_prior` (ADR 0007) plus onboarding
> information. `carry_location_metres` is set directly from the validated
> `reported_carry_metres` input (no invented trust-weighted blend — no
> defensible population carry-location prior exists to blend toward);
> `lateral_bias_metres` is `common_miss`'s sign (`LEFT`/`NONE`/`RIGHT`)
> times the provisional dimensionless `ONBOARDING_COMMON_MISS_BIAS_STRENGTH`
> times the resolved club's `lateral_scale_metres`, so bias magnitude
> scales with the club/ability-specific lateral scale rather than being a
> flat metres constant across all clubs; `carry_scale_metres`,
> `lateral_scale_metres`, `correlation`, and `degrees_of_freedom` are
> copied verbatim from `resolve_population_prior(...).parameters`. This is
> the binding aleatoric/epistemic separation the issue requires: a new
> `CarryProvenance` (`MEASURED`/`GPS_ESTIMATE`/`PERSONAL_ESTIMATE`) enum
> describes the trustworthiness of a self-reported carry and maps to a
> `CarryConfidence` (`LOW`/`MODERATE`/`HIGH`) — both metadata-only, never
> feeding into any `PlayerShotDistribution` scale/correlation/dof field.
> `ShotShape` (`STRAIGHT`/`DRAW`/`FADE`) is accepted and recorded but not
> consumed by bias logic in this issue. `resolve_population_prior`'s own
> `ValueError`/`PopulationPriorUnsupportedCategoryError` (invalid
> handicap, `PUTTER`=`DEFERRED`, `OTHER`=`NOT_MODELABLE`) propagate
> unmodified. `OnboardingPersonalisationResult` (`shot_distribution`,
> `carry_provenance`, `carry_confidence`, `population_prior`,
> `shot_shape`, `onboarding_config_version`) is a small additive result
> type, precedented by `PopulationPriorResult`'s "adjacent type" allowance
> under ADR 0007, rather than nSTRENGTH`/`ONBOARDING_CONFIG_VERSION`
> (`m4.3-provisional-v2`) are explicitly provisional, unvalidated
> constants pending calibration data, mirroring
> `population_prior_config.py`'s own provisional numbers.
> `ONBOARDING_COMMON_MISS_BIAS_STRENGTH` is dimensionless and carries no
> fitted/calibrated statistical meaning of its own; it is a convenience
> heuristic to make bias magnitude scale sensibly with club, nothing more.
> This creates an intentional intra-`caddai.player` coupling: recalibrating
> `lateral_scale_metres` in `caddai.statistics`'s population-prior config
> also changes onboarding bias magnitude for the same `common_miss` input.
>alidated
> constants pending calibration data, mirroring
> `population_prior_config.py`'s own provisional numbers. No RNG,
> `sample()`, or Monte Carlo logic exists in this module; `caddai.player`
> remains the only dependent of `caddai.statistics` (unmodified by this
> issue).
>
> M4.4 (issue #52) reworked `ShotRecord` in
> [src/caddai/player/models.py](../src/caddai/player/models.py) around an
> evidence-only observation contract: normal on-course CaddAI use cannot
> directly observe true carry (the
> ball's first landing point), only shot start/finish position.
> `achieved_carry_metres` is **renamed and re-scoped** (via an
> intermediate `total_distance_metres`) to `final_downrange_metres`
> (required, a signed coordinate — specifically the *downrange* component
> of the final resting position along the intended target line, not the
> straight-line start-to-finish distance, which would additionally require
> `lateral_offset_metres`; may be negative for a genuine severe outcome
> finishing behind the shot's start position, so no `ge=0` constraint is
> enforced — see the round-4 addendum below); `lateral_offset_metres`
> keeps its name but is
> now documented as the lateral offset at the *final resting position*. A
> new optional `observed_carry_metres: float | None` (`ge=0`,
> finite-validated when present) records true carry only when a suitable
> direct-measurement source (e.g. a launch monitor) genuinely measured
> it — `None` for the overwhelming majority of shots, and never
> auto-populated from an estimate. This is a deliberate breaking rename of
> a field with no consumer outside `caddai.player.models` and no release
> yet, not a preserved-compatibility change — see
> [docs/plans/m4.4-shotrecord-provenance-quality.plan.md](plans/m4.4-shotrecord-provenance-quality.plan.md)
> for the Architect's full review; ADR 0006 is unaffected. Measurement
> provenance/quality is **per-quantity, not record-level**: a new
> `ShotMeasurementMetadata` submodel (`source: ShotMeasurementSource` —
> `LAUNCH_MONITOR`/`GPS_DEVICE`/`MANUAL`/`UNKNOWN`; `quality:
> ShotMeasurementQuality` — `UNKNOWN`/`LOW`/`MODERATE`/`HIGH`) is composed
> once as `endpoint_measurement` (always present, default
> `UNKNOWN`/`UNKNOWN`, and covering both `final_downrange_metres` and
> `lateral_offset_metres` as one shared final-position observation) and
> once as `observed_carry_measurement` (`None`
> unless `observed_carry_metres` is set), so one quantity's
> source/quality never falsely applies to the other. A validator enforces
> `observed_carry_metres`/`observed_carry_measurement` are null-paired. No
> `observed_carry_metres <= final_downrange_metres` consistency check is
> enforced — `ShotRecord` records evidence, not physics consistency; the
> two may come from independent instruments that can legitimately
> disagree. None of these fields are consumed by any
> `CarryDistribution`/`DirectionalDispersion`/`PlayerShotDistribution`
> statistics/distribution math yet; whether/how a future personal-learning
> updater (M4.5+) weights or filters shots by them is that updater's
> decision. The shape does not structurally assume every shot has
> meaningful carry — a `ClubCategory.PUTTER` shot naturally has
> `observed_carry_metres=None` with no forcing. `club_name`/`notes` are
> unchanged. All new types are exported from `caddai.player.__init__`. No
> ADR was required (ordinary, if larger-than-usual, additive/corrective
> domain evolution — no shipped cross-subsystem consumer existed to
> break).
>
> Round-4 addendum (same issue): `final_downrange_metres`/
> `lateral_offset_metres` are relative to the golfer's own
> **selected/accepted** intended target line for the shot, never
> automatically the pin/green centre/hole centreline/a CaddAI-recommended
> target unless actually accepted — constructing those coordinates and
> recording which target was selected is future round/decision-journal
> responsibility (`docs/decision-journal.md`), not implemented here; no
> new field was added. `final_downrange_metres` lost its `ge=0` constraint
> — it is a signed coordinate, not an unsigned distance, since a genuine
> severe outcome can finish behind the shot's start position;
> `observed_carry_metres` keeps `ge=0` (a genuine physical carry
> measurement, not a coordinate).
>
> M4.5 (issue #53) added CaddAI's first personal-learning mechanism: a
> deterministic, closed-form partial-pooling (empirical-Bayes-style
> shrinkage) update that moves a `PlayerShotDistribution` from its current
> value (population-prior or onboarding-derived) toward personal
> `ShotRecord` evidence. Split across two modules per the Architect's
> review: the pure shrinkage math lives in
> [src/caddai/statistics/personalisation.py](../src/caddai/statistics/personalisation.py)
> (`shrink_shot_distribution(baseline_distribution, *, carry_observations,
> lateral_observations, joint_observations, config) ->
> ShotDistributionUpdateResult`; a leaf module, no `caddai.player`
> import), and the `ShotRecord` -> weighted-array glue lives in
> [src/caddai/player/personalisation.py](../src/caddai/player/personalisation.py)
> (`build_shot_distribution_update_inputs`,
> `update_shot_distribution_from_history`, both taking
> `baseline_distribution` as their first parameter). Each dimension
> shrinks at its own rate, consistent with the M4.0 research ordering
> (location fastest, dispersion slower, correlation slower still,
> degrees-of-freedom never learned): `carry_location_metres`/
> `lateral_bias_metres` pool the prior value with the weighted sample
> mean of evidence via a
> `location_prior_pseudo_count`-weighted convex combination (no minimum-
> evidence gate beyond zero evidence); `carry_scale_metres`/
> `lateral_scale_metres` convert to variance via the same `nu/(nu-2)`
> factor `implied_covariance_metres_sq` uses (Student-t scale is not
> standard deviation), pool variances via `dispersion_prior_pseudo_count`,
> and convert back, gated by `dispersion_min_effective_observations`;
> `correlation` pools a weighted-Pearson-correlation sample statistic via
> `correlation_prior_pseudo_count`, hard-gated by
> `correlation_min_effective_observations`, with near-zero-variance legs
> and a pre-pooling clip protecting against a degenerate or exactly-+/-1
> result; `degrees_of_freedom` is always retained unchanged
> (`DimensionUpdateOutcome.HELD_FIXED_BY_POLICY`) — never estimated in V1.
> Each dimension's outcome (`UPDATED`/`INSUFFICIENT_EVIDENCE`/
> `NO_EVIDENCE`/`HELD_FIXED_BY_POLICY`) and effective evidence count
> (`sum(weights)`) are reported on `ShotDistributionUpdateResult` for
> traceability. Configuration
> (`PersonalisationConfig`/`DEFAULT_PERSONALISATION_CONFIG`, version
> `m4.5-provisional-v1`) is explicitly provisional/uncalibrated, mirroring
> `population_prior_config.py`'s/`onboarding.py`'s own precedent.
>
> **Architect Decision A — endpoint lateral vs intrinsic lateral (V1
> limitation):** `PlayerShotDistribution`'s lateral dimension is, strictly,
> the ball's *intrinsic* lateral shot production. V1 approximates this
> with `ShotRecord.lateral_offset_metres` — the lateral offset at the
> shot's *final resting position*, not its first-landing/carry-point
> lateral offset — a documented, accepted, replaceable approximation, not
> a silent substitution: rollout after landing can shift the lateral
> offset between carry and final position. Carry-space parameters
> (`carry_location_metres`, `carry_scale_metres`) are never derived from
> endpoint data, only from genuinely observed `observed_carry_metres`;
> `final_downrange_metres` is not consumed by this updater at all.
>
> **Architect Decision B — measurement-quality weighting:**
> `caddai.player.personalisation.MEASUREMENT_QUALITY_WEIGHTS` maps each
> `ShotMeasurementQuality` to an explicit numeric weight (`HIGH=1.0`,
> `MODERATE=0.6`, `LOW=0.25`, `UNKNOWN=0.0`) applied per-quantity, per-
> record — not a filter, and not ignored. `UNKNOWN` contributes zero
> weight, equivalent to that dimension not existing for the record, never
> discarding the whole record. `ShotMeasurementSource` remains metadata-
> only in V1 (not a second weighting axis). Evidence selection is
> dimension-specific per record — a record can contribute to carry,
> lateral, both, or neither; joint (correlation) evidence requires both
> legs usable for the same record, weighted by the `min()` of the two leg
> weights. No ADR was required (no new dependency, public API contract
> change, unit/ownership/dependency-direction change, or
> deterministic-strategy-principle change) — see
> [docs/plans/m4.5-personal-partial-pooling-updater.plan.md](plans/m4.5-personal-partial-pooling-updater.plan.md).
>
> **Naming and batch-recompute contract:** the first parameter of all
> three public functions is named `baseline_distribution` (renamed from an
> earlier `prior` during pre-merge review) to make explicit that it must
> always be the same immutable cold-start `PlayerShotDistribution` — the
> golfer's population-prior or onboarding-derived distribution — never a
> previously-returned `ShotDistributionUpdateResult.shot_distribution`.
> All three functions recompute the posterior from scratch on every call
> (batch recomputation over the *complete* current eligible evidence set);
> none of them accumulate sufficient statistics incrementally across
> calls. Incremental/online Bayesian updating (accumulating sufficient
> statistics call-to-call instead of recomputing from the full history
> each time) is explicitly deferred — not implemented — in M4.5.
>
> M4.6 (issue #54) composed `PlayerShotDistribution` into `Club` without
> duplicating or coupling to M3's `CarryDistribution`/`DirectionalDispersion`.
> [src/caddai/player/models.py](../src/caddai/player/models.py) added an
> additive `Club.shot_distribution: PlayerShotDistribution | None = None`
> field — every existing `Club(...)` construction site (tests, `demo.py`,
> `with_expected_carry`) is unaffected by the default, and
> `with_expected_carry(...)` itself remains unchanged, leaving
> `shot_distribution` at its `None` default. `shot_distribution` holds only
> the immutable *baseline* (onboarding/population-prior cold-start
> distribution) — nothing ever writes a shrinkage posterior back into it.
> Its `None` value is uniformly "no baseline composed yet": `Club` stores
> no second marker for *why* (not-yet-onboarded vs. `ClubCategory.PUTTER`
> deferred vs. `ClubCategory.OTHER` not-modelable) — that distinction is
> derived on demand from `club.category` via the existing
> `club_category_support_status()` (`caddai.statistics`), never stored
> redundantly on `Club` itself.
>
> [src/caddai/player/shot_distribution.py](../src/caddai/player/shot_distribution.py)
> added the two composition/resolution entry points, as plain functions
> rather than `Club` methods (matching the existing convention —
> `Club.expected_carry_metres`/`with_expected_carry` remain the two
> existing method-style exceptions, not a precedent to extend):
> `compose_club_shot_distribution(*, handicap_index, club_category,
> reported_carry_metres, carry_provenance, common_miss, club_name,
> shot_history, shot_shape=ShotShape.STRAIGHT, config=None) ->
> ClubShotDistributionComposition` is the single M4.2 -> M4.3 -> M4.5
> composition entry point, called at (re-)onboarding time: it calls
> `personalise_shot_distribution` itself (the caller supplies raw
> onboarding inputs, not a pre-built `OnboardingPersonalisationResult`),
> propagates its `ValueError`/`PopulationPriorUnsupportedCategoryError`
> unmodified, then calls `update_shot_distribution_from_history` against
> `shot_history`, and returns `baseline_shot_distribution` (the caller
> persists this onto `Club.shot_distribution` explicitly — this function
> never mutates a `Club`), `current_shot_distribution` (immediate-use
> only, must never be persisted anywhere, including onto
> `Club.shot_distribution`, or a later call would silently double-count
> evidence already absorbed into what should be an immutable baseline),
> `onboarding` (`OnboardingPersonalisationResult`), and `update`
> (`ShotDistributionUpdateResult`). `resolve_current_shot_distribution(club,
> shot_history, config=None) -> ClubShotDistributionResolution` is the
> ongoing read path against an already-baselined `Club` (for
> `caddai.simulation`, M4.8, and any future `strategy` consumer built
> against `PlayerShotDistribution`): it never calls
> `resolve_population_prior`/`personalise_shot_distribution` (onboarding-time
> only), never mutates `club`/`club.shot_distribution`, and returns
> `shot_distribution: PlayerShotDistribution | None` plus `support_status:
> ClubCategorySupportStatus` (reused from `caddai.statistics`, not a new
> competing enum) — `None`/`SUPPORTED` means "not yet onboarded";
> `None`/`DEFERRED` means `PUTTER`; `None`/`NOT_MODELABLE` means `OTHER`;
> present/`SUPPORTED` means resolved and ready to use. `support_status` is
> always recomputed from `club.category`, independent of whether
> `shot_distribution` happens to be populated. Two functions, not one: they
> solve different call patterns (`onboarding inputs -> baseline` vs.
> `existing Club + fresh history -> current`) — collapsing them would force
> every M4.8 read-path call to also carry onboarding scalars it doesn't
> have.
>
> **M3-vs-M4 authority note:** M3 (`CarryDistribution`/`DirectionalDispersion`)
> remains authoritative for unmigrated consumers (`Club.expected_carry_metres`,
> current `strategy.recommend_club()`, which only reads
> `expected_carry_metres`). M4 (`PlayerShotDistribution`, via
> `resolve_current_shot_distribution`) becomes authoritative for any
> consumer built against it (`caddai.simulation`, M4.8; later `strategy`).
> No code ties the two together — no validator, computed field, or
> conversion function links `carry_distribution.mean_metres` to
> `shot_distribution.carry_location_metres`; they may legitimately hold
> different numbers for the same club. This is a **documentation**
> discipline, not a code one (enforcing consistency would itself be the
> coupling ADR 0006 rejects): once `shot_distribution` is populated for a
> club, `carry_distribution`/`dispersion` are not read by any
> `shot_distribution`-aware consumer, by convention — no consumer should
> read both and blend/average them. To state this unambiguously: M4
> `PlayerShotDistribution` is *the* authoritative representation for
> probabilistic simulation (`caddai.simulation`, M4.8, and any future
> `strategy` consumer built against it); M3
> `CarryDistribution`/`DirectionalDispersion` are legacy/deterministic
> compatibility representations, specifically still authoritative for
> `Club.expected_carry_metres` and current `strategy.recommend_club()`
> during the M3->M4 transition. The two representations are **not expected
> to remain synchronized automatically** — no code keeps them in sync, and
> none should be added to. Separately, `PlayerShotDistribution` is now a
> frozen (immutable) Pydantic value object (`model_config =
> ConfigDict(frozen=True)`), which structurally prevents in-place mutation
> of a stored baseline — this does not prevent wholesale reassignment of
> `Club.shot_distribution` itself, which remains a normal mutable field,
> reassigned only at onboarding/re-onboarding time via
> `compose_club_shot_distribution`'s caller.
>
> **Flagged, not solved, limitation:** `Club.name`/`ShotRecord.club_name`
> remain plain strings with no uniqueness constraint across a `Player`'s
> bag (mirroring the existing `ShotRecord.club_name`-not-cross-validated
> note above). Both `compose_club_shot_distribution` and
> `resolve_current_shot_distribution` therefore take a specific `Club`
> object / `club_name` directly, not a `Player` plus a name to look up — no
> `Player`-level name-lookup convenience function is added, and no
> duplicate-club-name disambiguation policy is introduced by this issue
> (see `docs/backlog.md`). No ADR was required (additive, defaulted field;
> no new dependency; no ownership/dependency-direction change; no
> `PopulationPrior` replaceability-contract change) — ADR 0006 already
> names this composition as its deferred M4.6 consequence; see
> [docs/plans/m4.6-compose-shot-distribution.plan.md](plans/m4.6-compose-shot-distribution.plan.md).

## Purpose

Represent a player's clubs, ability, and shot statistics so the strategy
engine can reason about what a specific player is likely to achieve with a
given shot.

## Owner

Player Engineer (see `.github/agents/player-engineer.agent.md`).

## Planned responsibilities

- **Player** domain model: identity, skill level, and owned clubs.
- **Club** domain model: club identifier/type and its carry distribution.
- **Carry distribution**: statistical model of distance (metres) achieved
  with a club, including variance — feeds the population/personalisation
  model and shot-outcome simulation in M4.0/M4 (see
  [roadmap.md](roadmap.md)).
- **Directional dispersion** (implemented as `DirectionalDispersion`):
  lateral/directional bias and spread for a club/player combination.
  Adopts a fixed sign convention for `lateral_bias_metres`: negative is
  left of the intended target line, zero is on-line with the intended
  target, and positive is right of the intended target line — independent
  of player handedness.
- **Performance history**: historical shot/round data feeding into
  statistical estimates (data model only at this stage — no storage
  technology selected; storage design is deferred to M6, see
  `decision-journal.md`).
- **Round statistics**: aggregate stats derived from a player's rounds
  (e.g. average proximity to target by club/distance band).

## Explicit non-goals

- No course geometry or GeoJSON parsing — that is the Course Engineer's
  responsibility.
- No caddie natural-language generation — that is the future `llm`
  subsystem's responsibility.
- No dependency on `course`, `strategy`, `simulation`, `llm`, `api`, or `cli`.

Reading a player's profile and club performance model is active-round core
functionality (`AGENTS.md` §2.2): it must work from locally available data,
with no network request on the critical path. Any future profile
synchronisation across devices is connectivity-enhanced, not a prerequisite
for in-round access — see
[ADR 0005](adr/0005-offline-first-active-round-architecture.md).

## Statistical approach (planned)

Carry and dispersion models will be represented as parametric distributions
(e.g. mean/variance, or empirical samples) computed with NumPy. Any
stochastic sampling introduced here (or consumed by `simulation`) must accept
an explicit random seed and be reproducible in tests, per
`.github/instructions/tests.instructions.md`.

## Units

All distances are in metres internally, consistent with `AGENTS.md` §5.
