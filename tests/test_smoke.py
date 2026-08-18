"""Smoke tests proving the ``caddai`` package is installable and importable."""

import importlib

import caddai


def test_package_imports() -> None:
    """The top-level package must import without side effects or errors."""
    assert importlib.import_module("caddai") is caddai


def test_package_exposes_a_semver_version_string() -> None:
    """``caddai.__version__`` must exist and look like a semantic version."""
    version = caddai.__version__

    assert isinstance(version, str)
    parts = version.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
