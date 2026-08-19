# Product Requirements Document (PRD)

> Status: describes intended product scope for the roadmap. Only M0
> (repository bootstrap) is currently implemented — see
> [roadmap.md](roadmap.md) for what exists today versus what's planned.

## 1. Problem statement

Golfers making on-course shot decisions typically have access to distance
(via rangefinder/GPS) but not to a synthesized recommendation that accounts
for their own ability, shot dispersion, hazards, wind, and risk trade-offs.
CaddAI closes that gap with a deterministic recommendation engine.

## 2. Primary user story

> As a golfer standing over a shot, I want a concise recommendation of club
> and target — with the reasoning behind it — so that I can make a better
> strategic decision than guessing from a yardage number alone.

## 3. Functional scope (by roadmap milestone)

See [roadmap.md](roadmap.md) for full milestone detail. At a high level:

- **Core domain model** (M1): represent holes, shots, players, and a simple
  deterministic recommendation for a trivial scenario end-to-end.
- **Course geometry** (M2): local GeoJSON course representation — holes,
  fairways, greens, hazards.
- **Player model** (M3): players, clubs, carry distributions, and shot
  dispersion.
- **Strategy simulation** (M4–M5): candidate shot generation, Monte Carlo
  outcome simulation, expected-strokes-based club/target selection.
- **Round tracking** (M6): a decision journal recording recommendations,
  player choices, and outcomes.
- **Mobile/GPS integration** (M7): live GPS position feeding the engine.
- **Natural-language explanation** (M8): an LLM explains the deterministic
  recommendation in caddie-style language — never generates it.
- **On-device inference research** (M9): exploratory, not committed scope.

## 4. Non-functional requirements

- **Determinism & explainability**: every recommendation must be traceable
  to specific inputs (geometry, statistics, simulation parameters). No
  opaque "the LLM decided" reasoning.
- **Offline-first active round**: network connectivity is optional during an
  active round. Positioning, course geometry access, player profile access,
  distance calculations, shot simulation, strategy/recommendation, and
  recording decisions/outcomes must remain capable of local execution with
  no network request on the critical path. Course-data downloads, profile/
  round-history sync, cloud analytics, weather refresh, and optional
  cloud-based LLM enhancement may use the network but must degrade
  gracefully, never becoming a prerequisite for the active-round path. See
  `AGENTS.md` §2.2 and
  [adr/0005-offline-first-active-round-architecture.md](adr/0005-offline-first-active-round-architecture.md).
- **Units**: SI internally, canonical distance metres; conversion to yards
  only at presentation boundaries.
- **Type safety**: strict typing throughout (mypy strict).
- **Testability**: deterministic algorithms are fully unit-testable;
  stochastic algorithms are seeded and reproducible in tests.
- **Dependency discipline**: only approved libraries (see `AGENTS.md`)
  without an ADR.

## 5. Out of scope for now

- Any production LLM integration (deliberately deferred to M8).
- Cloud services, hosted databases, or paid external APIs (require ADR +
  human approval whenever proposed).
- Swing mechanics, coaching, or biomechanical analysis.
- Course *discovery*/import from third-party providers — early milestones
  use local GeoJSON only.

## 6. Success signals (directional, not committed metrics)

- A recommendation for a simple, well-defined scenario (e.g. a straight
  approach shot with no hazards) is produced deterministically and matches
  reasonable human-caddie judgement.
- The system can explain *why* it chose a club/target in terms of the inputs
  that drove the decision.
- Golf-domain assumptions encoded in `strategy`/`simulation` are traceable to
  a specific doc or ADR, not implicit.

## 7. Open questions (track in `docs/decision-journal.md` / raise via
   `NEEDS_DECISION` when they block implementation)

- What data source(s) will provide real course geometry beyond local
  GeoJSON fixtures? (Deferred — no decision made; do not add a cloud/geo
  service without an ADR. Any such source must support downloading/caching
  course data locally before/between rounds — it must never become a live
  dependency for course geometry access *during* a round; see `AGENTS.md`
  §2.2.)
- What GPS hardware/mobile platform is targeted for M7? (Deferred — see the
  "Runtime & Offline Architecture" research spike, roadmap M5.5, which
  precedes this decision.)
- What LLM provider (if any) will be used for M8, and how are costs/privacy
  handled? (Deferred — requires explicit human approval; see escalation
  rules in `AGENTS.md`. Whatever is chosen, the deterministic recommendation
  must remain fully available without it — cloud LLM unreachability degrades
  to the structured recommendation, never to no recommendation.)
