# 0006. `PlayerShotDistribution` as a bivariate Student-t shot-production representation

## Status

Accepted

## Context

[M3](../roadmap.md) gave `player`/`statistics` two independent univariate
primitives: `CarryDistribution` (carry, Gaussian) and `DirectionalDispersion`
(lateral offset, Gaussian, with a fixed sign convention — negative left, zero
on-line, positive right of the intended target line, independent of
handedness). These are sufficient for simple carry/lateral summaries but
cannot express correlation between carry and lateral outcome, cannot express
heavier-than-Gaussian tails, and treat carry/lateral as unrelated draws.

The M4.0 research spike (issue #47,
[docs/research/m4-probabilistic-golfer-model.md](../research/m4-probabilistic-golfer-model.md))
reviewed public golf-performance research to determine what shot-production
representation M4 (`player`/`statistics`/`simulation`) should adopt for the
probabilistic outcomes that `simulation` (and, downstream, `strategy` in M5)
will consume. The research and a subsequent CaddAI Architect review
converged on rejecting an independent-Gaussian model:

- Exploratory analysis of the public CaddieSet dataset found lateral
  outcomes were non-normal in 10 of 11 golfer/club cells tested, with median
  lateral excess kurtosis around 1.37 (heavier-than-normal tails) and
  material, sign-varying carry/lateral correlation (roughly −0.34 to +0.56
  across cells).
- Broadie's amateur-scoring research independently observes that a small
  number of very poor ("awful") shots materially affects amateur scores —
  a thin-tailed model would understate this strategy-relevant risk.
- Driver studies (Betzler et al. 2012/2014) support handicap as a predictor
  of shot-to-shot production variability, motivating a population-prior
  input to whatever representation is chosen, but do not by themselves
  determine the distribution family.

This is a new architectural pattern intended to be reused across `player`,
`statistics`, and the not-yet-created `simulation` module, so it requires an
ADR per `AGENTS.md` §13 rather than being decided implicitly during
implementation.

Only NumPy and Pydantic v2 are approved runtime dependencies (`AGENTS.md`
§9). Full hierarchical Bayesian inference (e.g. MCMC via PyMC/Stan) and
`scipy`-based distribution fitting are disproportionate to what V1 needs and
are not currently justified — see "Alternatives considered".

## Decision

Introduce `PlayerShotDistribution`, a new domain type in `caddai.statistics`
(consumed by `caddai.player` for composition on `Club`/`Player`, and later
by `caddai.simulation` for outcome sampling), representing a golfer's stock
shot production for a given club/club-category as a **bivariate Student-t
distribution** over `(carry_metres, lateral_metres)`:

- **Family and correlation are a binding V1 structural decision.** The shot
  production model is bivariate (carry and lateral jointly), allows
  nonzero correlation between them, and uses Student-t (not Gaussian) tails
  to avoid understating severe-miss risk. This directly rejects the
  independent-Gaussian default that M3's separate `CarryDistribution`/
  `DirectionalDispersion` primitives implicitly encode.
- **Numeric hyperparameters are explicitly provisional**, not part of this
  binding decision. Population covariance scale, correlation-shrinkage
  strength, and degrees-of-freedom (ν) are evidence-informed starting
  points pending CaddAI's own calibration data (see the research document's
  "evidence gaps" section) and must be represented as configuration, not
  literals embedded in model logic. Superseding a provisional numeric value
  with a calibrated one is not itself an architectural change and does not
  require a new ADR.
- **The representation must remain extensible, not implicitly the only one
  ever supported.** `PlayerShotDistribution` must carry an explicit
  family/representation marker (e.g. a discriminated field, initially
  `"bivariate_student_t"`) so a future richer representation (e.g. a full
  launch-state distribution, or an explicit severe-miss mixture component)
  can be introduced later without silently assuming today's family is
  permanent. `simulation`/`strategy` must consume `PlayerShotDistribution`
  through its declared contract, not by assuming carry/lateral endpoints are
  the only fields that will ever exist.
- **Sampling and moment/shrinkage math must be implementable with NumPy
  alone.** Bivariate Student-t sampling is a standard construction —
  `z ~ N(0, Σ)` via `numpy.random.Generator.multivariate_normal` combined
  with `w ~ chisquare(ν)` via `numpy.random.Generator.chisquare`, returning
  `μ + z / sqrt(w / ν)` — and covariance/correlation moment estimation uses
  `numpy.cov`/`numpy.corrcoef`. No new dependency is introduced by this
  decision.
- `PlayerShotDistribution` is **additive**: `Club`/`Player` gain an optional
  field (e.g. `shot_distribution: PlayerShotDistribution | None`) rather
  than replacing the existing required `carry_distribution`/`dispersion`
  fields. M3's `CarryDistribution`/`DirectionalDispersion` remain valid,
  unmodified primitives for simple summaries and degenerate/placeholder
  clubs; they are not derived from, or converted into,
  `PlayerShotDistribution` as a permanent coupling.
- Module ownership and dependency direction are unchanged: this type lives
  in `caddai.statistics`, is composed by `caddai.player`, and will be
  consumed by `caddai.simulation` — never the reverse, and never imported
  by `llm`/`api`/`cli`.

## Consequences

- Positive: `simulation` and `strategy` (M5) can be built against a shot
  representation that already supports correlated, heavy-tailed outcomes,
  avoiding a later breaking change once severe-miss/tail behaviour becomes
  strategy-relevant.
- Positive: the explicit family marker and additive composition mean this
  decision does not foreclose a richer future representation (e.g. launch
  angle/spin, or a severe-miss mixture) — those can be added without
  breaking existing consumers.
- Positive: no new runtime dependency; implementation stays within the
  NumPy/Pydantic v2 approved set (`AGENTS.md` §9).
- Negative: bivariate Student-t is more complex to implement, test, and
  explain than independent Gaussians, and requires care in `player`
  (which must translate `ShotRecord` history into distribution updates)
  to avoid a `statistics → player` circular import — pure statistical
  machinery must operate on plain arrays/parameters it owns, not directly
  on `caddai.player.ShotRecord`.
- Negative: because numeric hyperparameters are provisional, early V1
  outputs carry real epistemic uncertainty that must not be presented to
  users as validated population fact; this must be reflected in whatever
  confidence/provenance metadata `PlayerShotDistribution` exposes.
- Negative: `CarryDistribution`/`DirectionalDispersion` and
  `PlayerShotDistribution` now coexist as two independent shot-related
  representations on `Club`/`Player`, which is intentional (avoids a
  breaking change) but adds a small amount of conceptual surface area that
  must be documented clearly (`docs/player-model.md`) to avoid confusion
  about which one a given code path should use.

## Alternatives considered

- **Independent Gaussian carry/lateral (status quo, M3 primitives only).**
  Rejected as the V1 stock-shot production model: public exploratory
  evidence rejects the independent, thin-tailed assumption in most tested
  cells, and it would understate severe-miss risk that matters to
  strategy. Retained unchanged as a separate, simpler primitive for other
  uses.
- **Correlated multivariate Gaussian.** Adds the correlation parameter this
  decision wants, but remains thin-tailed; the research report identifies
  Student-t as capturing both correlation and heavy tails for only one
  additional parameter (ν) at modest extra complexity.
- **Explicit core-shot + severe-miss mixture distribution.** More
  expressive and interpretable, but requires a miss probability/severity
  that public evidence does not currently support estimating by
  handicap × club; deferred to a later milestone once CaddAI has its own
  calibration data, per the research document.
- **Skew-t / other skewed multivariate families.** Would better capture the
  lateral skew observed in exploratory data, but adds parameters that
  cannot be defensibly initialised without calibration data; deferred.
- **Full hierarchical Bayesian model via a probabilistic-programming
  dependency (e.g. PyMC/Stan) or `scipy.stats`/`scipy.optimize`-based
  fitting.** Disproportionate to V1's needs, which use population priors
  plus closed-form empirical-Bayes/shrinkage updates rather than MCMC or
  maximum-likelihood fitting; would also require a new-dependency ADR and
  human approval (`AGENTS.md` §9/§13) that is not currently justified.
- **Empirical/bootstrap distribution from personal history.** Excellent
  once a golfer has many representative shots, but unusable at cold start
  and poor at estimating tails from small samples; may be revisited later
  as a diagnostic or high-data alternative, not for V1.
