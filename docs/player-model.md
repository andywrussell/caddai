# Player model

> Status: a minimal M1 vertical slice now exists —
> [src/caddai/player/models.py](../src/caddai/player/models.py) defines
> `Player` and, as of M3.3,
> `Club` composed of a `CarryDistribution` and `DirectionalDispersion`
> (both from `caddai.statistics`) rather than a bare scalar.
> `Club.expected_carry_metres` is now a computed field derived from
> `carry_distribution.mean_metres`; `Club.with_expected_carry(...)` builds a
> placeholder/degenerate (zero-variance, zero-bias) `Club` from a bare
> expected-carry scalar for callers without a measured distribution yet. As
> of M3.1,
> [src/caddai/statistics/models.py](../src/caddai/statistics/models.py)
> defines `CarryDistribution` (mean + stddev, metres) as a leaf subsystem
> with no dependency on other `caddai.*` modules. As of M3.2, the same file
> also defines `DirectionalDispersion` (lateral stddev + signed lateral
> bias, metres). As of M3.4, `Club` requires a `category: ClubCategory`
> field (`DRIVER`, `FAIRWAY_WOOD`, `HYBRID`, `IRON`, `WEDGE`, `PUTTER`,
> `OTHER`); it is metadata only — no strategy behaviour depends on it yet
> (see issue #29). As of M3.5, `Player.shot_history` is a
> `list[ShotRecord]` (defaulting to an empty list) of manually entered,
> observed shot outcomes — each a `club_name` snapshot (plain string, not
> an embedded `Club`), `achieved_carry_metres` (`ge=0`, so a
> whiffed/topped shot is representable), `lateral_offset_metres` (same
> sign convention as `DirectionalDispersion.lateral_bias_metres`), and
> optional free-text `notes`. This is in-memory only — no persistence/
> storage technology is introduced, and no derivation/fitting of
> `CarryDistribution` or `DirectionalDispersion` from `shot_history` exists
> yet; that is deferred to a future round-history/learning milestone (see
> `docs/backlog.md`). Round statistics below remain **planned**.

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
