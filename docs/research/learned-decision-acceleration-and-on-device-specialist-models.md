# Learned decision acceleration and on-device specialist models

> Status: non-binding research for [issue #99](https://github.com/andywrussell/caddai/issues/99).
> Documentation-only scope approved by the human on 2026-10-27. No model,
> training, runtime, interface, dependency, ADR, milestone, or implementation
> is approved here. Repository baseline: `main` at `e677418`.

## Recommendation

Profile the authoritative engine before considering learned acceleration.
Compare deterministic optimisations and lightweight numerical ML before an
LLM. LLM-as-Jev makes predefined-option scoring worth investigating, and
BitNet makes efficient inference plausible, but neither establishes golf
decision quality or acceptable end-to-end mobile cost. Combining them is
an untested CaddAI hypothesis, not a result of either paper.

Do not introduce a learned interface in M6 without a demonstrated bottleneck.
M9 is a possible future comparison location, not a mandatory learned-model
deliverable. Preserve M13's explanation-only scope. No M15 is created or
scheduled and no existing milestone dependency changes.

## Governing contracts and dependencies

- [ADR 0001](../adr/0001-deterministic-strategy-engine.md): the engine decides;
  an LLM may explain a finished recommendation, never supply or override it.
- [ADR 0005](../adr/0005-offline-first-active-round-architecture.md): the full
  active-round core must remain locally executable without network requests.
  Model download/update must never become an in-round prerequisite.
- [ADR 0006](../adr/0006-player-shot-distribution-bivariate-student-t.md) and
  [ADR 0007](../adr/0007-population-prior-replaceability.md): preserve M4's
  authoritative `PlayerShotDistribution`, its heavy-tailed joint shot-production
  representation, population-prior provenance, personalisation, and seeded
  Monte Carlo pipeline. Population-prior replaceability does not authorise a
  learned strategy or new dependency.
- [ADR 0008](../adr/0008-golf-state-domain-contract.md): `GolfState` is neutral
  resulting state, not strategy, selected-target context, or penalty procedure.
- The [M5 plan](../plans/m5-detailed-implementation-plan.md) preserves neutral
  `E_base`, benchmark `SG_base`, full retrievable candidate value distributions,
  and selection by mean benchmark SG. It does not add player adjustment,
  aggression, score-sensitive policy, or a new risk objective. Numeric baseline
  approval is a separate unresolved gate; research cannot bypass it.

Currently implemented: M4 supplies intrinsic carry/landing-relative outcomes
and an optional environment transform, not a completed course-relative SG
decision pipeline. M5 mapping, baseline evaluation, and candidate selection
remain planned. A meaningful acceleration experiment depends on those reference
semantics existing first; the legacy closest-carry recommendation is not an
adequate substitute. See [architecture](../architecture.md) and
[strategy-engine status](../strategy-engine.md).

## Primary research evidence

Sources were retrieved during the issue's research on 2026-10-27. These are
author-reported research results, not independently reproduced CaddAI results.
Pin paper/model/runtime versions in any future experiment.

### LLM-as-Jev

[Li and Wagle, LLM-as-Jev, arXiv:2610.02076v3](https://arxiv.org/abs/2610.02076v3)
describes architecture-preserving categorical scoring over predefined options,
including a training-free readout and fine-tuning with KL-divergence anchors.
The framework does not reproduce proprietary Jev's unknown architecture or
training recipe. Joint option conditioning/readout avoids free-form answer
generation; it still incurs prompt processing and option-scoring costs.

The paper evaluates Qwen3.5-4B and Qwen3-0.6B on classification/decision
benchmarks, including 231 public JevBench items and Banking77. It reports
81.4% frozen 4B JevBench accuracy, versus 84.0% with its anchored LoRA recipe
and 94.8% with a 4,096-token thinking budget (sections 4.2, 4.4, 4.5).
These are different configurations and cost profiles, not interchangeable
accuracy claims. Section 4 describes data iterations informed by public-set
error analysis; those exploratory results are not a clean golf holdout.
Appendix L distinguishes FLOP-based cost estimates from measured latency,
notes an unoptimised FP32 implementation, and explains that thinking adds
sequential decoding. Neither API price estimates nor general benchmark accuracy
establish phone latency, battery savings, or safe candidate pruning.

**CaddAI hypothesis:** a stock or adapted readout could order a supplied list
of club/target candidates or classify user intent. No cited test establishes
golf geometry reasoning, numeric SG accuracy, severe-miss risk calibration,
OOD reliability, or improvement over a small numeric model. Larger option
sets increase input cost; candidate order, labels, wording, and numeric
serialization require permutation and robustness tests.

### BitNet b1.58

[Ma et al., The Era of 1-bit LLMs, arXiv:2402.17764v1](https://arxiv.org/abs/2402.17764v1)
describes native ternary weights (`-1`, `0`, `+1`) and 8-bit activations.
The 1.58-bit label reflects three weight values, not total application memory
or a promise that every operation is 1.58-bit. This training recipe is not
equivalent to taking an arbitrary frozen LLM and losslessly quantising it.
Its mobile discussion is prospective, not a CaddAI phone benchmark.

[Ma et al., BitNet b1.58 2B4T Technical Report, arXiv:2504.12285v2](https://arxiv.org/abs/2504.12285v2)
reports a native 2B-parameter model trained on 4T tokens and released CPU/GPU
inference implementations. Section 4 reports non-embedding memory and estimated
decoding energy comparisons; neither is whole-app resident memory or measured
phone energy. Section 5.1 describes custom CUDA kernels and packing four
ternary values into an 8-bit integer. It explicitly notes limited native
commodity-GPU support for the required operations. Efficient CPU implementation
is relevant evidence, not proof of iOS/Android packaging or NPU acceleration.

**CaddAI hypothesis:** a compatible low-bit specialist might reduce local model
cost. Measure embeddings, activations, KV/cache/workspace, tokenisation, load
time, context length, prefill, option readout, and sustained thermal behaviour,
not just packed weights or decode tokens/second. A no-generation decision
readout may be prefill-bound, so decode speedups may not transfer. Licences,
device/runtime compatibility, supported operations and reproducibility remain
unresolved; no runtime or model is selected.

### Can the approaches be combined?

Conceptually yes: Jev-style readout is an option-scoring method; BitNet is a
model/training and execution approach. However, the cited Jev experiments use
Qwen backbones, not BitNet. A BitNet backbone must support the readout's
tokenisation/logit access and option encoding. Adaptation, native-low-bit
training constraints and inference kernels must remain compatible. KL anchors
are not a safety guarantee. Test the readout, backbone change and precision
change separately before attributing any gain to their combination. Do not
assume a larger Qwen model and a smaller BitNet model form a controlled
precision comparison.

## Preference prediction is not value or risk evaluation

An option probability describes the model's categorical preference under its
training/prompt, not the physical probability of a shot outcome, the probability
of that candidate being optimal, or calibrated SG/risk uncertainty.
M5's benchmark remains:

`SG_base = E_base(current_state) - (1 + E_base(resulting_state))`.

Its expectation and adverse-tail/hazard summaries require the authoritative
shot-outcome and value pipeline, with the approved penalty-counting semantics.
A ranking-only model supplies neither an outcome distribution nor its SG tails.
Risk summaries do not authorise changing M5's mean-SG objective.

Learned candidate pruning can remove the otherwise optimal shot and thereby
change the eventual golf decision, even if the remaining candidates are fully
simulated. High confidence on retained options says nothing reliable about an
omitted candidate. Confidence-only fallback is not automatically sufficient;
even a calibrated average error rate does not certify individual exclusions.
Ordering every candidate without changing evaluation work saves no simulation.

Initially run learned proposals in shadow experiments only. Any future
decision-affecting pruning requires explicit human review, a defensible
independent exclusion/coverage argument, adversarial audits and full-engine
fallback; a statistically good benchmark alone cannot prove no-regret pruning.
Preserving authority requires more than placing a deterministic selector after
a learned shortlist. No production exception to ADR 0001 is proposed here.

## Comparison baselines and promising uses

| Approach | Potential use | Limitation to measure |
|---|---|---|
| Batched NumPy simulation/value lookup, prepared geometry and spatial filtering | Reduce work without a learned policy | Floating-point/replay parity, geometry-boundary correctness |
| Complete-key caching of pure geometry/value computations | Avoid repeated work | Version/input invalidation; do not persist a derived personalisation posterior contrary to M4's baseline/history contract |
| Common random numbers, variance reduction, sequential/adaptive sampling | Improve paired comparisons per sample | Preserve marginal outcomes, sample counts, tail precision and valid stopping uncertainty under heavy tails |
| Analytical approximations, deterministic dominance/bounds, coarse-to-fine targets | Reduce evaluation or candidate work | Bounds must be valid; heuristic pruning and finite target grids can also lose the best candidate |
| Linear/logistic models, small trees/boosted trees, compact MLP or lookup/interpolation surrogate | Numeric ranking, value approximation, sample-budget prediction | OOD, discontinuous hazard edges, tail underestimation, runtime cost and calibration |
| Jev-style readout, optionally on a compatible low-bit backbone | Supplied-candidate ordering; separately, typed intent classification | Prefill cost, numeric fidelity, option-order sensitivity, calibration and specialised training burden |

These are experimental alternatives, not selected dependencies or algorithms.
NumPy/Pydantic-compatible simple baselines should precede adding a runtime.
Best initial research use is predicting where more evaluation is needed, or
ordering candidates for an independently justified evaluator. Numeric models
are a more direct starting point than a language model for structured SG inputs.
An intent parser needs its own labelled utterances, units/negation tests,
schema validation, ambiguity/abstention and manual-input fallback; it must not
invent player data, risk policy, or targets. It is not added to M13 here.

## Required data and future experiment

This is a protocol proposal only: no dataset generation, training, model
download or device experiment is performed by this change.

1. **Profile first.** Once M5's approved pipeline exists, measure candidate
   generation, geometry, sampling, mapping, value lookup, and selection.
   Establish candidate counts and device latency/energy budgets. Stop if the
   conventional engine already meets them or another stage dominates.
2. **Freeze a reference.** Record engine SHA, full candidate set and stable
   identities, target frames, course geometry/version, player distribution and
   provenance, environment/config, value-model version, seeds and sample counts.
   Use the real production engine, not a reimplemented golf oracle. Produce
   higher-budget, repeated-seed reference evaluations with Monte Carlo error
   estimates, including uncertain near-ties. Reference SG is model-based truth,
   not proof of actual golfer outcomes; provisional model labels remain so.
3. **Construct and split scenarios.** Cover courses, club categories, ability,
   correlated/heavy-tailed misses, wind, forced carries, hazard edges, missing
   inputs, unsupported states and near-ties. Hold out entire courses/player
   profiles and condition ranges, not random near-duplicate rows. Include
   deliberately shifted/OOD and adversarial geometry cases. Preserve course and
   data licensing; any later personal-data use needs consent/privacy approval.
4. **Train only if separately approved.** Ranking requires complete-set
   engine labels with uncertainty; value surrogates need per-candidate means
   and outcome distributions, quantiles and hazard/penalty frequencies, not
   only winner IDs. Weight rare severe-miss cases deliberately and report
   natural-frequency performance separately. A preferred-candidate human label
   measures preference alignment, not SG. Unplayed alternatives in a decision
   journal are counterfactual predictions, not observed outcomes.
5. **Compare controlled arms.** Full reference; profiled deterministic
   optimisations; lightweight numeric models; frozen Jev readout; adapted
   readout only if warranted; compatible low-bit variant only if available.
   Use identical held-out candidates and input information, with no expensive
   full-engine labels leaked into timed inference. Where a matched model
   precision comparison is unavailable, state the confounding. Vary shortlist
   size and sample budgets, count all preprocessing/validation/fallback work,
   and retain full-engine shadow results for auditing.

### Measurable scorecard

Pre-register thresholds with a human before any future experiment; the following
defines measurements, not accepted numeric release limits.

| Dimension | Required measurements |
|---|---|
| Candidate recall | Fraction of scenarios retaining the full-engine optimum in top-k; recall of all statistically near-optimal candidates; breakdown by hazard/OOD slice and shortlist size |
| Decision regret | Reference mean SG of its best candidate minus reference mean SG of the experimental choice, in strokes/decision; mean, p95/p99, worst observed and confidence intervals accounting for Monte Carlo uncertainty |
| Value and risk | SG mean error; hazard/penalty probability absolute error and systematic underprediction; adverse-tail probability and quantile errors using predeclared SG cutoffs; invalid/unsupported counts |
| Confidence and shift | Calibration/Brier or reliability plots for explicitly defined events; error-versus-abstention coverage; OOD false negatives; candidate/label permutation and input perturbation stability |
| Latency | End-to-end p50/p95/p99 and worst observed; cold/warm start; prefill/readout separately; representative candidate counts and contexts; fallback-inclusive results |
| Memory and energy | Peak process and total-app resident memory, packaged/download size, load workspace/cache; measured joules/decision and representative round battery impact against idle baseline on named device/OS/runtime; sustained thermal throttling |
| Fallback | Frequency, trigger/reason, missed-trigger failures, extra latency/energy, and replay agreement with the full engine using the same seeds/config; model missing/corrupt, timeout, invalid output, unsupported state and OOD fault injection, all offline |

Report accelerator-only and fallback-inclusive costs; a fast path that often
falls back may be slower overall. Distinguish quantisation error, approximation
error, reference Monte Carlo noise and underlying golf-model calibration.
Independent full-set audit runs are necessary to detect confident pruning
failures; omitted-candidate risk cannot be inferred from shortlist confidence.
Fallback must return to the authoritative full candidate/evaluation path, not
a second reduced offline model. Existing unsupported-state handling must remain
visible rather than manufacturing a recommendation for an unsupported regime.

## Roadmap implications and reasons not to proceed

The [current roadmap](../roadmap.md) and milestone dependencies are unchanged.
M6 may consider measured model costs only if relevant to its bounded runtime
and system-boundary decisions; this note adds no seam requirement. M9's
reproducible production-engine harness could host an optional future experiment
after M5, starting with fixtures and extending with M7 packages. Its event
evaluation work still depends on M5/M8 shapes. M13 remains solely exploratory
on-device inference for M12 explanations; this note does not extend it to
strategy or intent parsing. No model implementation milestone is scheduled.

Do not proceed if profiling shows no meaningful bottleneck, conventional
optimisations meet the device budget, training labels are unstable or legally
unusable, a simpler numeric model wins, hazard/tail errors or confident misses
remain unacceptable, or fallback erases the savings. Also stop if packaging,
thermal/energy costs, runtime support, model maintenance/version drift, poor
reproducibility, or privacy/licensing burden exceed the measured benefit.
Unknown real-device performance and no golf-specific result in either paper
are evidence gaps, not reasons to assume success.

## HUMAN DECISION REQUIRED

Documentation-only research is approved; implementation is not. After the
reference engine and profiling evidence exist, the human must decide whether
to fund a bounded experiment at all, its data/licensing/privacy permissions,
devices, budgets, candidate-recall/regret/risk/fallback thresholds and stop
criteria. Any decision-affecting pruning needs separate explicit review of
how optimal candidates can be lost and how exclusions are checked; model
confidence alone is not adequate authorisation. Production model/runtime or
dependency adoption, public contracts, authority/boundary changes and any new
milestone require their own applicable approval/ADR process. Nothing here
authorises those actions or changes existing M4/M5 or M6/M9/M13 commitments.