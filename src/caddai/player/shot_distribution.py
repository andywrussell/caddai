"""Compose `PlayerShotDistribution` into `Club` — baseline vs current.

See GitHub issue #54 ("M4.6 — Compose `PlayerShotDistribution` into
Club/Player") and
docs/plans/m4.6-compose-shot-distribution.plan.md for the full
Architect-approved design. This module wires the existing M4.2 -> M4.3 ->
M4.5 pipeline (`resolve_population_prior` -> `personalise_shot_distribution`
-> `update_shot_distribution_from_history`) into a single composition entry
point and a single ongoing read path, without duplicating or coupling to
the M3 `CarryDistribution`/`DirectionalDispersion` types. No Monte Carlo, no
environment/physics, no course-relative mapping, no strategy, no
persistence — those remain later milestones' responsibility. No RNG, no
side effects: every function here is a deterministic, pure composition of
already-deterministic `caddai.player`/`caddai.statistics` building blocks.

**Baseline vs current (binding distinction):** `Club.shot_distribution`
holds only the immutable *baseline* — the onboarding/population-prior
cold-start `PlayerShotDistribution` for that club, set once (at onboarding
or re-onboarding time) and never overwritten by a shrinkage posterior. The
*current* distribution — baseline shrunk toward a golfer's complete
`ShotRecord` history via M4.5's `update_shot_distribution_from_history` —
is always derived on demand, never persisted onto `Club`. This is the
architecturally load-bearing choice in this module: a persisted "current"
field would be indistinguishable from a baseline the next time this module
ran, silently violating M4.5's batch-recompute contract (always
`baseline + complete current history`, never a previous posterior fed back
in as if it were the baseline). If you find yourself wanting to persist a
`current_shot_distribution` anywhere (a database row, a cache, a session
object), don't — recompute it via `resolve_current_shot_distribution`
instead; the recomputation cost is one pass over one club's shot history,
the same cost model M4.5 already accepted.
"""

from pydantic import BaseModel

from caddai.player.models import Club, ShotRecord
from caddai.player.onboarding import (
    CarryProvenance,
    CommonMiss,
    OnboardingPersonalisationResult,
    ShotShape,
    personalise_shot_distribution,
)
from caddai.player.personalisation import update_shot_distribution_from_history
from caddai.statistics import (
    ClubCategory,
    ClubCategorySupportStatus,
    PersonalisationConfig,
    PlayerShotDistribution,
    ShotDistributionUpdateResult,
    club_category_support_status,
)


class ClubShotDistributionResolution(BaseModel):
    """The result of resolving a `Club`'s *current* `PlayerShotDistribution`.

    `shot_distribution` is `None` whenever `club.shot_distribution` (the
    baseline) is `None` — uniformly "no baseline composed yet," never
    distinguishing *why* on this type. `support_status` disambiguates that
    "why" instead, always recomputed from `club.category` independent of
    whether `shot_distribution` happens to be populated:
    `SUPPORTED`/`shot_distribution is None` means "a supported category
    that simply hasn't been onboarded yet"; `DEFERRED` means
    `ClubCategory.PUTTER`; `NOT_MODELABLE` means `ClubCategory.OTHER`.
    `SUPPORTED` with a populated `shot_distribution` means resolved and
    ready to use.
    """

    shot_distribution: PlayerShotDistribution | None
    support_status: ClubCategorySupportStatus


class ClubShotDistributionComposition(BaseModel):
    """The result of composing a fresh onboarding baseline with shot history.

    `baseline_shot_distribution` is the immutable cold-start distribution —
    the caller is responsible for persisting it onto `Club.shot_distribution`
    explicitly (this module never mutates a `Club`); it is safe to reuse as
    the `baseline_distribution` argument to future
    `update_shot_distribution_from_history` calls, including via
    `resolve_current_shot_distribution`. `current_shot_distribution` is the
    same baseline shrunk toward `shot_history` at composition time — for
    immediate use only (e.g. showing the golfer their distribution right
    after onboarding with any history already on file); it must **never**
    be persisted anywhere, including onto `Club.shot_distribution` — doing
    so would turn a later `resolve_current_shot_distribution`/
    `update_shot_distribution_from_history` call into a baseline that has
    already absorbed evidence, silently double-counting it. `onboarding`
    and `update` are the raw M4.3/M4.5 result objects, retained for
    traceability/provenance (population-prior confidence, per-dimension
    update outcomes, and so on) — nothing here summarises or discards them.
    """

    baseline_shot_distribution: PlayerShotDistribution
    current_shot_distribution: PlayerShotDistribution
    onboarding: OnboardingPersonalisationResult
    update: ShotDistributionUpdateResult


def resolve_current_shot_distribution(
    club: Club,
    shot_history: list[ShotRecord],
    config: PersonalisationConfig | None = None,
) -> ClubShotDistributionResolution:
    """Derive `club`'s *current* `PlayerShotDistribution`, on demand.

    The ongoing read path (for `caddai.simulation`, M4.8, and any future
    `strategy` consumer built against `PlayerShotDistribution`) against an
    already-baselined `Club`. Never calls `resolve_population_prior`/
    `personalise_shot_distribution` — those are onboarding-time only (see
    `compose_club_shot_distribution`). Never mutates `club` or
    `club.shot_distribution` — the returned `current_shot_distribution` is
    computed fresh on every call and must not be written back onto `club`
    (see this module's docstring for why).

    When `club.shot_distribution` (the baseline) is `None`, returns
    `ClubShotDistributionResolution(shot_distribution=None,
    support_status=...)` without reading `shot_history` at all — there is
    no baseline to shrink. Otherwise, shrinks the baseline toward
    `shot_history` via `update_shot_distribution_from_history` (filtered to
    `club.name` internally) and returns its `.shot_distribution` alongside
    `support_status`. `support_status` is always recomputed from
    `club.category`, independent of whether `club.shot_distribution`
    happens to be populated.
    """
    support_status = club_category_support_status(club.category)
    if club.shot_distribution is None:
        return ClubShotDistributionResolution(shot_distribution=None, support_status=support_status)
    update = update_shot_distribution_from_history(
        club.shot_distribution, club.name, shot_history, config
    )
    return ClubShotDistributionResolution(
        shot_distribution=update.shot_distribution, support_status=support_status
    )


def compose_club_shot_distribution(
    *,
    handicap_index: float,
    club_category: ClubCategory,
    reported_carry_metres: float,
    carry_provenance: CarryProvenance,
    common_miss: CommonMiss,
    club_name: str,
    shot_history: list[ShotRecord],
    shot_shape: ShotShape = ShotShape.STRAIGHT,
    config: PersonalisationConfig | None = None,
) -> ClubShotDistributionComposition:
    """Compose a fresh onboarding baseline with a club's shot history.

    The single M4.2 -> M4.3 -> M4.5 composition entry point, called at
    (re-)onboarding time. Builds the cold-start baseline via
    `personalise_shot_distribution` (which itself calls
    `resolve_population_prior`) from raw onboarding inputs — not a
    pre-built `OnboardingPersonalisationResult` — then immediately shrinks
    that baseline toward `shot_history` via
    `update_shot_distribution_from_history`, using `club_name` to filter
    the history to the relevant club.

    Propagates `personalise_shot_distribution`'s own `ValueError`/
    `PopulationPriorUnsupportedCategoryError` unmodified (including
    `ClubCategory.PUTTER` -> `DEFERRED` and `ClubCategory.OTHER` ->
    `NOT_MODELABLE`) — this function does not catch or reinterpret them.

    Does **not** mutate any `Club`. The caller is responsible for
    persisting `.baseline_shot_distribution` onto `Club.shot_distribution`
    explicitly (e.g. `club.shot_distribution =
    result.baseline_shot_distribution` or rebuilding the `Club`). See
    `ClubShotDistributionComposition`'s docstring for why
    `.current_shot_distribution` must never be persisted anywhere.
    """
    onboarding = personalise_shot_distribution(
        handicap_index=handicap_index,
        club_category=club_category,
        reported_carry_metres=reported_carry_metres,
        carry_provenance=carry_provenance,
        common_miss=common_miss,
        shot_shape=shot_shape,
    )
    update = update_shot_distribution_from_history(
        onboarding.shot_distribution, club_name, shot_history, config
    )
    return ClubShotDistributionComposition(
        baseline_shot_distribution=onboarding.shot_distribution,
        current_shot_distribution=update.shot_distribution,
        onboarding=onboarding,
        update=update,
    )
