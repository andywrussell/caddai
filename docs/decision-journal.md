# Decision journal

> Status: describes a **future** concept (milestone M6). No storage or data
> model is implemented yet — this document exists to guide that eventual
> design, not to describe existing functionality.

## Purpose

Capture what CaddAI recommended, what the player actually did, and what
happened, so both **player behaviour** and **strategy quality** can be
evaluated over time. This is the feedback loop that lets the strategy engine
(and, later, its statistical inputs) be validated against real outcomes
rather than assumptions alone.

## Planned record shape

For each shot, the decision journal will eventually record:

- **Situation** — the position, lie, hole geometry, and conditions (wind,
  elevation, etc.) at the time of the shot.
- **Recommendation** — the deterministic engine's structured output: target,
  club, intended shot shape, risk assessment.
- **Recommendation rationale** — which inputs (simulation results, expected
  strokes comparison, risk trade-off) drove the recommendation.
- **Player decision** — the club/target the player actually chose, which may
  differ from the recommendation.
- **Shot outcome** — the actual observed result of the shot (e.g. via GPS or
  manual entry).
- **Resulting lie** — the lie the ball ended up in.
- **Resulting position** — where the ball ended up.

## Intended uses

- Evaluate strategy quality: did following (or deviating from) the
  recommendation correlate with better outcomes?
- Evaluate and refine player statistical models: does a player's actual
  dispersion match the model used to generate the recommendation?
- Provide a dataset for future refinement of the simulation and strategy
  models.

## Explicit non-goals for now

- No storage technology is selected. Selecting one (file-based, embedded, or
  hosted database) is a decision deferred to M6 and requires an ADR plus
  human approval per `AGENTS.md` §14 (database/infrastructure selection is
  an escalation trigger). Whatever is chosen must support a local write path
  for recording decisions/outcomes, since that is active-round core
  functionality (`AGENTS.md` §2.2, see
  [ADR 0005](adr/0005-offline-first-active-round-architecture.md)); any
  round-history synchronisation to a remote store is connectivity-enhanced,
  never a prerequisite for recording during a round.
- No implementation of recording, querying, or persistence exists yet.
