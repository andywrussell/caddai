# AGENTS.md — CaddAI engineering handbook

This is the durable engineering handbook for CaddAI. Every agent (human or
AI) working in this repository reads this file before making changes. It is
the source of truth when other documents disagree with it.

## 1. Product mission

CaddAI is an AI-powered golf caddie. It combines course geometry, GPS
location, player ability, club performance, lie, wind, elevation,
environmental conditions, shot dispersion, and statistical simulation to
recommend golf shots. The target end-state user experience is a player
asking "What do you like here?" and receiving a concise, caddie-style
recommendation.

See [docs/vision.md](docs/vision.md) and [docs/prd.md](docs/prd.md) for full
product context, and [docs/roadmap.md](docs/roadmap.md) for milestone
sequencing.

## 2. Non-negotiable architectural principle: deterministic strategy

**CaddAI is a golf decision engine, not a chatbot.**

- The deterministic engine (`strategy` + `simulation`) decides target, club,
  intended shot, and risk.
- An LLM may eventually *explain* a structured recommendation in natural
  language. An LLM must **never** be the source of the underlying golf
  decision.
- No `strategy` or `simulation` code may import `llm`, `api`, `cli`, or any UI
  package, directly or transitively.
- This principle is recorded in
  [docs/adr/0001-deterministic-strategy-engine.md](docs/adr/0001-deterministic-strategy-engine.md).
  Changing it requires a new ADR and explicit human approval — see
  [Escalation rules](#9-escalation-rules).

## 3. Architecture overview

See [docs/architecture.md](docs/architecture.md) for the full picture. In
summary, planned subsystems under `src/caddai/`:

| Subsystem | Owns | Depends on |
|---|---|---|
| `course` | course geometry, holes, hazards, GeoJSON | domain types only |
| `gps` | coordinates, GPS calculations | domain types only |
| `player` | players, clubs, tendencies | domain types, `statistics` |
| `statistics` | carry distributions, dispersion, round stats | domain types |
| `strategy` | shot candidates, club/target selection, risk, EV | `course`, `player`, `statistics`, `simulation` |
| `simulation` | Monte Carlo shot outcome simulation | `course`, `player`, `statistics` |
| `llm` | natural-language explanation of a recommendation | reads `strategy` output only, never called by it |
| `api` | FastAPI adapters | calls into `strategy`/`course`/`player`, contains no business logic |
| `cli` | Typer adapters | calls into `strategy`/`course`/`player`, contains no business logic |

Only the bootstrap package (`src/caddai/__init__.py`) exists today. Modules
above are created as their owning milestone is implemented — do not
pre-create empty placeholder packages.

### Dependency direction

- Dependencies flow from adapters (`api`, `cli`, `llm`) inward to the domain
  and decision layers (`strategy`, `simulation`, `course`, `player`,
  `statistics`), never the reverse.
- `strategy` and `simulation` never depend on `llm`, `api`, `cli`, or UI code.
- Shared domain types (e.g. a `Shot`, `Hole`, `Player` model) may live in a
  neutral module imported by multiple subsystems, but business logic stays in
  its owning subsystem.

## 4. Module ownership

Each subsystem is owned by one domain engineer agent (see
[section 8](#8-agent-team)):

- `src/caddai/course/`, `src/caddai/gps/` → Course Engineer
- `src/caddai/player/`, `src/caddai/statistics/` → Player Engineer
- `src/caddai/strategy/`, `src/caddai/simulation/` → Strategy Engineer

Don't edit another agent's owned files without reason (e.g. a small,
clearly-scoped shared-type change). Cross-cutting changes should be flagged
to the Architect and coordinated by the Orchestrator.

## 5. Units

Use **SI units internally**. Canonical distance is **metres**. Name fields so
units are unambiguous wherever confusion is plausible, e.g. `carry_metres`,
`wind_speed_mps`, `elevation_change_metres`. Presentation layers (CLI output,
API responses intended for a yards-preferring audience, future mobile UI) may
convert metres to yards at the boundary — conversion never happens inside
`strategy` or `simulation`.

## 6. Python conventions

Full details: [.github/instructions/python.instructions.md](.github/instructions/python.instructions.md).
Summary:

- Python 3.13, `src` layout, full strict type hints everywhere (mypy strict).
- Pydantic v2 at domain/external boundaries; NumPy vectorisation for bulk
  numerical work.
- Small, single-purpose functions. Avoid premature abstraction.
- No business logic in `api`/`cli` adapters.
- Public APIs get concise docstrings.

## 7. Testing

Full details: [.github/instructions/tests.instructions.md](.github/instructions/tests.instructions.md).
Summary: behaviour-based, deterministic, edge-case-covering tests; regression
tests for every bug fix; fixed random seeds for any stochastic code; no tests
that just instantiate an object.

## 8. Quality gates

Every change must pass, in order:

```bash
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
```

Run via `scripts/check.sh` or follow
[.github/skills/quality-gates/SKILL.md](.github/skills/quality-gates/SKILL.md).
All four gates must pass before work is considered done — see
[Definition of done](#11-definition-of-done).

## 9. Approved dependencies

Runtime: **Pydantic v2, NumPy, Shapely, FastAPI, Typer**.
Dev: **pytest, Ruff, mypy**.

Do **not** add LangChain, LangGraph, GeoPandas, SciPy, pandas, DuckDB,
PostGIS, cloud SDKs, or LLM SDKs unless an ADR explicitly justifies it and a
human approves. Any new runtime dependency not on this list requires an ADR
(see [.github/skills/architecture-decision/SKILL.md](.github/skills/architecture-decision/SKILL.md))
and human sign-off.

## 10. Agent team

CaddAI is developed by a coordinated team of VS Code custom agents defined in
[.github/agents/](.github/agents):

1. **CaddAI Orchestrator** — main user-facing agent; plans, delegates, does
   not implement production features itself.
2. **CaddAI Architect** — hidden, read-only; architecture and boundary review.
3. **Course Engineer** — owns `course/`, `gps/`.
4. **Player Engineer** — owns `player/`, `statistics/`.
5. **Strategy Engineer** — owns `strategy/`, `simulation/`.
6. **QA Engineer** — designs and writes tests; does not implement production
   logic.
7. **Adversarial Reviewer** — hidden, read-only; approves or requests changes.
8. **Integrator** — runs quality gates, checks docs/dependency boundaries,
   updates `CHANGELOG.md`, reports final validation.

Full workflow: [docs/development-workflow.md](docs/development-workflow.md).

## 11. Definition of done

A change is done when:

- It satisfies the acceptance criteria from the implementation plan.
- Tests exist for the new/changed behaviour and pass.
- All four quality gates pass.
- Module ownership and dependency direction rules are respected.
- No unapproved dependency was added.
- Documentation affected by the change is updated (and an ADR exists for
  significant architectural decisions).
- `CHANGELOG.md` reflects the change under `[Unreleased]`.
- The Adversarial Reviewer has returned `APPROVE`, or the human has accepted
  the outstanding risk.

## 12. Documentation map

| Doc | Purpose |
|---|---|
| [docs/vision.md](docs/vision.md) | Why CaddAI exists, who it's for |
| [docs/prd.md](docs/prd.md) | Product requirements |
| [docs/architecture.md](docs/architecture.md) | System structure, boundaries, dependency direction |
| [docs/roadmap.md](docs/roadmap.md) | Milestones M0–M9 |
| [docs/development-workflow.md](docs/development-workflow.md) | Request → merge workflow |
| [docs/domain-model.md](docs/domain-model.md) | Core golf domain concepts and entities |
| [docs/course-engine.md](docs/course-engine.md) | Course/GPS subsystem design |
| [docs/player-model.md](docs/player-model.md) | Player/statistics subsystem design |
| [docs/strategy-engine.md](docs/strategy-engine.md) | Strategy/simulation subsystem design |
| [docs/decision-journal.md](docs/decision-journal.md) | Future recommendation/outcome logging |
| [docs/backlog.md](docs/backlog.md) | Candidate work items beyond the current milestone |
| [docs/plans/](docs/plans/) | Per-feature implementation plans written by the Orchestrator |
| [docs/adr/](docs/adr/) | Architecture Decision Records |

## 13. ADR requirements

An ADR is required for: a new runtime dependency, a public API contract
change, a canonical unit change, a module ownership change, a dependency
direction change, or any change to the deterministic-strategy principle. See
[.github/skills/architecture-decision/SKILL.md](.github/skills/architecture-decision/SKILL.md)
for format and process.

## 14. Escalation rules

Stop and request a human decision (`NEEDS_DECISION`, see format below) before:

- adding a new runtime dependency not already approved,
- changing a public API contract,
- changing canonical units,
- changing module ownership,
- violating dependency direction,
- adding a cloud service or a paid external service,
- adding an LLM provider,
- storing credentials or secrets,
- performing destructive Git operations,
- selecting a database or infrastructure component,
- anything with significant privacy implications,
- a golf strategy assumption not already defined by existing product docs,
- conflicting requirements,
- changing the deterministic-strategy principle.

`NEEDS_DECISION` output format:

```
NEEDS_DECISION

Context
...

Options
...

Recommendation
...

Consequences
...
```

Do not guess when one of these conditions applies.

## 15. Git safety

Agents may create/edit local files and run local commands (tests, lint,
`uv sync`, local `git add`/`git commit` on request). Agents must never create
a remote, push, force-push, merge, alter credentials, store API keys, or
commit on the human's behalf without explicit instruction for that specific
commit.
