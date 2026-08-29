# Decision journal

> Status: describes a **future** concept (milestone M6). No storage or data
> model is implemented yet — this document exists to guide that eventual
> design, not to describe existing functionality.

## Purpose

Capture what CaddAI recommended, what the player actually did, and what
happened, so both **player behaviour** and **strategy quality** can be
evaluated over time. This is the feedback loop that lets the strategy engine
(and, later, its statistical inputs) be validated against real outcomes
rather than assumptions alone.

## Monitoring vs. evaluation

The decision journal is the primary data source for a distinct concern from
day-to-day **operational monitoring**, and the two must not be collapsed
into one generic "logging" requirement:

- **Operational monitoring** asks *is the system behaving correctly?* —
  e.g. was a recommendation produced, did the system fall back to degraded
  behaviour, was course data missing/stale, was GPS confidence too low to
  trust, how long did the recommendation take, did an optional cloud sync
  fail. This is about pipeline/application health.
- **Recommendation evaluation** (this document's primary concern) asks *are
  CaddAI's recommendations actually good?* — which requires the
  decision-time record described below, evaluated over time, not just
  whether the system ran without error.

A single test to keep them apart: operational monitoring can be answered
from the system's own behaviour alone; recommendation evaluation requires
comparing what CaddAI predicted, what the golfer did, and what the ball
actually did. The two may eventually be served by different tooling or
components entirely (e.g. operational metrics/logs/traces/alerts vs.
evaluation analytics/calibration analysis) — this document does not assume
they share a service, repository, or storage technology.

## Planned record shape

For each shot, the decision journal will eventually record:

- **Situation** — the position, lie, hole geometry, and conditions (wind,
  elevation, etc.) at the time of the shot.
- **Recommendation** — the deterministic engine's structured output: target,
  club, intended shot shape, risk assessment.
- **Recommendation rationale** — which inputs (simulation results, expected
  strokes comparison, risk trade-off) drove the recommendation.
- **Player decision** — the club/target the player actually chose, which may
  differ from the recommendation.
- **Shot outcome** — the actual observed result of the shot (e.g. via GPS or
  manual entry).
- **Resulting lie** — the lie the ball ended up in.
- **Resulting position** — where the ball ended up.

### Decision-time snapshot

The record above must preserve enough **immutable decision-time context**
to support evaluation later, conceptually grouped as:

- **Identity/versioning** — a recommendation/decision identifier, round/hole
  context, timestamp, and the version of the course data, player model,
  strategy/config, and expected-strokes/Strokes Gained model in effect at
  the time.
- **Input context** — the relevant player state, the selected/intended
  target, lie/context where available, environmental inputs, and the
  course state relevant to the recommendation.
- **Candidate evaluations** — for each candidate club/target CaddAI
  considered (not only the one recommended): expected strokes/expected
  Strokes Gained, risk/downside metrics, scoring probabilities, penalty/
  hazard probability, and whatever other distribution summaries M5 planning
  settles on.
- **Decision** — the recommended option, and whether the golfer accepted,
  modified, or ignored it, including the actual club/target chosen where
  known.
- **Outcome** — the observed `ShotRecord`/endpoint, penalty/outcome flags
  once supported, the resulting golf state, and realised Strokes Gained
  where available.

No single event schema is fixed by this document — the M5/M6 (and M5.5)
architecture passes define the concrete, linked contracts.

### Counterfactual candidate information

Where CaddAI evaluated several candidates (e.g. driver at an expected
Strokes Gained of +0.20 with an 8% penalty probability vs. 3-wood at +0.14
with a 2% penalty probability), the non-chosen candidates' pre-shot
evaluations should also be preserved. If the golfer plays 3-wood, CaddAI
never observes what driver would truly have produced — retaining the
candidate evaluation only preserves CaddAI's own reasoning at the time, not
an observed outcome. This supports later analysis of recommendation policy,
risk calibration, golfer overrides, and model changes, but any such
candidate must never be presented as observed ground truth.

### Probabilistic calibration

Evaluating CaddAI's probabilistic models eventually needs to include
**calibration**, not only average realised scores — for example, whether
roughly 10% of comparable outcomes result in a penalty when CaddAI predicted
roughly a 10% penalty probability, whether observed outcomes fall inside
predicted dispersion regions at the expected rates, and whether predicted
scoring/Strokes Gained distributions are calibrated. Calibration should be
expected to improve as personal `ShotRecord` evidence accumulates, and
should eventually help evaluate population priors, personalisation,
dispersion modelling, environment coefficients, hazard probabilities, and
the recommendation policy itself. No calibration metric is implemented by
this document.

## User-reported issues / feedback

Golfers/testers should eventually be able to flag a recommendation that
looks wrong (e.g. wrong club, wrong target, risk judged too high or too
low, incorrect lie/context, wrong course data, wrong GPS/location, or
other). This should not require feedback after every shot — an
occasional, user-triggered, or post-round report is sufficient. When a
report is made, the relevant recommendation/decision context should be
associated automatically, so the golfer/tester does not have to manually
reconstruct the situation.

## Offline-first capture

Consistent with the offline-first active-round principle (`AGENTS.md`
§2.2, [ADR 0005](adr/0005-offline-first-active-round-architecture.md)),
appending a decision/evaluation event locally during a round must not
depend on connectivity — this includes recording that a connectivity-
dependent action (e.g. an optional cloud sync) failed. Only exporting or
synchronising the accumulated events afterwards is connectivity-enhanced,
and losing connectivity must never affect shot simulation, recommendation,
round tracking, or decision logging.

## Privacy boundary (not designed here)

Any eventual synchronisation/export of decision-journal or evaluation data
should be expected to require explicit product privacy choices,
pseudonymous identifiers where practical, data minimisation, user control
over upload/export, and keeping raw evaluation data private from unrelated
consumers. This document does not design consent, account, or privacy
systems — that is future work.

## Intended uses

- Evaluate strategy quality: did following (or deviating from) the
  recommendation correlate with better outcomes?
- Evaluate and refine player statistical models: does a player's actual
  dispersion match the model used to generate the recommendation?
- Provide a dataset for future refinement of the simulation and strategy
  models.
- Support an MVP evaluation scorecard, e.g. recommendation availability
  rate, recommendation latency, acceptance/override rate, realised Strokes
  Gained after recommendations vs. after overrides, predicted-vs-realised
  penalty/hazard frequency, probabilistic calibration, bad-recommendation
  report frequency and reason categories, and missing/poor course-data or
  unsupported/fallback event frequency. Observational comparisons such as
  "accepted recommendations had better realised Strokes Gained than
  overrides" must not be read as proof of causal superiority — proper
  experiment/policy comparison is future work, not implied here.

## Explicit non-goals for now

- No storage technology is selected. Selecting one (file-based, embedded, or
  hosted database) is a decision deferred to M6 and requires an ADR plus
  human approval per `AGENTS.md` §14 (database/infrastructure selection is
  an escalation trigger). Whatever is chosen must support a local write path
  for recording decisions/outcomes, since that is active-round core
  functionality (`AGENTS.md` §2.2, see
  [ADR 0005](adr/0005-offline-first-active-round-architecture.md)); any
  round-history synchronisation to a remote store is connectivity-enhanced,
  never a prerequisite for recording during a round.
- No implementation of recording, querying, or persistence exists yet.
- No event schema, evaluation-dataset format, calibration metric, A/B-test
  design, feedback UI, or monitoring/analytics technology is specified or
  implemented here.

