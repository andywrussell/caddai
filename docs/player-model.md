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
