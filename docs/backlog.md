# Backlog

> Status: candidate work items and open questions beyond the current
> milestone. Not a commitment or a schedule — see [roadmap.md](roadmap.md)
> for sequencing. Items move here when identified but not yet scheduled.

## Candidate items

- A severe-miss mixture component for `PlayerShotDistribution` (an
  explicit core-shot + severe-miss two-part model) — deliberately not
  part of M4; the M4.0 research spike found public evidence does not
  currently support estimating a defensible miss probability/severity by
  handicap × club. Revisit once CaddAI has its own calibration data. See
  [docs/research/m4-probabilistic-golfer-model.md](research/m4-probabilistic-golfer-model.md)'s
  "Explicitly deferred, not M4" section and
  [ADR 0006](adr/0006-player-shot-distribution-bivariate-student-t.md)'s
  "Alternatives considered".
- A lateral-skew parameter for `PlayerShotDistribution` — exploratory
  public data shows visible lateral skew, but magnitude by handicap/club
  is not established; deferred out of M4 pending calibration data. See
  [docs/research/m4-probabilistic-golfer-model.md](research/m4-probabilistic-golfer-model.md).
- Lie-specific (rough/slope/bunker) numeric effect multipliers on carry/
  lateral outcome and dispersion — deferred out of M4; the current
  `PopulationPrior`/`PlayerShotDistribution`/environment-transform models
  have no lie-conditional behaviour. See
  [docs/research/m4-probabilistic-golfer-model.md](research/m4-probabilistic-golfer-model.md).
- A learned/ML population-prior model, replacing the M4.2 config-table
  `PopulationPrior` implementation behind the same
  [ADR 0007](adr/0007-population-prior-replaceability.md) interface, once
  CaddAI has enough first-party calibration/round data to justify it — no
  distributional-modelling/ML dependency is approved for this yet (new
  runtime dependency requiring its own ADR and human approval,
  `AGENTS.md` §9).
- A handicap × club repeated-shot calibration data-collection effort (a
  research/data activity, not code) to replace the "unresolved evidence
  gaps" the M4.0 research spike identified — the specific provisional
  numeric parameters this would inform live in
  [src/caddai/statistics/population_prior_config.py](../src/caddai/statistics/population_prior_config.py)
  (`m4.2-provisional-v1`),
  [src/caddai/player/onboarding.py](../src/caddai/player/onboarding.py)
  (`m4.3-provisional-v2`),
  [src/caddai/statistics/personalisation.py](../src/caddai/statistics/personalisation.py)/
  [src/caddai/player/personalisation.py](../src/caddai/player/personalisation.py)
  (`m4.5-provisional-v1`), and
  [src/caddai/simulation/environment_config.py](../src/caddai/simulation/environment_config.py)
  (`m4.7-provisional-v1`). See
  [docs/research/m4-probabilistic-golfer-model.md](research/m4-probabilistic-golfer-model.md)'s
  "Unresolved evidence/calibration gaps" section.
- A generic psychological-pressure penalty for shot dispersion —
  **rejected, not merely deferred**: the M4.0 research spike found
  controlled/observational studies disagree on direction and individual
  golfer response varies, so no defensible generic penalty exists absent
  new evidence. Revisit only if CaddAI's own data supports a specific,
  defensible effect.
- Unify `strategy.Wind`/`strategy.LieType` and `simulation.WindComponents`/
  `simulation.EnvironmentInput` into a single neutral shared-domain
  representation — `strategy/models.py` defined `Wind`/`LieType` in M1
  before `simulation` existed to own them; `simulation` (M4.7) has since
  defined its own overlapping `WindComponents`/`EnvironmentInput` types.
  Not resolved in M4 (no consumer forces the merge yet); flagged as a
  forward pointer since M1 — see
  [docs/plans/m1-core-domain-vertical-slice.plan.md](plans/m1-core-domain-vertical-slice.plan.md)
  and [docs/strategy-engine.md](strategy-engine.md).
- A dedicated putting-shot probabilistic model for `ClubCategory.PUTTER`,
  distinct from the stock full-swing `PopulationPrior`/
  `population_prior_config.py` table — putting is a behaviourally distinct
  shot regime per docs/research/m4-probabilistic-golfer-model.md's scope
  assumptions and must not be pooled with full-swing carry/lateral
  dispersion. `resolve_population_prior` currently raises
  `PopulationPriorUnsupportedCategoryError` with
  `status=ClubCategorySupportStatus.DEFERRED` for `PUTTER` pending this
  work; likely needs its own representation (e.g. green-side distance/line
  model, not carry/lateral Student-t) and probably its own research spike
  before a config table or ADR is warranted.
- Derive/fit `CarryDistribution`/`DirectionalDispersion` from historical
  `ShotRecord` samples (deferred out of M3 — see #9/#30; M3 uses only
  manually supplied statistical parameters; likely lands around the
  round-history/learning milestone, M8+).
- A more stable club-identity mechanism for `ShotRecord`, if plain
  `club_name` string snapshots prove insufficient (e.g. a club is renamed
  or replaced in a player's bag, silently orphaning historical shot
  records with no referential integrity check today — see
  `docs/player-model.md`). Research/non-committed; feeds a future
  round-history milestone if it becomes a real problem in practice.
- Player-level strategic tendencies (risk preference, aggressiveness) as a
  distinct model, beyond club-level carry distribution/dispersion/bias
  (deferred out of M3; belongs to later strategy/player-preference work).
- Decide the expected-strokes model / baseline data source used by
  `strategy` (feeds M5, after its evidence/research spike and decision gate;
  likely needs an ADR if it requires external strokes-gained reference
  data).
- The M5.0 research spike
  ([docs/research/m5-golf-state-expected-strokes.md](research/m5-golf-state-expected-strokes.md))
  ends in two explicit `DECISION REQUIRED` blocks the human must resolve
  before any M5 implementation issue is opened: (1) `GolfState` ownership
  (a new neutral `caddai.golf_state` module, per the spike's
  recommendation, vs. folding it into `simulation` or `strategy`) and the
  course-relative classification operation's home; (2) the expected-
  strokes/state-value architecture — a follow-up amendment performed live
  verified web research and found the distance/lie/ability-conditioned
  expected-strokes CONCEPT well-supported (Broadie 2008/2011, Golfmetrics,
  Arccos, Shot Scope) but no legally reusable public numeric baseline
  table; a second amendment then separated the value contract into a
  neutral benchmark (`E_base`, Layer B), a player-specific adjustment
  (`Delta`, Layer C), and strategic risk (Layer D, later strategy/M8
  work), recommending a neutral `baseline_expected_strokes(state)`
  function for V0 (Architecture Option C) and a two-function
  `E_base`/`Delta` composition (Architecture Option B) as the long-term
  target — not an approved V0 either way. A separate, still-unresolved
  follow-on item tracks the `E_base` numeric-baseline/data-source
  decision itself (see the research document's `FOLLOW-ON REQUIRED`
  block); `Delta`'s own numeric/model content is a further, later,
  unscheduled follow-on.
- Course-geometry gaps the M5.0 spike identified as needed (not built by
  the spike) before course-relative classification can be implemented: a
  `ROUGH` `FeatureType` (today's `FeatureType` enum has no rough
  category at all), a generic penalty-area `FeatureType` distinct from
  `WATER`, and a point-in-polygon containment query against
  `Feature.boundary` (no such primitive exists in `course/distance.py`
  today, though Shapely — already an approved dependency — can supply it
  directly). See
  [docs/research/m5-golf-state-expected-strokes.md](research/m5-golf-state-expected-strokes.md)'s
  "Current-state audit" section.
- Decide the production runtime / possible Rust core, mobile/core runtime
  boundary, cross-language contracts, logical component boundaries,
  repository architecture, CI/CD architecture, release/version
  compatibility model, the future multi-repo agentic-development workflow,
  and any cross-repo security/permissions model (feeds M6; each remains
  its own future ADR/human-approval decision — M6 decides and proves
  these, it does not implement the full future platform).
- Decide a commercial/legitimate offline course-data provider and package
  format (feeds M7; requires human decision on the provider; no provider is
  selected today).
- Decide the decision-journal storage technology (feeds M8; requires ADR +
  human approval — database selection is an escalation trigger).
- Decide the target mobile/GPS platform and integration approach (feeds
  M10; requires human decision).
- Decide the LLM provider and integration approach for the explanation layer
  (feeds M12; requires human approval — LLM provider selection is an
  escalation trigger).
- Investigate on-device inference feasibility for the M12 explanation layer
  (feeds M13; research only, not committed scope).
- Decide the target mobile devices/OS versions for the M11 real-round
  validation (feeds M11; no dedicated hardware, reuses M10's
  platform decision).
- Decide whether/which hardware/sensor inputs (camera lie assessment, GNSS,
  IMU, compass, barometer, microphone) warrant dedicated hardware (feeds
  M14; research only — not committed scope until M11 real-round validation
  is complete; a concrete hardware/sensor adapter design requires a future
  ADR per `AGENTS.md` §13).
- Decide the payment/billing mechanism (if any) for optional paid rounds,
  prepaid usage credits, or premium cloud features (feeds the subscription-
  independent core principle in [docs/prd.md](prd.md); requires ADR + human
  approval — new paid/cloud service selection is an escalation trigger).
- Add regression test coverage for a line-of-play exactly overlapping a
  polygon boundary edge in `caddai.course.distance` (feeds M2 follow-up).
- Add regression test coverage directly targeting `caddai.course.distance`'s
  `1e-6` m Shapely precision-snap boundary itself (feeds M2 follow-up).
- Add an `observed_carry_lateral_metres` counterpart to `ShotRecord` for
  launch-monitor-style lateral offset *at carry landing* (distinct from
  `lateral_offset_metres`, which is now the lateral offset at final
  resting position) — deferred out of M4.4 (issue #52) pending an actual
  launch-monitor integration. See
  [docs/plans/m4.4-shotrecord-provenance-quality.plan.md](plans/m4.4-shotrecord-provenance-quality.plan.md).
- A future carry-from-downrange-distance estimator (using club, shot
  regime, rollout, landing surface, ground firmness/wetness, wind,
  elevation, and other environmental conditions) that reads `ShotRecord.
  final_downrange_metres` and produces a distinct, uncertainty/provenance-
  tagged *estimated* carry — must never be confused with, or written back
  into, `ShotRecord.observed_carry_metres` — deferred out of M4.4 (issue
  #52); this is the "context-aware inference" step of the learning
  pipeline the Architect described in that issue's round-2 review.
- An "attempted but rejected/discarded measurement" concept for
  `ShotRecord` (e.g. a carry reading was attempted but not trusted enough
  to keep) — distinct from `observed_carry_metres` simply being absent —
  identified as a possible future extension during M4.4 (issue #52)'s
  round-2 Architect review; not built unless a real consumer needs it.
- A player-domain lie/context type for `ShotRecord` (e.g. fairway, rough,
  bunker, recovery) — deferred out of M4.4 (issue #52), no consumer yet.
  Must **not** import `caddai.strategy.LieType` (dependency direction:
  `player` may not depend on `strategy`); open question is whether a shared
  neutral lie type should live in a subsystem-neutral module and be reused
  by both, or whether `player` should define its own duplicate enum. See
  [docs/plans/m4.4-shotrecord-provenance-quality.plan.md](plans/m4.4-shotrecord-provenance-quality.plan.md).
- A penalty/out-of-bounds/lost-ball outcome flag on `ShotRecord` — deferred
  out of M4.4 (issue #52), no consumer yet. See
  [docs/plans/m4.4-shotrecord-provenance-quality.plan.md](plans/m4.4-shotrecord-provenance-quality.plan.md).
- Intended-shot-type/target-line context on `ShotRecord` (e.g. intended shot
  shape, target line, distinct from the achieved outcome) — deferred out of
  M4.4 (issue #52), no consumer yet. See
  [docs/plans/m4.4-shotrecord-provenance-quality.plan.md](plans/m4.4-shotrecord-provenance-quality.plan.md).
- Decide the offline synthetic validation harness's repository/component
  ownership (a separate `caddai-sim` repository, part of a future
  `caddai-evals` repository, or another clearly separated component), its
  CI/DevOps placement, and its future role as a cross-repository
  integration gate, at the M9 field-readiness validation gate (see
  [roadmap.md](roadmap.md) M9), informed by M6's repository-architecture
  decision point if a split occurs.
- Full analytics/calibration tooling and dashboards beyond M9/M10's MVP
  local event-capture and issue-reporting level (post-MVP; see
  [decision-journal.md](decision-journal.md#intended-uses) for the
  candidate MVP evaluation scorecard).
- The static Course Handicap/Playing Handicap arithmetic could in principle
  be implemented as soon as M5/M7's player/tee data exists, ahead of M8's
  round-progress-sensitive WHS scoring policy — not split out today since
  it is one coherent objective layer with M8 (see [roadmap.md](roadmap.md)
  M8); revisit only if a real consumer needs the arithmetic before M8
  lands.
- The post-M4 roadmap reassessment
  ([docs/plans/post-m4-roadmap-reassessment.plan.md](plans/post-m4-roadmap-reassessment.plan.md))
  that produced the current M5–M14 structure is now resolved and merged
  into [roadmap.md](roadmap.md); no further reassessment action is pending
  here.

## Process

- The Orchestrator adds items here when work is identified as valuable but
  out of scope for the current task, per
  `docs/development-workflow.md`.
- Items are promoted out of the backlog into a `docs/plans/` implementation
  plan only when a human confirms the milestone should start.
