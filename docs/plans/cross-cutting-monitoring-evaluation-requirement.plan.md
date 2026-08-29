# Cross-cutting MVP requirement: recommendation monitoring, evaluation, issue capture, calibration

## Goal

Capture, as documentation/planning only (no implementation), a cross-cutting
MVP requirement that the future CaddAI system must preserve enough
structured information to answer two distinct questions: (1) is the
product/system working correctly (operational monitoring), and (2) are
CaddAI's recommendations actually good (recommendation evaluation,
including decision-time candidate snapshots, counterfactual candidate
retention, and probabilistic calibration). Also record a lightweight
user-reported-issue capture requirement, an offline-first local-capture
requirement, an explicit non-design of the privacy architecture, and a
roadmap responsibility split across M5/M5.5/M6/M7. This must be raised
before further M4 implementation continues so M5/M6/M5.5 planning already
accounts for it.

## Architect input

CaddAI Architect (read-only) review findings:

- No conflict with ADR 0001 (deterministic strategy) — nothing here puts a
  monitoring/evaluation system on the decision path.
- No conflict with ADR 0005 (offline-first active round), provided the
  local-write-then-optional-sync framing survives verbatim: *recording*
  events (including e.g. "sync failed") is itself a local, offline-capable
  act; only export/sync is connectivity-enhanced.
- No new ADR required now: no new runtime dependency, no public API
  contract change (no `api` module exists yet), no canonical unit change,
  no module ownership change, no dependency-direction change, and no change
  to either the deterministic-strategy or offline-first principles — this
  is planning/roadmap scope-shaping, not an architectural decision.
- `docs/architecture.md`'s only genuine existing touchpoint is the
  "Offline-first active round" section's item 7 ("Recording player
  decisions and shot outcomes"). Add at most one clarifying sentence there
  distinguishing local recording (active-round core) from deriving
  operational/evaluation analytics from that record (connectivity-enhanced,
  may live in a separate component) — optional, not required elsewhere in
  that file, since `simulation`/`llm`/`api`/`cli` don't exist yet.
- Avoid collapsing operational monitoring and recommendation evaluation:
  don't list "user-reported issue" under both categories (it's an
  evaluation/quality signal); state the operational-vs-evaluation test
  explicitly once rather than relying on parallel example lists; keep the
  M5.5 scope additions as two separate bullets (operational observability
  architecture; evaluation-data architecture), not one clause.
- Keep wording aspirational/roadmap-level: no schemas, storage tech, or
  metric formulas — mirror the roadmap's existing self-limiting phrasing
  ("this is a planning-scope note only", "no concrete implementation types
  are locked in").
- M5 (issue #11) is mid-flight (PRs #65–67 just landed WHS/SG-framework
  text). The existing M5 distribution-aware requirement (candidates must
  carry expected SG / upside-downside / tail-penalty information, not
  collapse to one scalar) already functionally satisfies the
  "evaluation-ready" ask. Add at most one short cross-reference sentence in
  roadmap.md's M5 section; do not edit issue #11 itself — defer any
  issue-#11 changes to a future M5 planning sync so as not to collide with
  in-progress planning work.
- decision-journal.md (M6) and the M5.5 spike are the correct primary homes
  for the bulk of the new substance.

## Documents touched

- `docs/prfaq.md` — expand the existing "Does CaddAI store every shot I
  hit?" FAQ (and, if needed, an adjacent new FAQ) to state the
  monitoring-vs-evaluation distinction, decision-time snapshot idea,
  counterfactual candidate retention, calibration, lightweight feedback
  capture, and offline-first local capture, all as aspirational north-star
  framing consistent with the rest of the document.
- `docs/roadmap.md` — one short additive cross-reference sentence in M5;
  additive scope bullets in M5.5 (event contracts, storage/sync boundary,
  ownership, versioning, operational-observability architecture,
  evaluation-data architecture as two separate bullets); explicit
  monitoring-vs-evaluation split and MVP scorecard framing added at M6/M7
  where the roadmap already describes those milestones.
- `docs/decision-journal.md` — expand with: the operational-vs-evaluation
  distinction test, decision-time snapshot categories (identity/versioning,
  input context, candidate evaluations, decision, outcome), counterfactual
  candidate retention, calibration framing, user-reported issue capture,
  offline-first local-append-then-sync framing, and a brief privacy-boundary
  note — all at the same conceptual-bullet altitude the document already
  uses, no concrete schema.
- `docs/architecture.md` — one clarifying sentence in the "Offline-first
  active round" section distinguishing local recording from
  operational/evaluation analytics derived from it. No other changes (no
  natural boundary yet for the rest).
- `docs/adr/README.md`/new ADR — none required (see Architect input).
- GitHub issue #11 — not touched (mid-flight; defer).
- `CHANGELOG.md` — entry under `[Unreleased]` noting the documentation
  addition.

## Tasks

All tasks are documentation-only edits performed directly by the
Orchestrator (no domain engineer subagent required — no production code,
tests, or module ownership boundaries are involved).

1. Edit `docs/prfaq.md`: expand the "Does CaddAI store every shot I hit?"
   FAQ into the fuller monitoring/evaluation picture; keep the aspirational
   present-tense PRFAQ style used throughout the document.
   - Acceptance: the FAQ distinguishes "is the system healthy" from "are
     recommendations good"; mentions decision-time snapshot,
     counterfactual candidates, calibration, lightweight feedback, and
     offline-first local capture; does not specify a storage technology,
     schema, or monitoring stack.
2. Edit `docs/roadmap.md`: add the M5 cross-reference sentence; add the
   M5.5 scope bullets (as two separate items); add M6/M7 responsibility
   framing consistent with `decision-journal.md`.
   - Acceptance: M5/M6/M5.5/M7 responsibility split is legible; no roadmap
     milestone is renumbered; existing "planning-scope note only" style is
     preserved; M7's existing scope gains the local-event-capture /
     lightweight-issue-reporting / optional-sync framing.
3. Edit `docs/decision-journal.md`: add the monitoring-vs-evaluation test,
   decision-time snapshot category list, counterfactual-candidate framing,
   calibration framing, user-reported-issue framing, offline-first
   local-append-then-sync framing, and privacy-boundary note.
   - Acceptance: existing "Explicit non-goals for now" section is preserved
     and extended (no storage tech, no schema, no consent/account system
     implied); the document explicitly states that a single realised
     outcome must not be read as proof of recommendation quality.
4. Edit `docs/architecture.md`: add one sentence to "Offline-first active
   round" distinguishing local recording from downstream analytics.
   - Acceptance: no subsystem table row added (no such subsystem exists
     yet); no dependency-direction rule changed.
5. Update `CHANGELOG.md` under `[Unreleased]`.

## Parallelism

Tasks 1–4 touch different files and can be edited in any order (all done by
the Orchestrator directly, sequentially, since these are simple docs edits
with no risk of file collision). Task 5 depends on 1–4 being finished.

## Escalations

None. Per Architect review: no ADR required, no conflict with ADR
0001/0005, no dependency/API/unit/ownership change. If the Adversarial
Reviewer or Integrator identifies wording that implies a network
prerequisite for active-round function, or an implied schema/technology
commitment, that must be fixed before merge — see `AGENTS.md` §14 if a
genuine architectural conflict is found (not expected here).

## Non-goals (explicit)

No telemetry schema, telemetry persistence, monitoring stack (Grafana/
Prometheus/etc.), analytics warehouse, cloud event ingestion, evaluation
notebook, calibration calculation, A/B testing, feedback UI, or sync/
account/privacy system is implemented as part of this task.
