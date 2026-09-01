# Strategy engine

> Status: a minimal M1 vertical slice now exists —
> [src/caddai/strategy/models.py](../src/caddai/strategy/models.py) and
> [src/caddai/strategy/recommend.py](../src/caddai/strategy/recommend.py)
> implement a deliberately primitive closest-expected-carry club selection
> with placeholder wind/lie adjustment constants, proving the end-to-end
> architecture. `src/caddai/simulation/` now exists: a deterministic
> wind/elevation/air-density environment transform (M4.7, issue #55) and
> seeded bivariate Student-t intrinsic shot-outcome sampling (M4.8, issue
> #56, `sample_bivariate_student_t_shot_outcomes`) are implemented — see
> the `simulation` responsibilities below. **M4 `simulation` is complete**
> for its defined scope (M4.7 environment transform, M4.8 seeded sampling);
> course-relative mapping, expected-strokes/Strokes Gained, and risk/reward
> club/target selection described below remain **planned** for M5+ — see
> [roadmap.md](roadmap.md).
>
> M4/M5 boundary: M4 produces probabilistic landing/carry-space shot
> outcomes only. It does **not** produce final resting position,
> terrain/bounce/rollout, fairway/rough/bunker/green/water/OB
> classification, resulting golf state, expected strokes, Strokes Gained,
> candidate-shot strategy value, WHS-aware strategy, round state/decision
> journal, a synthetic full-round validation harness, mobile application,
> or cloud behaviour — all of that is M5+ (see the M5 parent GitHub issue
> #11, which already records course-relative outcome mapping as an
> explicit M5 prerequisite dependency, and [roadmap.md](roadmap.md)'s M5
> entry). This boundary is also distinct from a future *inverse* problem
> (final observed endpoint → infer latent landing/carry → environment/
> terrain inversion), which M4 does not attempt to solve and which must
> remain architecturally separate from this forward simulator — see
> [docs/backlog.md](backlog.md)'s carry-from-downrange-distance estimator
> item.
>
> Forward pointer: `Wind`/`LieType` are defined in `strategy/models.py` for
> M1 because no `course`/`gps`/`simulation` package exists yet to own them.
> They may move to a neutral shared-domain module once `course` (M2) or
> `simulation` (M4) land — see
> [docs/plans/m1-core-domain-vertical-slice.plan.md](plans/m1-core-domain-vertical-slice.plan.md).
>
> A developer demo script, `src/caddai/strategy/demo.py`, runs
> `recommend_club()` on a fixed scenario for manual inspection
> (`uv run python -m caddai.strategy.demo`).

## Purpose

Deterministically decide what shot a player should play: target, club,
intended shot shape, and risk — the core of CaddAI's value. See
[adr/0001-deterministic-strategy-engine.md](adr/0001-deterministic-strategy-engine.md).

## Owner

Strategy Engineer (see `.github/agents/strategy-engineer.agent.md`).

## CRITICAL constraint

`strategy` and `simulation` must **never** import `llm`, `api`, `cli`, or any
UI package, directly or transitively, and must never call an LLM to make a
golf decision. An LLM may only read a finished `strategy` recommendation to
phrase it in natural language (M11+).

`strategy` and `simulation` are also **active-round core functionality**
(`AGENTS.md` §2.2): they must be able to produce a recommendation using only
locally available course/player/statistics data, with no network request on
the critical path. Neither module may take on a mandatory network dependency
(e.g. a remote scoring/reference service) for the recommendation path — see
[ADR 0005](adr/0005-offline-first-active-round-architecture.md).

## Planned responsibilities

### `simulation` (M4, following the M4.0 research/architecture spike)

- Consume a `player`/`statistics`-owned probabilistic representation of the
  shots a golfer is likely to produce — an evidence-based population model
  personalised from onboarding information and, over time, observed
  `ShotRecord` data (see [player-model.md](player-model.md) and
  [roadmap.md](roadmap.md) M4.0/M4) — rather than assuming arbitrary generic
  dispersion parameters. **Implemented (M4.8, issue #56):**
  `sample_bivariate_student_t_shot_outcomes` in
  `src/caddai/simulation/sampling.py` draws seeded, vectorised intrinsic
  `ShotOutcome`s from a `caddai.statistics.PlayerShotDistribution` per ADR
  0006's bivariate Student-t construction, exposed behind a
  `ShotOutcomeSampler` `Protocol` so a future alternate technique can be
  added without changing this contract. It is composable with M4.7's
  `apply_environment_transform` via a plain caller-side loop.
- Generate shot candidates (club + target combinations) for a given
  situation (position, hole geometry, conditions) — **still M5+**.
- Run seeded outcome simulation against course geometry (from `course`) and
  conditions (lie, wind, elevation), transforming the player's shot
  distribution into a resulting outcome distribution. Monte Carlo is an
  acceptable initial sampling technique but must not be the only supported
  one, and must not lock the model to a single probability distribution.
  **Implemented so far:** intrinsic outcome sampling (M4.8) and the
  environment/physics transform (M4.7); course-geometry-relative mapping
  is **still M5+**.
- Produce a distribution of simulated outcomes (resulting position, lie,
  and any hazard/penalty incurred) per shot candidate — **still M5+**:
  course-relative mapping, expected strokes, Strokes Gained, and
  risk/reward strategy selection are not implemented yet.

### `strategy` (M5)

- Evaluate each shot candidate's simulated outcomes to estimate expected
  strokes-to-holed (or another comparable objective).
- Select the club/target combination that best balances expected strokes and
  risk, per the player's demonstrated ability.
- Assemble a structured **recommendation**: target, club, intended shot
  shape, risk assessment, and the rationale (which inputs drove the
  decision) — see `docs/domain-model.md`.

## Explicit non-goals

- No course geometry parsing (Course Engineer) or player/statistics
  modelling (Player Engineer) — `strategy`/`simulation` consume those
  subsystems' outputs, they don't implement them.
- No natural-language generation.
- No API/CLI adapter logic.
- No Rules-of-Golf/competition-mode policy — `simulation` only computes the
  effect of environmental inputs *if* applied; whether a round permits
  environmental assistance at all belongs to a future round/rules layer
  (see [roadmap.md](roadmap.md)'s M9 entry).

## Reproducibility

Every stochastic component (candidate sampling, seeded outcome simulation)
must accept an explicit random seed. Tests must fix seeds so strategy
decisions are reproducible and regression-testable, per
`.github/instructions/tests.instructions.md`.

## Units

All distances are in metres internally; wind speed in metres per second;
elevation change in metres. Consistent with `AGENTS.md` §5.
