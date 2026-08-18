## Summary

<!-- What does this PR do and why? -->

## Related task/issue

<!-- Link the docs/plans/ entry, issue, or milestone this PR implements -->

## Changes

<!-- Bullet list of the key changes, and which subsystem(s)/owner(s) they touch -->

## Testing

<!-- What tests were added/updated? How was this verified locally? -->

## Architecture impact

<!-- Any changes to module ownership, dependency direction, public API
     contracts, canonical units, or the deterministic-strategy principle?
     Link an ADR under docs/adr/ if one was required. If none, say "None". -->

## Documentation impact

<!-- Which docs/ files were updated? If none were needed, say why. -->

## Quality gate checklist

- [ ] `uv sync --frozen`
- [ ] `uv run ruff format --check .`
- [ ] `uv run ruff check .`
- [ ] `uv run mypy src`
- [ ] `uv run pytest`
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] Adversarial Reviewer returned `APPROVE` (or human accepted the risk)
