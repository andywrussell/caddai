# Implementation plans

This directory holds per-feature/per-milestone implementation plans written
by the **CaddAI Orchestrator** before delegating work to domain engineers.

## Naming

`docs/plans/<feature-or-milestone-slug>.plan.md`, e.g.
`docs/plans/m1-core-domain-vertical-slice.plan.md`.

## Expected shape

Each plan should include:

- **Goal** — one or two sentences describing the milestone/feature.
- **Architect input** — summary of the CaddAI Architect subagent's review
  (boundary concerns, ADR needs).
- **Tasks** — a small, ordered list of tasks, each with:
  - owning domain engineer,
  - files/subsystem touched,
  - acceptance criteria,
  - test expectations from QA Engineer input.
- **Parallelism** — which tasks (if any) can run concurrently because they
  touch non-overlapping files.
- **Escalations** — any `NEEDS_DECISION` items raised during planning.

Plans are living documents during a milestone and are not deleted after
completion — they form a historical record of how each milestone was
delivered. No plans exist yet; the first will be written when M1 begins.
