"""Simulation subsystem: environment/physics transform of shot outcomes.

See docs/architecture.md's `simulation` subsystem entry and GitHub issue
#55 ("M4.7 — Environment/physics transformation layer and simulation
bootstrap").

Callers choose whether to apply environmental adjustment per shot outcome
— this is not this subsystem's decision. **Enabled:** intrinsic
``PlayerShotDistribution`` sample -> intrinsic ``ShotOutcome`` ->
``apply_environment_transform(...)`` -> adjusted ``ShotOutcome``.
**Disabled:** intrinsic ``PlayerShotDistribution`` sample -> intrinsic
``ShotOutcome``, used unchanged, with no call to
``apply_environment_transform`` at all. Nothing in ``caddai.simulation``
requires every sample to pass through the transform, and nothing here
encodes Rules-of-Golf or tournament-mode policy about when environmental
inputs may influence advice.
"""

from caddai.simulation.environment import (
    EnvironmentTransformUnsupportedClubCategoryError,
    apply_environment_transform,
)
from caddai.simulation.environment_config import (
    DEFAULT_ENVIRONMENT_TRANSFORM_CONFIG,
    ENVIRONMENT_TRANSFORM_CONFIG_VERSION,
    EnvironmentTransformConfig,
)
from caddai.simulation.models import EnvironmentInput, ShotOutcome, WindComponents
from caddai.simulation.sampling import ShotOutcomeSampler, sample_bivariate_student_t_shot_outcomes

__all__ = [
    "DEFAULT_ENVIRONMENT_TRANSFORM_CONFIG",
    "ENVIRONMENT_TRANSFORM_CONFIG_VERSION",
    "EnvironmentInput",
    "EnvironmentTransformConfig",
    "EnvironmentTransformUnsupportedClubCategoryError",
    "ShotOutcome",
    "ShotOutcomeSampler",
    "WindComponents",
    "apply_environment_transform",
    "sample_bivariate_student_t_shot_outcomes",
]
