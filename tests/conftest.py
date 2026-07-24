"""Test fixtures, including the bridge to a local massing checkout.

The golden round-trip test (PLAN.md §10 Phase 0) deliberately runs against massing's *real*
`import_types_from_ifc` rather than a reimplementation, because the whole library depends on that exact
code path preserving our content. Point MASSING_ROOT at a checkout to enable it.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DEFAULT_MASSING = Path(os.environ.get("MASSING_ROOT", r"C:\Server\modelmaker"))
MASSING_DATA_SRC = DEFAULT_MASSING / "services" / "data" / "src"


@pytest.fixture(scope="session")
def catalog_root() -> Path:
    return REPO / "catalog"


@pytest.fixture(scope="session")
def massing_families():
    """massing's own `aec_data.families` module, or skip if no checkout is available."""
    if not (MASSING_DATA_SRC / "aec_data" / "families.py").exists():
        pytest.skip(f"no massing checkout at {DEFAULT_MASSING} (set MASSING_ROOT)")
    if str(MASSING_DATA_SRC) not in sys.path:
        sys.path.insert(0, str(MASSING_DATA_SRC))
    try:
        from aec_data import families  # type: ignore
    except Exception as e:                                    # noqa: BLE001
        pytest.skip(f"could not import massing aec_data.families: {e}")
    return families


@pytest.fixture()
def target_model():
    """An empty IFC4 project with a Body context — stands in for a user's model."""
    from massing_families.ifc import new_library
    return new_library("Target Project")
