# 0007. Population-prior replaceability contract for `PlayerShotDistribution`

## Status

Proposed

## Context

[ADR 0006](0006-player-shot-distribution-bivariate-student-t.md) adopts a
bivariate Student-t `PlayerShotDistribution` as CaddAI's V1 player
shot-production representation. That representation's initial parameters
must come from somewhere before any personal `ShotRecord` history exists:
the M4.0 research spike (issue #47,
[docs/research/m4-probabilistic-golfer-model.md](../research/m4-probabilistic-golfer-model.md))
concludes that public raw golf data is only **partially** sufficient — it
can inform the *shape* of a population prior (e.g. that lower handicap is
associated with lower shot-to-shot variability, particularly evidenced for
driver) but not a defensible, complete numeric surface across
handicap × club-category × dispersion × correlation × tail behaviour. V1
must therefore combine a small, evidence-derived and explicitly provisional
parameter set (config/lookup-table-backed) with onboarding information and,
over time, CaddAI's own calibration data and observed `ShotRecord` history.

`AGENTS.md` §2.1 requires the deterministic engine (`strategy`/`simulation`)
never depend on an LLM, and §2.2 requires active-round core functionality
(which includes shot simulation and strategy/recommendation) to remain
capable of local execution with no network request on the critical path.
A population-prior mechanism that is initially a config table and later a
fitted or learned model must not be allowed to violate either constraint by
accident — for example, by any future implementation being tempted to fetch
population parameters from a cloud service at recommendation time. This is
exactly the kind of forward-looking dependency-swap guarantee that
`AGENTS.md` §13 identifies as needing its own ADR (a public API/contract
commitment that later work must not silently violate), distinct from the
representation-family decision in ADR 0006.

## Decision

The initial `PlayerShotDistribution` parameters for a golfer with no (or
minimal) personal history are produced by a **`PopulationPrior`** function
(name illustrative), with the following binding contract:

- **Stable interface, replaceable implementation.** `PopulationPrior` maps
  golfer/context inputs (at minimum: handicap, club/club-category) to
  `PlayerShotDistribution` parameters (location, covariance/correlation,
  degrees-of-freedom). Its initial implementation is an evidence-derived,
  explicitly provisional config/lookup table. A future implementation may
  be a fitted statistical model, a learned/ML model trained on CaddAI's own
  accumulated calibration and round data, or a richer function of
  additional covariates (e.g. swing speed, equipment) — **without changing
  the function signature or the `PlayerShotDistribution` contract that
  `simulation`/`strategy` consume.** Consumers depend on the interface, not
  on how its parameters were produced.
- **Locally embeddable, no network dependency on the critical path.** A
  `PopulationPrior` implementation — whether a static config table or a
  future learned model — must resolve to parameters usable entirely from
  locally available data during an active round. Any future move to a
  learned model (e.g. periodically retrained centrally and shipped to the
  device) must ship its parameters as local, embeddable data ahead of time;
  it must never require a runtime network call to produce a recommendation,
  per [ADR 0005](0005-offline-first-active-round-architecture.md) and
  `AGENTS.md` §2.2. Model/parameter *updates* are connectivity-enhanced
  functionality (may sync when online); *using* the current parameters
  during a round is active-round core functionality (must not require
  connectivity).
- **Provisional numeric values must be visibly marked as such.** Because
  the research evidence does not yet support a complete, authoritative
  handicap × club-category parameter surface, the initial `PopulationPrior`
  implementation must expose enough provenance/confidence information that
  `simulation`/`strategy` (and ultimately any user-facing explanation) can
  distinguish "population-prior-only" from "personally-informed" estimates,
  without requiring `simulation`/`strategy` to know *how* that provenance
  was computed.
- **No dependency change implied.** Selecting or replacing a
  `PopulationPrior` implementation is, by itself, not license to add a new
  runtime dependency (e.g. `scipy`, a probabilistic-programming library, or
  an ML framework); any such dependency remains subject to its own ADR and
  human approval under `AGENTS.md` §9/§13 at the time it is actually
  proposed.

## Consequences

- Positive: `simulation` (and later `strategy`) can be implemented and
  tested against a stable `PlayerShotDistribution`/`PopulationPrior`
  contract now, while the underlying population-prior parameters are
  expected to improve as CaddAI collects its own calibration and round
  data — without a future breaking change to simulator or strategy code.
- Positive: makes explicit, ahead of implementation, that population-prior
  data must remain locally embeddable — preventing a design that would
  otherwise be easy to get wrong (e.g. a cloud lookup called during a
  round), consistent with ADR 0005.
- Positive: keeps "what personalizes a player's distribution" (ADR 0006)
  and "where population parameters come from and how they may evolve"
  (this ADR) as clearly separated concerns, each independently revisable.
- Negative: requires provenance/confidence metadata to be designed into
  `PlayerShotDistribution` (or an adjacent type) from the start, which is
  a small amount of extra V1 scope compared to shipping bare distribution
  parameters.
- Negative: defers, rather than resolves, exactly how a future learned
  population model would be trained, validated, or shipped to devices —
  that remains a future decision (and likely its own ADR) once CaddAI has
  enough first-party data to consider it.

## Alternatives considered

- **Hard-code population parameters directly into `player`/`statistics`
  logic (no separate `PopulationPrior` abstraction).** Simpler initially,
  but would make a future move to calibrated or learned parameters a
  breaking change to the code that also implements personalisation logic,
  and would make it easy to accidentally conflate "population assumption"
  with "personal estimate." Rejected.
- **Treat population-prior replacement as an implementation detail not
  requiring an ADR.** Rejected because it is precisely the kind of
  forward-looking contract guarantee (future dependency/model swap without
  breaking consumers) and offline-first constraint that `AGENTS.md` §13
  calls out for an ADR, and because it is easy to violate by accident
  (e.g. a well-intentioned future cloud-sync feature) without a recorded
  decision to check against.
- **Defer this decision entirely to M5 (strategy).** Rejected: `simulation`
  (M4) is the first consumer of `PlayerShotDistribution`, and the
  replaceability/offline constraints must hold before `simulation` is
  implemented, not retrofitted afterward.
