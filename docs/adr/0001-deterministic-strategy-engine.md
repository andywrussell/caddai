# 0001. Deterministic strategy engine

## Status

Accepted

## Context

CaddAI's core value proposition is a trustworthy, explainable golf shot
recommendation. Large language models are increasingly capable of producing
plausible-sounding golf advice directly from a prompt, which would be the
fastest way to prototype a "what do you like here?" feature. However, LLM
output is not reliably grounded in the actual geometry of the hole, the
player's real statistical tendencies, or a consistent risk model — it can
sound authoritative while being wrong, and its reasoning is not reproducible
or unit-testable in the way a deterministic calculation is.

CaddAI needs recommendations that are: reproducible (the same inputs always
produce the same recommendation), testable (strategy logic can be unit and
regression tested), and traceable (a recommendation can be explained in terms
of concrete inputs: geometry, statistics, simulation results).

## Decision

CaddAI's shot recommendation is produced entirely by a deterministic engine
(`strategy` + `simulation`), built from course geometry, player/club
statistics, and Monte Carlo simulation of outcomes. This engine decides
target, club, intended shot shape, and risk.

An LLM may, at a later milestone (M8), be used **only** to translate an
already-finished, structured recommendation into natural, caddie-style
language for presentation. It reads the recommendation; it does not produce
it, and it is never in a position to override or substitute for the
deterministic decision.

Enforcement: `strategy` and `simulation` modules must never import `llm`,
`api`, `cli`, or any UI package, directly or transitively. This is checked by
architecture-invariant tests (see
`.github/instructions/tests.instructions.md`) and by the Adversarial
Reviewer subagent on every change.

## Consequences

- Positive: recommendations are reproducible, unit-testable, and their
  reasoning is traceable to specific inputs. The system can be validated
  against known scenarios without depending on LLM behaviour or availability.
- Positive: LLM integration can be deferred (roadmap M8) without blocking any
  other milestone, and can be swapped or removed later without touching the
  decision engine.
- Negative: building a good deterministic engine (geometry, statistics,
  simulation, risk modelling) is more work up front than prompting an LLM for
  golf advice, and covers a narrower set of situations until those
  subsystems mature.
- Negative: any request to have an LLM "help decide" a shot (rather than
  explain one already decided) is out of scope and must be escalated via
  `NEEDS_DECISION`, not implemented ad hoc.

## Alternatives considered

- **LLM-first recommendation** (prompt an LLM with situation details and let
  it produce the club/target/rationale directly): rejected — not
  reproducible or reliably testable, and risks confidently wrong advice that
  looks credible.
- **Hybrid where the LLM can override the deterministic recommendation in
  edge cases**: rejected — reintroduces the same trust and testability
  problem for exactly the cases where it matters most (unusual situations).
- **No natural-language layer at all**: rejected as a permanent stance — a
  concise, human-readable explanation is part of the target product
  experience (see `docs/vision.md`), just deliberately sequenced late
  (roadmap M8) so it never becomes the source of the decision.
