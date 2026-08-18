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
4. Use SI units internally — canonical distance is **metres**. Name fields so
   units are unambiguous (`carry_metres`, `wind_speed_mps`).
5. Use strict, full type hints everywhere (mypy strict mode).
6. Write or update tests for every behaviour change, following
   [tests.instructions.md](instructions/tests.instructions.md).
7. Run the quality gates (`.github/skills/quality-gates/SKILL.md`) before
   considering work done: `uv sync --frozen`, `ruff format --check`,
   `ruff check`, `mypy src`, `pytest`.
8. Avoid unnecessary dependencies. Only the libraries approved in `AGENTS.md`
   may be used without an ADR and human approval.
9. Never commit secrets, API keys, or credentials. Never push, force-push, or
   perform destructive Git operations on the user's behalf.
10. Update documentation (`docs/`) when architectural behaviour changes, and
    write an ADR (`.github/skills/architecture-decision/SKILL.md`) for
    significant architectural decisions.

When in doubt, escalate rather than guess — see the escalation rules in
`AGENTS.md`.
