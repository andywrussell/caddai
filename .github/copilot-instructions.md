---
applyTo: "**"
---

# Copilot instructions for CaddAI

Every Copilot interaction in this repository must:

1. Read [AGENTS.md](../AGENTS.md) first — it is the durable engineering
   handbook (module ownership, dependency direction, units, quality gates,
   escalation rules, definition of done).
2. Respect subsystem boundaries and module ownership defined in `AGENTS.md`.
   Don't edit another subsystem's owned files without reason.
3. Preserve the deterministic golf strategy principle: `strategy` and
   `simulation` decide; `llm` may only explain. No strategy/simulation code
   may import `llm`, `api`, `cli`, or UI packages.
4. Preserve the offline-first active-round principle: network connectivity
   is optional during an active round. Active-round core functionality
   (positioning, course geometry access, player profile access, distance
   calculations, shot simulation, strategy/recommendation, and recording
   decisions/outcomes) must remain capable of local execution with no
   network request on the critical path. Never make a cloud API a mandatory
   dependency for these — see `AGENTS.md` §2.2.
5. Use SI units internally — canonical distance is **metres**. Name fields so
   units are unambiguous (`carry_metres`, `wind_speed_mps`).
6. Use strict, full type hints everywhere (mypy strict mode).
7. Write or update tests for every behaviour change, following
   [tests.instructions.md](instructions/tests.instructions.md).
8. Run the quality gates (`.github/skills/quality-gates/SKILL.md`) before
   considering work done: `uv sync --frozen`, `ruff format --check`,
   `ruff check`, `mypy src`, `pytest`. The same gates run in GitHub Actions CI
   (`.github/workflows/ci.yml`) on pull requests and pushes to `main`.
9. Avoid unnecessary dependencies. Only the libraries approved in `AGENTS.md`
   may be used without an ADR and human approval.
10. Never commit secrets, API keys, or credentials. Never push, force-push,
    open/merge a GitHub pull request, or perform destructive Git operations on
    the user's behalf. Collaboration happens through GitHub pull requests,
    reviewed and merged by a human.
11. Update documentation (`docs/`) when architectural behaviour changes, and
    write an ADR (`.github/skills/architecture-decision/SKILL.md`) for
    significant architectural decisions.
12. Check significant product decisions against
    [docs/prfaq.md](../docs/prfaq.md), the product north star, but consult it
    selectively — see the relevant `.github/agents/*.agent.md` file for when.
    It never overrides an ADR, architectural constraint, or accepted issue
    requirements — escalate conflicts.
13. Read only the documentation necessary for the task. Prefer the issue plus
    relevant subsystem docs and ADRs over loading the full documentation set.

When in doubt, escalate rather than guess — see the escalation rules in
`AGENTS.md`.
