---
applyTo: "docs/**/*.md"
---

# Documentation conventions

- Write concise, technical prose. Prefer short paragraphs, bullet lists, and
  precise terms over marketing language.
- Clearly distinguish **current implementation** from **future/intended
  design**. Use explicit markers such as "Currently implemented:" and
  "Planned:" or a status note at the top of the document when a whole doc
  describes a not-yet-built system.
- Never claim a feature, module, or behaviour exists if it has not been
  implemented and merged. If unsure whether something is implemented, check
  `src/caddai/` before writing about it as fact.
- Significant architectural decisions (new dependency, changed module
  ownership, changed canonical units, changed public API contract, dependency
  direction changes) require an ADR under `docs/adr/`, following the format in
  `.github/skills/architecture-decision/SKILL.md`. Reference the ADR from
  other docs instead of re-explaining the decision.
- Keep documents in their lane: product/vision in `vision.md`/`prd.md`,
  structural decisions in `architecture.md`, plans in `docs/plans/`, durable
  engineering rules in `AGENTS.md`. Don't duplicate content across documents —
  link instead.
