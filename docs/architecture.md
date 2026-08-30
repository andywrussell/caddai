# Architecture

> Status: describes intended target architecture for the full roadmap.
> Implemented so far: `gps`/`course` (M2, complete — see
> [course-engine.md](course-engine.md)) and `player`/`statistics` (M3,
> complete — see [player-model.md](player-model.md)). `simulation` has been
> bootstrapped with a deterministic wind/elevation/air-density environment
> transform (M4.7, issue #55) and seeded bivariate Student-t intrinsic
> shot-outcome sampling (M4.8, issue #56,
> `sample_bivariate_student_t_shot_outcomes`) — course-relative mapping,
> expected strokes/Strokes Gained, and risk/reward strategy selection
> remain future work (M5+). `llm`, `api`, and `cli` do not exist yet.

## Guiding principle

CaddAI is a **deterministic decision engine** with optional natural-language
explanation layered on top, never the reverse. See
[adr/0001-deterministic-strategy-engine.md](adr/0001-deterministic-strategy-engine.md).

CaddAI is also **offline-first for an active round**: network connectivity
is optional while a round is in progress. See
[Offline-first active round](#offline-first-active-round) below and
[adr/0005-offline-first-active-round-architecture.md](adr/0005-offline-first-active-round-architecture.md).

## System diagram (target end-state)

```mermaid
graph TD
    UI[Mobile / GPS UI] --> API
    CLI[Typer CLI] --> STRAT
    API[FastAPI adapter] --> STRAT[strategy]
    STRAT --> SIM[simulation]
    STRAT --> COURSE[course]
    STRAT --> PLAYER[player]
    STRAT --> STATS[statistics]
    SIM --> COURSE
    SIM --> PLAYER
    SIM --> STATS
    PLAYER --> STATS
    COURSE --> GPS[gps]
    LLM[llm] -.explains output of.-> STRAT
    API -.optional.-> LLM
```

Dashed edges: `llm` only ever *reads* a finished recommendation to phrase it
in natural language. It is never on the decision path, and `strategy`/
`simulation` never import it.

This diagram shows the **module dependency graph**, not a deployment
topology. `UI --> API` and `CLI --> STRAT` must not be read as implying `api`
is necessarily a remote network service: for the active-round path, `api`
(or `cli`) may run co-located with, or embedded in, the device performing
the round — see [Offline-first active round](#offline-first-active-round).
Whether/where a network boundary exists in the deployed system is a roadmap
M7 (GPS/mobile integration) decision, not something this diagram settles.

## Offline-first active round

CaddAI must remain usable for its core value proposition — a shot
recommendation — with no network connectivity during a round. This is
recorded in
[adr/0005-offline-first-active-round-architecture.md](adr/0005-offline-first-active-round-architecture.md)
and is a standing constraint, complementary to (not a replacement for) the
deterministic-strategy principle above: that ADR governs *who* decides;
this constraint governs *what network reachability may be assumed*.

**Active-round core functionality** (must remain capable of running with
only locally available device compute, storage, and data, with no network
request on the critical path):

1. Positioning/location acquisition.
2. Course geometry access.
3. Player profile access.
4. Distance calculations.
5. Shot simulation.
6. Strategy/recommendation.
7. Recording player decisions and shot outcomes.

**Connectivity-enhanced functionality** (may use the network and may
degrade gracefully offline, but must never be a prerequisite for the above):
course-data download/updates before a round, player-profile/round-history/
cross-device synchronisation, cloud analytics, account management, weather
refresh, model/software updates, optional cloud-based LLM enhancement, and
optional cloud-based player-model training. If a future LLM explanation
layer (M8) is unreachable, the system degrades to the structured
deterministic recommendation rather than withholding one.

No storage technology, mobile runtime, or infrastructure component is
selected by this constraint — those are future decisions, informed by the
"Runtime & Offline Architecture" research spike (roadmap M5.5; see
[roadmap.md](roadmap.md)) that precedes committing to the full mobile
runtime architecture (roadmap M7).

Recording a decision/outcome locally (item 7 above) is distinct from
*deriving* operational or recommendation-evaluation analytics from that
record (see [decision-journal.md](decision-journal.md)): the former is
active-round core functionality; the latter is connectivity-enhanced and
may live in a separate component entirely — this diagram does not assume
they share a service, repository, or storage technology.

## Subsystems

| Subsystem | Path | Responsibility |
|---|---|---|
| Course | `src/caddai/course/` | Hole/course geometry, hazards, GeoJSON representation |
| GPS | `src/caddai/gps/` | Coordinates, bearings, GPS distance calculations |
| Player | `src/caddai/player/` | Player and club domain models, tendencies |
| Statistics | `src/caddai/statistics/` | Carry distributions, dispersion, round statistics, the `ClubCategory` taxonomy, and the `PopulationPrior` contract/config |
| Strategy | `src/caddai/strategy/` | Shot candidates, club/target selection, risk, expected strokes, Strokes Gained |
| Simulation | `src/caddai/simulation/` | Deterministic wind/elevation/air-density environment transform of a forward-modelled shot outcome (M4.7); seeded bivariate Student-t intrinsic shot-outcome sampling composed with `player`'s shot distribution (M4.8); course-relative mapping, expected strokes/Strokes Gained, and risk/reward strategy are future work (M5+) |
| LLM | `src/caddai/llm/` | Natural-language explanation of a finished recommendation (M8+) |
| API | `src/caddai/api/` | FastAPI adapter; translates HTTP ↔ domain calls, no business logic |
| CLI | `src/caddai/cli/` | Typer adapter; translates CLI ↔ domain calls, no business logic |

Modules are created when their owning milestone is implemented, not
pre-scaffolded as empty placeholders (see `AGENTS.md` §3).

## Dependency direction

- Adapters (`api`, `cli`, `llm`) depend inward on domain/decision layers.
  Domain/decision layers never depend on adapters.
- `strategy` and `simulation` depend only on `course`, `player`, `statistics`,
  and shared domain types — **never** on `llm`, `api`, `cli`, or UI code,
  directly or transitively. This is enforced by convention and by
  architecture-invariant tests (see
  `.github/instructions/tests.instructions.md`).
- `course`/`gps` and `player`/`statistics` are siblings: neither depends on
  the other. Shared concepts (e.g. a point-in-space type used by both) live
  in a neutral shared-domain module, not duplicated or cross-imported.

## Future hardware/sensor adapters

Roadmap M11 (see [roadmap.md](roadmap.md)) explores dedicated CaddAI
hardware and on-device sensing (camera-based lie assessment, GNSS, IMU,
compass, barometer, other environmental sensors, microphone/voice) as
research only, not committed scope, and not before roadmap M10 validates
the mobile software prototype in real rounds. Architecturally, any such
hardware/sensor input system is just another adapter, subject to the same
rule as `api`/`cli`/`llm`: it must produce canonical domain inputs already
defined in [domain-model.md](domain-model.md) — e.g. camera/manual input ->
`Lie`, GNSS -> `Position`, barometer/course data -> elevation,
weather/manual/sensor -> `Wind` — and must never itself contain golf
strategy logic. `strategy`/`simulation` remain the sole source of golf
decisions ([ADR 0001](adr/0001-deterministic-strategy-engine.md)). A
concrete hardware/sensor adapter design (real module boundaries, not
research) is the trigger for a future ADR, or an amendment to ADR 0001
naming this adapter category explicitly, per `AGENTS.md` §13.

## Synthetic validation harness (future)

Roadmap M5.5 (see [roadmap.md](roadmap.md)) records a future requirement for
an offline synthetic round/scenario validation harness that exercises
`strategy`/`simulation` at scale before broad mobile/field testing. This
harness is not a subsystem and not a new decision path: it is a test-time
*caller* of `strategy`/`simulation`'s existing public interface, in the same
dependency-direction position as `api`/`cli` — it depends inward on
`strategy`/`simulation`, never the reverse, and `strategy`/`simulation` must
never import or become aware of it. Whatever "stable contract" the harness
ultimately calls through (today's Python module surface, a later formal
interface, or a post-Rust-migration binding/CLI boundary) is not decided
here. The harness must invoke the real production engine and must never
duplicate or reimplement `strategy`/`simulation` decision logic — this is
[ADR 0001](adr/0001-deterministic-strategy-engine.md)'s testability
rationale applied at scale, not a change to it. It is also distinct from the
operational-monitoring/recommendation-evaluation architecture described in
[decision-journal.md](decision-journal.md#monitoring-vs-evaluation): the
harness is a controlled, reproducible, high-volume, synthetic-data
capability, while monitoring/evaluation concerns real golfers, real
execution, and real conditions — synthetic run data must not flow into
production telemetry by default. No repository/component ownership,
interface technology, or CI placement is decided by this section.

## Module ownership

See `AGENTS.md` §4 and the [development-workflow.md](development-workflow.md)
for how ownership maps to the agent team.

## API contracts

Not yet defined — no `api`/`cli` module exists. When first introduced, the
contract will be documented here and any breaking change to it afterward
requires an ADR (see `AGENTS.md` §13).

## Units

SI internally; canonical distance is metres. See `AGENTS.md` §5.

## Architectural decisions

Recorded under [adr/](adr/). Start with
[0001-deterministic-strategy-engine.md](adr/0001-deterministic-strategy-engine.md).
