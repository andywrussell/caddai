# Backlog

> Status: candidate work items and open questions beyond the current
> milestone. Not a commitment or a schedule — see [roadmap.md](roadmap.md)
> for sequencing. Items move here when identified but not yet scheduled.

## Candidate items

- Derive/fit `CarryDistribution`/`DirectionalDispersion` (or a future
  `PlayerShotDistribution`) from historical `ShotRecord` samples (deferred
  out of M3 — see #9/#30; M3 uses only manually supplied statistical
  parameters). M4.0 must define the future-compatible personal-learning
  mechanism conceptually (Bayesian updating, hierarchical/empirical Bayes,
  shrinkage, robust incremental statistics) and determine whether actual
  implementation belongs in M4 or a later milestone — see
  [roadmap.md](roadmap.md) M4.0/M4.
- Decide whether M4.0 concludes a higher-level `PlayerShotDistribution`
  abstraction is needed beyond M3's `CarryDistribution`/
  `DirectionalDispersion`; if adopted, it requires an ADR (cross-subsystem
  `player`/`statistics` ↔ `simulation` contract) before M4 implementation
  begins, per Architect review of the M4 roadmap redefinition.
- Decide whether M4's initial probabilistic golfer-model representation
  needs a distributional-modelling library beyond NumPy/Pydantic (e.g.
  `scipy`); if so, this is a new runtime dependency requiring an ADR and
  human approval (`AGENTS.md` §9) before M4 implementation begins.
- Identify and evaluate specific public/legitimately reusable golf-
  performance datasets or published research (R&A/USGA, academic,
  launch-monitor) for M4.0's population model, and record licensing/
  representativeness findings (feeds M4.0 directly; see
  [roadmap.md](roadmap.md)).
- Update GitHub tracking issue #10 (currently titled "M4 — Candidate-shot
  generation and Monte Carlo simulation") to reflect the M4.0/M4 roadmap
  redefinition once this documentation change is merged.
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
  round-history/learning milestone, M6+).
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
  `strategy` (feeds M5; likely needs an ADR if it requires external
  strokes-gained reference data).
- Decide the decision-journal storage technology (feeds M6; requires ADR +
  human approval — database selection is an escalation trigger).
- Decide the target mobile/GPS platform and integration approach (feeds M7;
  requires human decision).
- Decide the LLM provider and integration approach for the explanation layer
  (feeds M8; requires human approval — LLM provider selection is an
  escalation trigger).
- Investigate on-device inference feasibility for the M8 explanation layer
  (feeds M9; research only, not committed scope).
- Decide the target mobile devices/OS versions for the M10 real-round
  validation prototype (feeds M10; no dedicated hardware, reuses M7's
  platform decision).
- Decide whether/which hardware/sensor inputs (camera lie assessment, GNSS,
  IMU, compass, barometer, microphone) warrant dedicated hardware (feeds
  M11; research only — not committed scope until M10 real-round validation
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
- Decide whether `ShotRecord.achieved_carry_metres` should become optional
  and/or a new `achieved_total_metres` field should be added to preserve the
  carry-vs-total distinction — deferred out of M4.4 (issue #52) as a new
  measurement axis, not provenance/quality metadata; the Architect
  identified this as a follow-up during that issue's review. See
  [docs/plans/m4.4-shotrecord-provenance-quality.plan.md](plans/m4.4-shotrecord-provenance-quality.plan.md).
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

## Process

- The Orchestrator adds items here when work is identified as valuable but
  out of scope for the current task, per
  `docs/development-workflow.md`.
- Items are promoted out of the backlog into a `docs/plans/` implementation
  plan only when a human confirms the milestone should start.
