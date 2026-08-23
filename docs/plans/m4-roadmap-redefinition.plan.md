# M4 roadmap redefinition (documentation-only)

## Goal

Redefine roadmap milestone M4 — currently framed narrowly as "candidate-shot
generation and Monte Carlo simulation" — to correctly centre the more
fundamental modelling problem: what shots a given golfer is likely to
produce, represented probabilistically, initialised from an evidence-based
population model plus onboarding personalisation, and only then sampled
(initially via Monte Carlo) for candidate-shot outcomes. Add a preceding
research/architecture milestone, M4.0, that must investigate and settle this
modelling approach before the detailed M4 implementation backlog is created.
This is a **documentation-only** change: no production code, no new
dependency, no M4 implementation issues are created as part of this task.

## Architect input

The CaddAI Architect subagent reviewed the proposed reframing (see summary
below) and confirmed:

- No ADR is required for this roadmap edit itself — no new runtime
  dependency, public API change, canonical unit change, module ownership
  change, dependency-direction change, or change to the deterministic-
  strategy/offline-first principles is being made now.
- ADR 0001's Decision text (which names "Monte Carlo simulation of outcomes")
  should **not** be edited — it's a historical record of a decision that
  remains valid (an LLM never decides). The roadmap/architecture prose can
  clarify that Monte Carlo is `simulation`'s *initial* outcome-sampling
  mechanism, not the domain abstraction, without contradicting ADR 0001.
- If M4.0's conclusions lead to a new shared `player`/`statistics` ↔
  `simulation` contract (e.g. a `PlayerShotDistribution` abstraction) or a
  new runtime dependency (e.g. `scipy` for a non-Gaussian representation),
  **that** is the trigger for its own ADR before M4 implementation starts —
  not now, and not implied by this roadmap edit.
- Any such abstraction must live in `player`/`statistics` (consumed by
  `simulation`), preserving the existing `simulation → player/statistics`
  dependency direction.
- M4.0's research into public/legitimate data sources is an offline,
  one-time model-building activity — the resulting population-model
  parameters must ship as locally embeddable data, never a runtime network
  dependency on the active-round critical path (`AGENTS.md` §2.2).
- M4 spanning both `player`/`statistics` and `simulation` concepts is
  consistent with existing practice (e.g. M3.3); the detailed M4 backlog
  (a separate future task) will need explicit per-task ownership.

## Scope of doc changes

- `docs/roadmap.md`: add M4.0, rewrite M4, leave M5 wording materially
  unchanged (per explicit instruction), update the status callout only if
  needed.
- `docs/prd.md`: update the M4–M5 functional-scope bullet for consistency.
- `docs/strategy-engine.md`: update the M4 forward-pointer/status note and
  the `simulation` planned-responsibilities section to reflect the broader
  M4 scope; keep Monte Carlo as the initial simulation technique, not the
  abstraction.
- `docs/player-model.md`: update the one-line M4 forward pointer for
  consistency (population/personalisation, not just "Monte Carlo
  simulation").
- `docs/backlog.md`: add candidate items capturing the open questions M4.0
  must resolve before M4 implementation (new shared abstraction / new
  dependency as future ADR triggers).
- `docs/architecture.md`, ADRs: no edit — reviewed, no inconsistency
  requiring a change (avoid documentation churn).
- `CHANGELOG.md`: add an `[Unreleased]` entry under a `### Changed` heading.

## Tasks

Single task, performed directly by the Orchestrator (documentation only, no
domain engineer implementation required):

1. Edit the six documentation files listed above on feature branch
   `agent/m4-roadmap-redefinition`.
2. Run the local quality gate (`scripts/check.sh`) to confirm no regression
   (docs-only change, but gates must still pass per `AGENTS.md` §8).
3. Adversarial Reviewer reviews the documentation diff for internal
   consistency, ADR-boundary correctness, and adherence to the instructions
   above.
4. Integrator commits, pushes, and opens a draft PR.

## Parallelism

Not applicable — single documentation task, no overlapping-file conflicts.

## Escalations

None. Architect review confirmed no `NEEDS_DECISION` trigger applies to this
roadmap-only edit.
