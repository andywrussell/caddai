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
> `achieved_carry_metres`, `lateral_offset_metres`, optional `notes`,
> finite-value validated per issue #43). `ShotRecord.club_name` is a plain
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
