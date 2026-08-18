# Strategy engine

> Status: a minimal M1 vertical slice now exists —
> [src/caddai/strategy/models.py](../src/caddai/strategy/models.py) and
> [src/caddai/strategy/recommend.py](../src/caddai/strategy/recommend.py)
> implement a deliberately primitive closest-expected-carry club selection
> with placeholder wind/lie adjustment constants, proving the end-to-end
> architecture. The real expected-value/Monte Carlo model described below
> remains **planned** for milestones M4–M5; `src/caddai/simulation/` does not
> exist yet.
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
phrase it in natural language (M8+).

## Planned responsibilities

### `simulation` (M4)

- Generate shot candidates (club + target combinations) for a given
  situation (position, hole geometry, conditions).
- Run seeded Monte Carlo simulation of shot outcomes using the player's
  carry/dispersion model (from `player`/`statistics`) against course
  geometry (from `course`) and conditions (wind, elevation).
- Produce a distribution of simulated outcomes (resulting position, lie,
  and any hazard/penalty incurred) per shot candidate.

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

## Reproducibility

Every stochastic component (candidate sampling, Monte Carlo outcome
simulation) must accept an explicit random seed. Tests must fix seeds so
strategy decisions are reproducible and regression-testable, per
`.github/instructions/tests.instructions.md`.

## Units

All distances are in metres internally; wind speed in metres per second;
elevation change in metres. Consistent with `AGENTS.md` §5.
