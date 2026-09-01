# 0005. Offline-first active-round architecture

## Status

Accepted

## Context

CaddAI's target usage moment is a golfer standing over a shot, mid-round, on
a golf course — an environment where cellular/Wi-Fi connectivity is
frequently weak, absent, or intentionally avoided (many courses have poor
signal in low-lying holes or tree cover; some clubs restrict connectivity).
[docs/vision.md](../vision.md) states CaddAI's core value is a deterministic,
explainable decision the golfer can trust on every shot, not an occasional
best-effort one.

[ADR 0001](0001-deterministic-strategy-engine.md) already establishes *who*
produces a recommendation (deterministic `strategy`/`simulation` code, never
an LLM). It does not address a separate, equally important question: *what
network reachability may the system assume* while a round is in progress?
Without an explicit constraint, it would be architecturally easy — and, for
a naive client/server split, even the default — to design the system so that
every shot recommendation requires a round-trip to a remote service. That
would make the product materially less useful (or entirely unusable) exactly
when a golfer needs it: mid-round, on course, wherever signal happens to be
poor that day.

The planned system diagram in [docs/architecture.md](../architecture.md)
shows `UI --> API --> STRAT`; read literally, with `api` deployed as a
conventional remote FastAPI service, this would make the deterministic
engine unreachable without a network connection. That reading needs to be
foreclosed explicitly before `api`/`cli` adapters, GPS/mobile integration
(roadmap M10), or a decision-journal storage technology (roadmap M8) are
designed, since each of those future decisions must satisfy this constraint
rather than contradict it after the fact.

## Decision

**Network connectivity is optional during an active round. Core golf
decision functionality must remain capable of local execution.**

The following **active-round core functionality** must remain capable of
running with only locally available device compute, storage, and data, with
no network request on the critical path:

1. Positioning/location acquisition (device-accessible GPS).
2. Course geometry access (locally available course data).
3. Player profile access (locally available player/club data).
4. Distance calculations.
5. Shot simulation.
6. Strategy/recommendation (the deterministic engine, per ADR 0001).
7. Recording player decisions and shot outcomes.

No cloud API may be a *mandatory* dependency between the user interface and
any of the above during a round. Concretely: the `api`/`cli` adapter layer
must remain architecturally able to run co-located with (or embedded in) the
device performing the round, rather than requiring a remote server for the
active-round path — this constrains *deployment topology*, not the module
dependency direction already established in `docs/architecture.md` (`api`/
`cli` still depend inward on `strategy`/`simulation`/`course`/`player`, never
the reverse).

The following **connectivity-enhanced functionality** may use the network,
and may degrade gracefully when offline, but must never become a
prerequisite for the active-round path above: course-data download/updates
before a round, player-profile synchronisation, round-history
synchronisation, cross-device sync, cloud analytics, account management,
weather refresh, model/software updates, optional cloud-based LLM
enhancement, and optional cloud-based player-model training.

This is a **complementary, orthogonal** constraint to ADR 0001, not a
change to it: ADR 0001 governs *who* decides (deterministic code, never an
LLM); this ADR governs *what network reachability the active-round path may
assume*. In particular, if a future LLM explanation layer (ADR 0001,
roadmap M12) is unreachable, the system must degrade to the structured
deterministic recommendation (no natural-language phrasing), not withhold a
recommendation. Cloud LLM availability must never determine whether the
golfer receives a recommendation at all.

**Data principle.** Data required during a round should eventually support
local availability, including at minimum: selected course geometry,
relevant course metadata, player profile, club performance model, active
round state, recommendations, player decisions, and shot outcomes. This ADR
does not select a storage technology, mobile runtime, course-package format,
or any cloud/database/infrastructure component — those remain future
decisions (each still individually subject to the ADR/escalation
requirements in `AGENTS.md` §13/§14), informed by the
production system architecture & runtime checkpoint (roadmap M6, see
[docs/roadmap.md](../roadmap.md)) that precedes committing to the full
mobile MVP (roadmap M10).

## Consequences

- Positive: the product remains usable for its core value proposition
  (a trustworthy shot recommendation) regardless of course connectivity,
  which is a materially better golfer experience than a cloud-dependent
  design and removes a single point of failure from the critical path.
- Positive: forces `api`/`cli` to be designed as adapters that *can* run
  on-device, rather than assuming a client/server split by default — this
  is checked earlier (now, as a standing principle) rather than discovered
  as a costly redesign during roadmap M10.
- Positive: gives every future ADR that touches persistence, mobile runtime,
  or LLM integration (M6, M8, M10, M12) an explicit, pre-existing constraint
  to satisfy, rather than requiring each to re-derive it independently.
- Negative: rules out a "thin client, all logic in the cloud" architecture
  as the default deployment shape for the active-round path — a cloud-only
  design would need an explicit ADR superseding this one, with human
  approval, per `AGENTS.md` §14.
- Negative: local execution of `strategy`/`simulation`/`course`/`player`
  on-device (likely mobile) raises open questions about packaging a Python
  core, compute/battery budget, and local persistence — this ADR
  deliberately does not resolve those; it hands them to the M6 production
  system architecture & runtime checkpoint and to whichever future ADR
  each individually triggers.
- Negative/neutral: connectivity-enhanced features (sync, cloud analytics,
  cloud LLM) must be designed to degrade gracefully rather than assuming
  connectivity, which is a small amount of extra design discipline for those
  features but is deferred, not decided, here.

## Alternatives considered

- **Cloud-API-first** (every recommendation requires reaching a remote
  service): rejected — a golf course is exactly the kind of environment
  where connectivity cannot be assumed; this would make the core product
  fail unpredictably in its primary use case.
- **Best-effort hybrid** (fall back to a degraded/simplified recommendation
  when offline, rather than the full deterministic engine): rejected — the
  user's explicit requirement, and this ADR's decision, is that the *same*
  deterministic engine (ADR 0001) runs locally; there is no separate,
  lesser "offline mode" for the core decision itself. Degradation is
  reserved for connectivity-enhanced features (e.g. dropping natural-
  language phrasing), never for the recommendation's correctness.
- **Local-only forever, no synchronisation** (reject network use
  entirely): rejected — cross-device sync, round-history backup, cloud
  analytics, and optional cloud LLM enhancement are valuable and explicitly
  permitted, provided they never become prerequisites for the active-round
  path. This ADR is about optionality of connectivity, not prohibition of
  it.
- **Resolve mobile runtime/storage technology now**: rejected — premature.
  This ADR fixes the constraint those decisions must satisfy; the
  technology choices themselves are deferred to the M6 production system
  architecture & runtime checkpoint and the individual ADRs it will
  likely produce
  (M8 decision-journal storage, M10 mobile runtime, M13 on-device LLM
  feasibility).
