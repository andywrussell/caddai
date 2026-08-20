"""Architecture-invariant tests: subsystem modules must not import forbidden subsystems.

Statically parses every source file in each covered subsystem with the
``ast`` module (not just relying on runtime import side effects) to assert
the dependency-direction rules from AGENTS.md: no `strategy`/`simulation`
code may import `llm`, `api`, `cli`, or any UI package, and each subsystem
below may only depend on its own approved `caddai.*` prefixes.

Parametrized across subsystems (rather than duplicated per subsystem file)
so a new subsystem's boundary coverage is a one-line addition to
``SUBSYSTEM_BOUNDARIES`` below — see `course`/`gps` in milestone M2.
"""

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

FORBIDDEN_TOP_LEVEL_MODULES = {
    "caddai.llm",
    "caddai.api",
    "caddai.cli",
    # Common UI/web packages that would indicate a boundary violation.
    "streamlit",
    "flask",
    "django",
    "tkinter",
    "kivy",
    "textual",
    "rich",
}

REPO_ROOT = Path(__file__).parent.parent


@dataclass(frozen=True)
class SubsystemBoundary:
    """A subsystem's source files and the `caddai.*` prefixes it may depend on."""

    name: str
    source_files: tuple[Path, ...]
    allowed_caddai_prefixes: tuple[str, ...]
    plan_reference: str


SUBSYSTEM_BOUNDARIES = [
    SubsystemBoundary(
        name="strategy",
        source_files=(
            REPO_ROOT / "src/caddai/strategy/__init__.py",
            REPO_ROOT / "src/caddai/strategy/models.py",
            REPO_ROOT / "src/caddai/strategy/recommend.py",
            REPO_ROOT / "src/caddai/strategy/demo.py",
        ),
        allowed_caddai_prefixes=("caddai.player", "caddai.strategy"),
        plan_reference="Task 2 of docs/plans/m1-core-domain-vertical-slice.plan.md",
    ),
    SubsystemBoundary(
        name="gps",
        source_files=(
            REPO_ROOT / "src/caddai/gps/__init__.py",
            REPO_ROOT / "src/caddai/gps/models.py",
            REPO_ROOT / "src/caddai/gps/distance.py",
            REPO_ROOT / "src/caddai/gps/projection.py",
        ),
        # gps is a leaf domain module: zero other caddai.* imports permitted.
        allowed_caddai_prefixes=("caddai.gps",),
        plan_reference='GitHub issue #3 ("M2.1 — GPS coordinate & distance primitives")',
    ),
    SubsystemBoundary(
        name="course",
        source_files=(
            REPO_ROOT / "src/caddai/course/__init__.py",
            REPO_ROOT / "src/caddai/course/models.py",
            REPO_ROOT / "src/caddai/course/geojson.py",
            REPO_ROOT / "src/caddai/course/distance.py",
        ),
        allowed_caddai_prefixes=("caddai.course", "caddai.gps"),
        plan_reference='GitHub issue #5 ("M2.3 — Course/hole/hazard domain models")',
    ),
    SubsystemBoundary(
        name="statistics",
        source_files=(
            REPO_ROOT / "src/caddai/statistics/__init__.py",
            REPO_ROOT / "src/caddai/statistics/models.py",
        ),
        # statistics is a leaf domain module: zero other caddai.* imports permitted.
        allowed_caddai_prefixes=("caddai.statistics",),
        plan_reference='GitHub issue #26 ("M3.1 — Carry distribution model")',
    ),
]


def _boundary_test_cases() -> list[tuple[SubsystemBoundary, Path]]:
    """Flatten each boundary's source files into one (boundary, path) case per file."""
    return [
        (boundary, source_path)
        for boundary in SUBSYSTEM_BOUNDARIES
        for source_path in boundary.source_files
    ]


BOUNDARY_TEST_CASES = _boundary_test_cases()
BOUNDARY_TEST_CASE_IDS = [f"{boundary.name}-{path.name}" for boundary, path in BOUNDARY_TEST_CASES]


def _imported_module_names(source_path: Path) -> set[str]:
    """Return every module name referenced by an `import`/`from ... import` statement."""
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    module_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            module_names.add(node.module)

    return module_names


def _is_forbidden(module_name: str) -> bool:
    return any(
        module_name == forbidden or module_name.startswith(f"{forbidden}.")
        for forbidden in FORBIDDEN_TOP_LEVEL_MODULES
    )


@pytest.mark.parametrize(
    ("boundary", "source_path"), BOUNDARY_TEST_CASES, ids=BOUNDARY_TEST_CASE_IDS
)
def test_subsystem_module_does_not_import_forbidden_subsystems(
    boundary: SubsystemBoundary, source_path: Path
) -> None:
    """No covered subsystem file may import llm, api, cli, or a UI package."""
    if not source_path.exists():
        pytest.fail(
            f"{source_path} does not exist yet — this test is the executable spec "
            f"for {boundary.plan_reference}."
        )

    imported_modules = _imported_module_names(source_path)
    forbidden_imports = {name for name in imported_modules if _is_forbidden(name)}

    assert not forbidden_imports, (
        f"{source_path} imports forbidden module(s) {forbidden_imports}; "
        "strategy/simulation may never import llm, api, cli, or UI packages (AGENTS.md §2.1)."
    )


@pytest.mark.parametrize(
    ("boundary", "source_path"), BOUNDARY_TEST_CASES, ids=BOUNDARY_TEST_CASE_IDS
)
def test_subsystem_module_only_depends_on_approved_subsystems(
    boundary: SubsystemBoundary, source_path: Path
) -> None:
    """Each subsystem may only import its approved caddai prefixes, stdlib, or pydantic."""
    if not source_path.exists():
        pytest.fail(
            f"{source_path} does not exist yet — this test is the executable spec "
            f"for {boundary.plan_reference}."
        )

    imported_modules = _imported_module_names(source_path)

    disallowed_caddai_imports = {
        name
        for name in imported_modules
        if name.startswith("caddai.") and not name.startswith(boundary.allowed_caddai_prefixes)
    }

    assert not disallowed_caddai_imports, (
        f"{source_path} imports out-of-scope caddai module(s) {disallowed_caddai_imports}; "
        f"{boundary.name} may only depend on {boundary.allowed_caddai_prefixes} + stdlib "
        f"(see {boundary.plan_reference})."
    )
