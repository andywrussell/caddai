"""Architecture-invariant test: ``strategy`` must not import forbidden subsystems.

Statically parses every source file in ``caddai.strategy`` with the ``ast``
module (not just relying on runtime import side effects) to assert the
deterministic-strategy principle from AGENTS.md: no `strategy`/`simulation`
code may import `llm`, `api`, `cli`, or any UI package.
"""

import ast
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

STRATEGY_SOURCE_FILES = [
    REPO_ROOT / "src/caddai/strategy/__init__.py",
    REPO_ROOT / "src/caddai/strategy/models.py",
    REPO_ROOT / "src/caddai/strategy/recommend.py",
]


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


@pytest.mark.parametrize("source_path", STRATEGY_SOURCE_FILES, ids=lambda path: path.name)
def test_strategy_module_does_not_import_forbidden_subsystems(source_path: Path) -> None:
    """Neither strategy source file may import llm, api, cli, or a UI package."""
    if not source_path.exists():
        pytest.fail(
            f"{source_path} does not exist yet — this test is the executable spec "
            "for Task 2 of docs/plans/m1-core-domain-vertical-slice.plan.md."
        )

    imported_modules = _imported_module_names(source_path)
    forbidden_imports = {name for name in imported_modules if _is_forbidden(name)}

    assert not forbidden_imports, (
        f"{source_path} imports forbidden module(s) {forbidden_imports}; "
        "strategy/simulation may never import llm, api, cli, or UI packages (AGENTS.md §2)."
    )


@pytest.mark.parametrize("source_path", STRATEGY_SOURCE_FILES, ids=lambda path: path.name)
def test_strategy_module_only_depends_on_approved_subsystems(source_path: Path) -> None:
    """Strategy source may only import caddai.player, caddai.strategy, stdlib, or pydantic."""
    if not source_path.exists():
        pytest.fail(
            f"{source_path} does not exist yet — this test is the executable spec "
            "for Task 2 of docs/plans/m1-core-domain-vertical-slice.plan.md."
        )

    allowed_caddai_prefixes = ("caddai.player", "caddai.strategy")
    imported_modules = _imported_module_names(source_path)

    disallowed_caddai_imports = {
        name
        for name in imported_modules
        if name.startswith("caddai.") and not name.startswith(allowed_caddai_prefixes)
    }

    assert not disallowed_caddai_imports, (
        f"{source_path} imports out-of-scope caddai module(s) {disallowed_caddai_imports}; "
        "M1 strategy depends only on player + stdlib + pydantic (docs/plans/"
        "m1-core-domain-vertical-slice.plan.md)."
    )
