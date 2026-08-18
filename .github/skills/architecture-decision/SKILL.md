---
name: architecture-decision
description: Determine when a change needs an Architecture Decision Record (ADR) and how to write one, for CaddAI. Use when proposed work changes a dependency, public API, canonical units, module ownership, dependency direction, or the deterministic-strategy principle.
---

# Architecture decisions (ADRs)

## When an ADR is required

Create an ADR under `docs/adr/` before (or as part of) implementing a change
that:

- adds a new runtime dependency not already approved in `AGENTS.md`,
- changes a public API contract (FastAPI routes, CLI commands, or the stable
  surface of `caddai` modules used across subsystems),
- changes the canonical unit system (currently SI / metres internally),
- changes which module/agent owns a subsystem,
- changes the dependency direction between modules (e.g. anything importing
  `strategy` or `simulation`, or `strategy`/`simulation` importing anything
  outside themselves and shared domain types),
- touches the deterministic-strategy principle (the rule that `llm` can
  explain but never decide),
- introduces a new architectural pattern (e.g. a new persistence approach,
  a new simulation method) intended to be reused going forward.

Small, local implementation choices that don't affect other subsystems do not
need an ADR.

If you are an agent and you identify that a task requires one of the above but
no ADR exists and the decision isn't already settled by an existing ADR or
product doc, do not decide unilaterally — escalate with `NEEDS_DECISION` (see
`AGENTS.md`) so a human can approve the direction. Once approved, write the
ADR to record it.

## ADR format

Create `docs/adr/NNNN-short-title.md` (four-digit, zero-padded, sequential)
using this structure:

```markdown
# NNNN. Title

## Status

Proposed | Accepted | Superseded by NNNN | Rejected

## Context

What situation/problem/tension makes a decision necessary. Include relevant
constraints from AGENTS.md or product docs.

## Decision

The decision, stated plainly and specifically.

## Consequences

What becomes easier or harder as a result. Include negative consequences
honestly, not just benefits.

## Alternatives considered

Each alternative considered, with why it was not chosen.
```

## Process

1. Check `docs/adr/README.md` for the next available ADR number.
2. Write the ADR with status `Proposed` if human approval is still pending,
   or `Accepted` if the human has already approved the direction in the
   conversation.
3. Link the ADR from `docs/architecture.md` or the relevant domain doc if it
   changes documented behaviour.
4. Never silently supersede or delete an existing ADR — add a new one with
   status `Superseded by NNNN` and update the old one's status.
