# M1 — Core golf domain model and simple deterministic recommendation vertical slice

## Goal

Prove the CaddAI architecture and agent workflow end-to-end with a
deliberately trivial, fully deterministic recommendation path: given a
player (with clubs), a target distance, basic wind, and a lie, return a
structured recommendation (club, playing distance, confidence, reasons). No
course geometry, no statistics/simulation subsystem, no LLM, no adapters —
those are later milestones (see [docs/roadmap.md](../roadmap.md)).

## Architect input (CaddAI Architect review, summarised)

- `Player`/`Club` → `src/caddai/player/` (Player Engineer owned). `Club` uses
  a single scalar `expected_carry_metres` for M1, **not** a carry
  distribution — carry distributions are explicit M3 scope
  ([docs/player-model.md](../player-model.md)). Document this as a stand-in.
- `Wind`/`LieType` → defined inside `src/caddai/strategy/` for M1 (no
  `course`/`gps`/`simulation` package exists yet to own them). Flagged: these
  may need to move to a neutral shared-domain module once `course` (M2) or
  `simulation` (M4) land — noted in `docs/strategy-engine.md` as a forward
  pointer, not an ADR (no ownership/dependency-direction change today).
- `RecommendationRequest`/`RecommendationResult` + the `recommend_club`
  function → `src/caddai/strategy/`, Strategy Engineer owned. This is an
  explicit trimmed subset of the full `Recommendation` concept in
  [docs/domain-model.md](../domain-model.md) (no shot shape/risk yet).
- Dependency direction: `strategy` (M1) depends only on `player` + stdlib +
  Pydantic. No `course`/`gps`/`statistics`/`simulation` imports exist or are
  needed. No NumPy for this slice — arithmetic is scalar, not bulk.
- **No ADR required.** No new dependency, no public API change (none
  existed), no unit change, no ownership change, no dependency-direction
  change, no change to the deterministic-strategy principle — ADR 0001
  already covers determinism and the import ban.
- Risks to address in tasks below: document wind/lie adjustment as an
  explicit, arbitrary, documented placeholder formula (no bearing/vector
  math — headwind/tailwind/crosswind only); document the `confidence`
  formula precisely; validate at the Pydantic boundary (no empty club list,
  no non-positive target distance/wind speed); add an architecture-invariant
  test that `caddai.strategy` never imports `llm`/`api`/`cli`/UI packages;
  keep unambiguous unit suffixes on every field.

## Escalations

None. No item in this milestone matches an `AGENTS.md` §14 escalation
trigger.

## Tasks

### Task 1 — Player domain model (Player Engineer)

Files: `src/caddai/player/__init__.py`, `src/caddai/player/models.py`.

- `Club` (Pydantic v2 model): `name: str` (non-empty), `expected_carry_metres: float`
  (must be `> 0`). Docstring must state this is a deliberate M1 placeholder
  for the future carry distribution (M3).
- `Player` (Pydantic v2 model): `name: str` (non-empty), `clubs: list[Club]`
  (must be non-empty — validated, not silently accepted).
- Full strict type hints; concise docstrings on both public models.
- No imports from `strategy`, `simulation`, `course`, `gps`, `llm`, `api`,
  `cli`.

Acceptance criteria:

- `Club` and `Player` are constructible with valid data and raise a
  validation error for: empty club name, non-positive
  `expected_carry_metres`, empty player name, empty `clubs` list.
- `mypy --strict` passes on the new module.
- No cross-subsystem imports other than Pydantic/stdlib.

### Task 2 — Strategy request/result models + recommendation logic (Strategy Engineer)

Depends on Task 1 (imports `Player`/`Club`) — runs **after** Task 1, not in
parallel.

Files: `src/caddai/strategy/__init__.py`, `src/caddai/strategy/models.py`,
`src/caddai/strategy/recommend.py`.

`strategy/models.py`:

- `WindDirection` (str enum): `HEADWIND`, `TAILWIND`, `CROSSWIND`.
- `Wind` (Pydantic v2 model): `speed_mps: float` (`>= 0`),
  `direction: WindDirection`. Docstring states the M1 simplification: wind is
  treated as a scalar along-shot component only (headwind/tailwind
  lengthen/shorten playing distance; crosswind has no effect on playing
  distance in this model) — no bearing/vector wind model until `gps`/`course`
  exist.
- `LieType` (str enum): `TEE`, `FAIRWAY`, `ROUGH`, `BUNKER`, `RECOVERY`.
- `RecommendationRequest` (Pydantic v2 model): `player: Player`,
  `target_distance_metres: float` (`> 0`), `wind: Wind`, `lie: LieType`.
- `RecommendationResult` (Pydantic v2 model): `selected_club: Club`,
  `playing_distance_metres: float`, `confidence: float` (`0.0`–`1.0`),
  `reasons: list[str]` (non-empty).

`strategy/recommend.py`:

- Explicit, documented, arbitrary placeholder constants (module-level,
  named, with a comment that they are placeholders pending a real
  statistical/physical model):
  - `WIND_ADJUSTMENT_METRES_PER_MPS` — additive metres of playing distance
    per m/s of headwind (subtracted for tailwind, ignored for crosswind).
  - `LIE_ADJUSTMENT_METRES` — `dict[LieType, float]` additive playing-distance
    penalty per lie (e.g. `TEE`/`FAIRWAY` = 0, `ROUGH` > 0, `BUNKER` >
    `ROUGH`, `RECOVERY` highest).
  - `CONFIDENCE_ZERO_AT_METRES` — the carry/playing-distance gap (metres) at
    or beyond which confidence reaches `0.0`; confidence decays linearly
    from `1.0` at zero gap.
- `recommend_club(request: RecommendationRequest) -> RecommendationResult`:
  1. Compute `playing_distance_metres` = target distance + wind adjustment +
     lie adjustment, floored at `0.0`.
  2. Select the club in `request.player.clubs` minimising
     `abs(club.expected_carry_metres - playing_distance_metres)` (ties broken
     by club list order — deterministic, no randomness).
  3. Compute `confidence` from the winning club's distance gap using the
     documented linear decay, clamped to `[0.0, 1.0]`.
  4. Build `reasons`: at minimum (a) a reason stating the target→playing
     distance adjustment and why (wind + lie), (b) a reason stating why the
     club was chosen (closest expected carry), (c) an explicit reason
     stating this is a primitive M1 strategy that does not yet model shot
     dispersion, course conditions, or risk.
  5. Return a `RecommendationResult`.
- Module or function docstring must explicitly state: *"This is an
  intentionally primitive placeholder strategy for milestone M1, proving the
  end-to-end architecture. It is not a realistic golf strategy model — see
  docs/roadmap.md M4/M5 for the real expected-value/Monte Carlo model."*
- No imports from `course`, `gps`, `statistics`, `simulation`, `llm`, `api`,
  `cli`, or any UI package.

Acceptance criteria:

- Given a player with clubs `[100m, 120m, 140m]`, a target distance of
  `120m`, calm-equivalent wind (`speed_mps=0`), and `lie=FAIRWAY`, the
  `120m` club is selected, `playing_distance_metres == 120.0`, `confidence == 1.0`
  (zero gap), and `reasons` is non-empty.
- Headwind increases `playing_distance_metres` versus the same request with
  `speed_mps=0`; tailwind decreases it; crosswind leaves it unchanged versus
  calm.
- A worse lie (e.g. `BUNKER` vs `FAIRWAY`, all else equal) never decreases
  `playing_distance_metres`.
- `playing_distance_metres` never goes below `0.0` even for a small target
  distance with a strong tailwind.
- Confidence strictly decreases as the winning club's carry/playing-distance
  gap increases, reaching exactly `0.0` at `CONFIDENCE_ZERO_AT_METRES` and
  staying at `0.0` beyond it.
- `reasons` always contains at least the three reason categories above.
- `mypy --strict` passes; no forbidden imports.

### Task 3 — Architecture-invariant test (QA Engineer, cross-cutting)

Files: `tests/test_architecture_boundaries.py`.

- Statically asserts (via `ast` module or `importlib`) that neither
  `caddai.strategy.models` nor `caddai.strategy.recommend` imports
  `caddai.llm`, `caddai.api`, `caddai.cli`, or common UI packages, directly.

Acceptance criteria:

- Test fails if someone later adds a forbidden import to `strategy`, passes
  today.

### Task 4 — Documentation updates (Integrator, after review passes)

- Update the "Status" banners in [docs/player-model.md](../player-model.md)
  and [docs/strategy-engine.md](../strategy-engine.md) to note that a
  minimal M1 slice now exists (`player/models.py`,
  `strategy/models.py`/`recommend.py`), while full carry-distribution
  (M3)/expected-value/Monte Carlo (M4–M5) depth remains pending.
- Add a short forward-pointer note in `docs/strategy-engine.md` that
  `Wind`/`LieType` are defined in `strategy` for M1 pending a possible move
  to a neutral shared-domain module at M2/M4.
- Update `CHANGELOG.md` under `[Unreleased]`.

## Parallelism

Task 1 (Player Engineer) must complete before Task 2 (Strategy Engineer)
starts, since Task 2 imports `Player`/`Club`. Task 3 (QA Engineer test
design/writing) can be authored in parallel with Task 1/2 implementation
(tests target the acceptance criteria above) but the architecture-invariant
test can only be run for real once `strategy` exists. No two agents modify
the same subsystem concurrently.

## Escalations raised during planning

None.
