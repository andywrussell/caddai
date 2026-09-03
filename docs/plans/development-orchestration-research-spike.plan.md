# Platform spike - Development orchestration architecture

> Status: Phase 1 research and proof-of-concept planning only. This plan does
> not adopt an orchestration runtime, create infrastructure, change CaddAI's
> production architecture, or authorize Phase 2.

## Goal

Determine which development orchestration architecture CaddAI should test so
specialist agents can execute bounded engineering tasks with less manual prompt
passing, while GitHub remains authoritative and Andy retains merge and binding
architecture-decision authority.

Tracking issue: [#97](https://github.com/andywrussell/caddai/issues/97).

## Scope

Phase 1 covers current repository and GitHub-state inspection, fresh first-party
research, qualitative comparison of four candidate architectures, security and
state-ownership analysis, and a measurable Phase 2 PoC design.

It is independent of M5 product work. ADR 0008 and PR #96 were confirmed merged
before this spike proceeded. Issue #82 remains open at project Status `Backlog`
and is not started by this work.

## Working hypothesis and disconfirming check

**Hypothesis:** the first Phase 2 candidate should be a GitHub-first hybrid in
which GitHub Issues, branches, commits, draft pull requests, CI, ADRs, and human
decision records are authoritative; OpenClaw is a replaceable interactive
coordinator and local execution adapter; and GitHub Agentic Workflows are used
only for bounded event-driven experiments while they remain in Public Preview.

**Cheap disconfirming check:** execute the same approved fixture task through
the current manual baseline and the GitHub Agentic Workflows-only path before
crediting OpenClaw with unique value. If GitHub-native execution meets the
operator, recovery, model-routing, and human-gate criteria with lower complexity,
the hybrid hypothesis is rejected. The full framework-removal and clean-M3 tests
must also succeed without copying OpenClaw runtime state.

This is a recommendation for a PoC, not a binding architecture decision.

## Questions investigated

- Where should authoritative work, decisions, policy, credentials, and
  disposable execution state live?
- Can OpenClaw express CaddAI's role sequence, bounded nesting, model and
  reasoning routing, isolated worktrees, interruption recovery, and Telegram
  interaction?
- Can GitHub Agentic Workflows provide enough GitHub-native orchestration to
  avoid OpenClaw or a hybrid?
- Can Copilot Max be the primary model-access route through a native provider,
  Copilot-owned coding harness, or ACP worker, and how can actual routing and AI
  credit use be verified?
- How should human decision and merge gates be enforced technically and survive
  loss of sessions, the Gateway, Telegram, or the local machine?
- Is a dedicated `caddai-dev-orchestrator` repository needed for the PoC?
- Can a clean 2024 M3 Mac reproduce the setup using only GitHub, declarative
  configuration, documented prerequisites, and freshly supplied secrets?
- Can the design coordinate two disposable repositories without approving a
  CaddAI repository split?
- Does local worker concurrency provide useful throughput before hardware is
  considered?

## Sources

Repository sources include `AGENTS.md`, the product and architecture documents,
the M5 plan and issues, ADR 0008, the existing multi-repository research, current
agent definitions, the CI workflow, and GitHub Project field conventions.

Fresh external research used first-party sources current on 2026-09-03:

- OpenClaw documentation and release `v2026.8.2`.
- GitHub Copilot plan, model, billing, CLI, SDK, and agent documentation.
- GitHub Agentic Workflows documentation and `github/gh-aw` release `v0.88.2`.
- GitHub Actions, rulesets, token-permission, GitHub App, and Projects
  documentation.

Third-party reports may inform maturity risks but do not establish supported
product behaviour. Unsupported and undocumented capabilities are kept distinct.

## Alternatives

### A - Current manual workflow

Andy delegates through ChatGPT and VS Code/Copilot agents, with GitHub holding
the resulting issues, branches, PRs, and CI. This is the control and fallback.

### B - OpenClaw-first

OpenClaw owns interactive orchestration and specialist delegation, provisions
local worktrees, and reports through Telegram. GitHub receives durable outputs.
This option must prove that local session and workboard state do not become the
only usable work graph.

### C - GitHub Agentic Workflows-first

GitHub events invoke agentic workflows, safe outputs dispatch repository-local
workers, and GitHub owns execution records. This option has the smallest
conceptual state split but currently depends on a Public Preview platform.

### D - GitHub-first hybrid

OpenClaw handles interactive and long-running local coordination; GitHub and
deterministic Actions own durable work, CI, and gates; Agentic Workflows handles
selected scheduled/event-driven tasks. Overlap is forbidden unless a PoC shows
why two orchestration surfaces are necessary.

## Architect input

The Architect found the spike framing sound and confirmed no ADR is needed for
research or an isolated, explicitly non-authoritative PoC. The Architect's first
candidate was Option C, with Option A as the strongest fallback, and challenged
Option D to prove unique OpenClaw value through an ablation test. The following
constraints are incorporated:

- GitHub must contain all information needed to reconstruct and resume work.
- Runtime prompts, sessions, caches, clones, and worktrees are disposable.
- Dispatches require correlation and idempotency keys.
- Human decisions require an explicit GitHub record; merge is not implicit
  architecture approval.
- A dedicated orchestration repository should be deferred unless the PoC proves
  a durable ownership boundary that the CaddAI repository cannot express.
- Cross-repository tests use disposable fixtures and exact SHAs; they make no M6
  topology decision.
- Durable task contracts name capabilities and permissions, not providers or
  permanent model IDs.

The research recommendation differs narrowly from the Architect's initial
preference: it proposes testing a constrained hybrid first because Telegram,
persistent local coordination, heterogeneous local harnesses, and managed
worktrees are central user requirements. Phase 2 must run the Architect's
GitHub-native ablation first and reject the hybrid if those features do not
produce measurable additional value.

## Tasks and acceptance criteria

### Task 1 - Verify authoritative current state

Owner: CaddAI Orchestrator.

Acceptance criteria:

- Confirm current `main`, ADR 0008/PR #96 merge, issues #11/#82/#97, Project
  fields, agent definitions, and CI from GitHub and the repository.
- Correct issue #97 artifact paths without introducing Project field options.
- Keep #82 at `Backlog` and make no M5 dependency or source change.

### Task 2 - Research candidate platforms and access routes

Owner: CaddAI Orchestrator, with Architect challenge.

Acceptance criteria:

- Use current first-party OpenClaw and GitHub sources.
- Distinguish supported, preview, experimental, undocumented, and PoC-required
  claims.
- Compare OpenClaw native Copilot, Copilot-owned coding harness, and ACP/external
  worker routes.
- Record model-selection, reasoning-control, observability, cost, permissions,
  recovery, and lock-in limits in a claim-to-source ledger with exact versions,
  maturity labels, and CaddAI-specific PoC gaps.

### Task 3 - Define state, security, and portability invariants

Owner: CaddAI Orchestrator, with Architect and QA review.

Acceptance criteria:

- Classify every material state item by owner, source of truth, and recovery.
- Design an Andy-only, DM-only initial Telegram surface.
- Keep all secrets outside Git and specify fresh authentication on each machine.
- Forbid migration of `~/.openclaw`, sessions, pairing databases, hidden memory,
  cached credentials, and runtime worktrees to the M3.
- Require technical merge prevention and durable human-decision records.

### Task 4 - Design the Phase 2 PoC

Owner: CaddAI Orchestrator, with QA review.

Acceptance criteria:

- Specify tests A-K with objective evidence and pass/fail criteria.
- Run symmetric manual, GitHub-native, OpenClaw-first, and constrained-hybrid
  arms against the same versioned fixture oracle.
- Verify actual provider, model, and reasoning level rather than accepting
  configuration as proof; an unobservable reasoning level is a failed or
  inconclusive route, not a pass.
- Measure Copilot credits using baseline and before/after readings while
  controlling concurrent use, with repeated trials and a predeclared
  reconciliation tolerance.
- Compare one, two, and four active workers using end-to-end throughput and
  machine-pressure metrics.
- Include two-repository coordination, interruption recovery, clean-M3 bootstrap,
  framework removal, attempted merge, negative human-gate cases, duplicate
  delivery, concurrent dispatcher intents, and a forced stop after the second
  rejected fix.

### Task 5 - Review, integrate, and publish research

Owner: CaddAI Orchestrator and Integrator.

Acceptance criteria:

- Architect, QA, and Adversarial Reviewer verdicts are recorded.
- `docs/research/development-orchestration-architecture.md`, this plan, and
  `CHANGELOG.md` are the only intended tracked file changes.
- Full local quality gates pass.
- A draft PR closes only issue #97 and is never merged by an agent.

## QA expectations

QA must reject a PoC that proves only installation, startup, Telegram delivery,
or acceptance of a model name. It must also reject recovery that copies old
runtime state, session-only decisions, unmeasurable cost claims, prompt-only
merge controls, or tests whose only success signal is CPU utilization.

## Parallelism

Independent read-only source research can run concurrently. GitHub mutations,
artifact edits, reviews, integration, and PR creation remain serialized. No
domain engineer is assigned because no product subsystem is changed.

## Proposed Phase 2

Subject to explicit human approval, test a GitHub-first hybrid with:

- GitHub Issues/Project, branches, commits, draft PRs, checks, ADRs, and decision
  comments as the durable control plane.
- OpenClaw pinned to a tested version as a disposable interactive coordinator,
  with native specialist roles, bounded delegation, managed worktrees, and an
  Andy-only Telegram adapter.
- Copilot Max tested through the native OpenClaw provider for reasoning roles and
  the Copilot coding harness for engineering work; ACP retained as the provider-
  neutral comparison route.
- GitHub Agentic Workflows tested only for bounded event-driven tasks and the
  OpenClaw ablation, never as the only recovery or correctness mechanism while
  in Public Preview.
- Configuration templates and verification scripts initially kept with the
  disposable PoC material; no dedicated permanent orchestration repository is
  created until evidence shows it is warranted.

## Intentionally unexecuted actions

- No OpenClaw, plugin, coding harness, or provider installation.
- No OpenClaw authentication or significant AI-credit experiment.
- No Telegram bot, token, pairing, webhook, group, or dashboard setup.
- No `andywrussell/caddai-dev-orchestrator` or fixture repository creation.
- No source, tests, runtime architecture, GolfState, issue #82, M5 dependency,
  M6 topology, repository split, or Project Area-option change.
- No ADR, architecture adoption, production service, merge, auto-merge, or
  protected-branch change.

## Escalations

Phase 1 raises no binding decision. Phase 2 requires a new human approval before
installing OpenClaw, creating bots/repositories/apps or credentials, enabling a
preview/cloud service, changing rulesets, spending material credits, or adopting
any orchestration architecture. Binding adoption after the PoC should be handled
as a separate ADR-backed decision.

## Review record

- Architect: initial review complete. Spike framing approved; GitHub-native
  execution must be tested before hybrid complexity is credited.
- QA: `APPROVE` after one test-design repair. The fixed oracle, negative cases,
  repeated trials, routing proof, cost reconciliation, hardware thresholds, and
  independent multi-repo/merge/removal gates are objectively falsifiable.
- Adversarial Reviewer: `APPROVE` after one repair. The final design uses a
  deterministic GitHub single writer, separately authenticated Andy decisions,
  a route-specific permission matrix, symmetric A-D trials, and technical
  Andy-only default-branch update tests.
- Integrator: `PASS` on 2026-09-03. Documentation diff/whitespace checks and
  all required quality gates passed (`791` tests); pytest required clearing a
  local macOS `hidden` flag from `.venv` path files, with no repository change.
