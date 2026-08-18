# CaddAI

CaddAI is an AI-powered golf caddie. It combines course geometry, GPS
location, player ability, club performance, lie, wind, elevation, and
statistical simulation to recommend golf shots.

> **Status: bootstrap (M0).** This repository currently contains project
> architecture, documentation, and a minimal Python package skeleton. No golf
> strategy, course import, player modelling, or LLM functionality is
> implemented yet. See [docs/roadmap.md](docs/roadmap.md).

## Non-negotiable architectural principle

CaddAI is a **golf decision engine, not a chatbot**. A deterministic engine
decides target, club, shot, and risk. An LLM may eventually *explain* a
recommendation, but must never *be* the source of a golf decision. See
[docs/adr/0001-deterministic-strategy-engine.md](docs/adr/0001-deterministic-strategy-engine.md).

## Technology

- Python 3.13, managed with [uv](https://docs.astral.sh/uv/).
- Runtime dependencies: Pydantic v2, NumPy, Shapely, FastAPI, Typer.
- Dev tooling: pytest, Ruff, mypy (strict).
- `src/` layout. SI units internally (metres for distance).

## Getting started

```bash
uv sync
uv run pytest
```

Run the developer recommendation demo (prints a sample club recommendation
using the real strategy engine):

```bash
uv run python -m caddai.strategy.demo
```

Run the full local quality gate:

```bash
scripts/check.sh
```

The same checks run in CI via [GitHub Actions](.github/workflows/ci.yml) on
every pull request targeting `main` and on every push to `main`.

## Documentation

Start with [AGENTS.md](AGENTS.md) (the engineering handbook), then
[docs/vision.md](docs/vision.md), [docs/architecture.md](docs/architecture.md),
and [docs/roadmap.md](docs/roadmap.md).

## Development workflow

CaddAI is developed by a coordinated team of specialized AI agents defined in
[.github/agents](.github/agents). See
[docs/development-workflow.md](docs/development-workflow.md) for how a request
flows from orchestration through implementation, review, integration, and a
GitHub pull request.

## License

[MIT](LICENSE)
