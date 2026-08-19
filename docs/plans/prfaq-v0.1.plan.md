# Plan: Add CaddAI PRFAQ v0.1 (issue #33)

## Goal

Add the approved CaddAI PRFAQ v0.1 as a first-class product document
(`docs/prfaq.md`) — the long-term customer-experience/product-principles
north star — and update repository-context documents so its relationship to
the PRD, architecture/ADRs, and roadmap is clear. Documentation-only change;
no production code is modified.

## Architect input

The CaddAI Architect subagent reviewed the PRFAQ content against
`AGENTS.md`, `docs/prd.md`, `docs/architecture.md`, `docs/roadmap.md`, and
ADRs 0001/0005. Findings:

- **No material contradictions** with the deterministic-strategy principle,
  the offline-first active-round principle, the subscription/commercial
  framing in `prd.md` §4, or the hardware/LLM sequencing in the roadmap
  (M8–M11). The PRFAQ closely paraphrases ADR 0001 and ADR 0005 rather than
  conflicting with them.
- The press-release marketing voice uses present tense for target-state
  capability (e.g. "CaddAI can understand carry distances...", the
  `Confidence: 84%` worked example) that does not exist yet at the current
  M2-complete/M3-in-progress state. This isn't a contradiction of the source
  docs (which already treat this as future work) but needed a framing note
  in the file so a reader doesn't infer current capability.
- No ADR is required to add this document: it's a documentation addition
  that restates, rather than changes, approved dependencies, API contracts,
  units, module ownership, dependency direction, or the deterministic
  strategy/offline-first principles (`AGENTS.md` §13).
- Recommended: add a row to the `AGENTS.md` §12 documentation map near
  `docs/vision.md`/`docs/prd.md`, and add an explicit relationship note
  inside `docs/prfaq.md` itself so it's read as aspirational north-star
  vision, not current implementation status.

## Tasks

All tasks performed by the Orchestrator directly (documentation-only change;
no domain-engineer subsystem code is touched).

1. **Add `docs/prfaq.md`** — the approved PRFAQ v0.1 content, with a short
   framing note clarifying its relationship to the PRD/architecture/roadmap
   and that it describes target-state vision, not current implementation.
   - Acceptance: file exists, contains the supplied content, preserves the
     PRFAQ author's substance verbatim.
2. **Update `AGENTS.md` §12** — add `docs/prfaq.md` to the documentation
   map; add a short paragraph distinguishing PRFAQ ("what experience are we
   trying to create") from PRD ("what must the product do"),
   architecture/ADRs ("how must the system be designed"), and roadmap
   ("when are capabilities built"); note that agents proposing significant
   new product functionality should check consistency with the PRFAQ, that
   PRFAQ must never override an explicit ADR/architectural constraint, and
   that conflicts must be escalated rather than guessed.
   - Acceptance: distinction present; escalation rule present; no change to
     dependency table, module-ownership table, or the deterministic-strategy/
     offline-first principle sections.
3. **Update `.github/copilot-instructions.md`** — one concise line noting
   significant product decisions should be checked against `docs/prfaq.md`.
   - Acceptance: single short addition, not verbose.
4. **Update `README.md`** — add `docs/prfaq.md` to the documentation links
   so a new developer can discover it.
5. **Update `docs/prd.md`** — a short reference noting the PRFAQ captures
   long-term customer/product vision, without duplicating its content.
6. **Update `docs/roadmap.md`** — add a reference only if it aids sequencing
   context; do not copy PRFAQ content.

## Parallelism

All tasks are documentation edits across independent files; no subsystem
code is touched. Performed sequentially by the Orchestrator since they are
small and interdependent (all reference the same new file).

## Escalations

None. Architect confirmed no ADR is required and no material contradiction
exists with existing product/architecture/roadmap documents.
