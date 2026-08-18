---
name: quality-gates
description: Run and report the CaddAI local quality gate (dependency sync, format check, lint, strict type check, tests). Use before considering any implementation task done.
---

# Quality gates

CaddAI treats these four checks as the definition of a passing build. Run them
in this order, using `uv`, from the repository root:

```bash
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
```

Equivalently, run `scripts/check.sh`, which executes the same sequence.

## How to run and report

1. Run `uv sync --frozen`. If this fails, the lockfile is out of date with
   `pyproject.toml` — do not silently regenerate it; report the mismatch. A
   dependency change requires human sign-off if it's not already an approved
   dependency (see `AGENTS.md`).
2. Run `uv run ruff format --check .`. Report PASS/FAIL and the list of files
   that would be reformatted, if any. Fix by running `uv run ruff format .`
   only on files you own.
3. Run `uv run ruff check .`. Report PASS/FAIL and each rule violation with
   file:line. Fix the underlying code; do not disable rules to make this
   pass unless a rule is clearly wrong for a specific, justified line (use a
   scoped `# noqa: RULE` with a reason, never a blanket ignore).
4. Run `uv run mypy src`. Report PASS/FAIL and each type error. mypy runs in
   strict mode — do not add `# type: ignore` without a one-line reason
   comment, and never weaken `strict` in `pyproject.toml` to make an error
   disappear.
5. Run `uv run pytest`. Report PASS/FAIL, the number of tests passed/failed,
   and the failure output for any failing test.

## Reporting format

Summarize as a short checklist, e.g.:

```
- uv sync --frozen: PASS
- ruff format --check: PASS
- ruff check: PASS
- mypy src: FAIL (2 errors) — src/caddai/course/geometry.py:41, :57
- pytest: PASS (18 passed)
```

## Rules

- All four checks must pass before work is considered integrated. A single
  failing check blocks integration regardless of how minor it looks.
- Never mask a failure by loosening configuration (weakening mypy strictness,
  disabling a ruff rule broadly, skipping/xfail-ing a real test) instead of
  fixing the underlying issue. If a config change is genuinely warranted,
  escalate it — see `AGENTS.md` escalation rules.
- If a failure reveals a substantial design or ownership problem (not a small
  fix), stop and report it rather than making a large unreviewed change.
