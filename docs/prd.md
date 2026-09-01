# Product Requirements Document (PRD)

> Status: describes intended product scope for the roadmap. Only M0
> (repository bootstrap) is currently implemented — see
> [roadmap.md](roadmap.md) for what exists today versus what's planned. For
> the long-term customer/product vision this scope is derived from, see
> [docs/prfaq.md](prfaq.md); this PRD defines what the product must do at
> each milestone, not the full aspirational experience.

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
- **Probabilistic golfer modelling & shot outcome simulation** (M4.0–M4):
  research/define a defensible probabilistic representation of the shots a
  golfer can produce (evidence-based population model + onboarding
  personalisation + context/environment effects), then candidate shot
  generation and shot-outcome simulation (Monte Carlo as an initial
  sampling technique, not the domain abstraction) against that model.
- **Strategy** (M5): expected-strokes-based club/target selection over the
  outcomes M4 produces.
- **Round tracking** (M8): a decision journal recording recommendations,
  player choices, and outcomes.
- **Mobile/GPS integration** (M10): live GPS position feeding the engine
  — a build/integration milestone, not yet field-proven.
- **Mobile real-round validation** (M11): validate CaddAI on existing
  consumer mobile devices during real rounds, gated by field-readiness
  validation (M9) and the mobile MVP build (M10), before any dedicated
  hardware is designed or any LLM explanation layer is added.
- **Natural-language explanation** (M12): an LLM explains the deterministic
  recommendation in caddie-style language — never generates it —
  deliberately sequenced after real-round validation (M11).
- **On-device inference research** (M13): exploratory, not committed scope.
- **Hardware / on-device intelligence research** (M14): exploratory
  research into dedicated hardware and on-device sensing; not committed
  scope until M11 has validated real-round usability and its actual
  sensor, compute, UX, latency, and battery requirements are understood.

## 4. Product & commercial principles

- **Subscription-independent core.** CaddAI should aim to keep its core
  product (GPS/course access, player/club model, deterministic
  strategy/recommendation) functional without requiring an ongoing
  subscription. Where recurring cloud costs exist (e.g. course-data hosting,
  optional cloud LLM enrichment), they should preferentially be recovered
  through mechanisms such as optional paid rounds, prepaid cloud/caddie
  usage credits, or optional premium cloud features — not by making core
  GPS/strategy functionality itself subscription-dependent. No prices or
  payment infrastructure are decided here; a specific payment/billing
  mechanism is a future decision requiring an ADR and human approval per
  `AGENTS.md` §14 ("adding a cloud service or a paid external service").
- **Cloud LLM is optional enrichment, never a gate.** Per
  [ADR 0001](adr/0001-deterministic-strategy-engine.md) and
  [ADR 0005](adr/0005-offline-first-active-round-architecture.md), any
  cloud-based LLM functionality (M12+) is optional enrichment layered on top
  of the deterministic recommendation. Failure, unreachability, or
  exhaustion of cloud LLM functionality (including any future usage-credit
  exhaustion under the principle above) must never prevent a deterministic
  shot recommendation — the system always degrades to the structured
  recommendation, never to no recommendation.

## 5. Non-functional requirements

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

## 6. Out of scope for now

- Any production LLM integration (deliberately deferred to M12, after
  real-round validation, M11).
- Cloud services, hosted databases, or paid external APIs (require ADR +
  human approval whenever proposed).
- Swing mechanics, coaching, or biomechanical analysis.
- Course *discovery*/import from third-party providers — early milestones
  use local GeoJSON only.

## 7. Success signals (directional, not committed metrics)

- A recommendation for a simple, well-defined scenario (e.g. a straight
  approach shot with no hazards) is produced deterministically and matches
  reasonable human-caddie judgement.
- The system can explain *why* it chose a club/target in terms of the inputs
  that drove the decision.
- Golf-domain assumptions encoded in `strategy`/`simulation` are traceable to
  a specific doc or ADR, not implicit.

## 8. Open questions (track in `docs/decision-journal.md` / raise via
   `NEEDS_DECISION` when they block implementation)

- What data source(s) will provide real course geometry beyond local
  GeoJSON fixtures? (Deferred — no decision made; do not add a cloud/geo
  service without an ADR. Any such source must support downloading/caching
  course data locally before/between rounds — it must never become a live
  dependency for course geometry access *during* a round; see `AGENTS.md`
  §2.2.)
- What GPS hardware/mobile platform is targeted for M10? (Deferred — see the
  production runtime & cross-language architecture checkpoint, roadmap M6,
  which precedes this decision.)
- What LLM provider (if any) will be used for M12, and how are costs/privacy
  handled? (Deferred — requires explicit human approval; see escalation
  rules in `AGENTS.md`. Whatever is chosen, the deterministic recommendation
  must remain fully available without it — cloud LLM unreachability degrades
  to the structured recommendation, never to no recommendation.)
- What, if any, dedicated hardware should CaddAI build? (Deferred — see
  roadmap M14. Must not be committed to until the M11 mobile real-round
  validation has been completed in real rounds and its actual sensor,
  compute, UX, latency, and battery requirements are understood from that
  experience.)
- What payment/billing mechanism (if any) recovers recurring cloud costs
  (optional paid rounds, prepaid usage credits, premium cloud features)?
  (Deferred — no prices or payment infrastructure selected; requires an ADR
  and human approval per `AGENTS.md` §14 before any implementation.)
