---
applyTo: "**/*.py"
---

# Python conventions

- Target Python 3.13. Use modern idioms: built-in generics (`list[str]`, not
  `List[str]`), `X | None` unions, `match` statements where they improve
  clarity, `Self`, and structural typing (`Protocol`) over inheritance where
  appropriate.
- Every function, method, and module-level variable has a full type hint. No
  untyped `def`. mypy runs in strict mode — code must satisfy it.
- Use clear, domain-accurate names. Prefer full words over abbreviations
  (`distance_metres`, not `dm`). Avoid generic names like `data`, `obj`, `tmp`.
- Keep functions small and single-purpose. Extract a helper when a function
  does more than one clearly nameable thing, not preemptively.
- Use Pydantic v2 models at domain and external boundaries (API request/response
  bodies, parsed course/GPS data, configuration) where validation or
  serialization adds value. Do not wrap purely internal, hot-path numerical
  data in Pydantic models if it hurts performance or clarity — plain
  dataclasses or NumPy arrays are fine internally.
- Use NumPy vectorised operations for bulk numerical work (dispersion grids,
  Monte Carlo samples, distance arrays). Avoid Python-level loops over large
  numeric arrays.
- All physical quantities are SI internally. Canonical distance unit is
  **metres**. Name fields so units are unambiguous whenever a reader could
  otherwise guess wrong (e.g. `carry_metres`, `wind_speed_mps`,
  `elevation_change_metres`), especially at module or API boundaries.
- API and UI adapters (FastAPI routes, CLI commands) must not contain golf
  business logic. They translate between the outside world and calls into the
  domain/strategy layers.
- Public functions, classes, and modules get a concise docstring stating
  purpose, units of any physical parameters, and notable invariants. Private
  helpers only need docstrings when behaviour isn't obvious from the name and
  signature.
- Avoid premature abstraction: don't introduce base classes, plugin systems,
  or config-driven generality for a single concrete use case. Add abstraction
  when a second real use case demands it.
