"""Simulation subsystem: environment/physics transform of shot outcomes.

See docs/architecture.md's `simulation` subsystem entry and GitHub issue
#55 ("M4.7 — Environment/physics transformation layer and simulation
bootstrap").
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

__all__ = [
    "DEFAULT_ENVIRONMENT_TRANSFORM_CONFIG",
    "ENVIRONMENT_TRANSFORM_CONFIG_VERSION",
    "EnvironmentInput",
    "EnvironmentTransformConfig",
    "EnvironmentTransformUnsupportedClubCategoryError",
    "ShotOutcome",
    "WindComponents",
    "apply_environment_transform",
]
