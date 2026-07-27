"""Documentation must not drift from the catalog.

The README claimed 270 families / 2,334 types for a while after the catalog had grown past 400 — the
numbers were right when written and quietly went stale. Generated docs plus these checks mean that
cannot happen silently again.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from massing_families import docs
from massing_families.spec import load_catalog

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def specs(catalog_root):
    return load_catalog(catalog_root)


def test_catalog_reference_is_current(specs):
    """`docs/CATALOG.md` is generated. If it differs from a fresh render, someone edited the catalog
    without re-running `python -m massing_families.cli docs`."""
    path = ROOT / "docs" / "CATALOG.md"
    assert path.exists(), "docs/CATALOG.md missing — run `cli docs`"
    assert path.read_text(encoding="utf-8") == docs.render(specs), (
        "docs/CATALOG.md is stale — run `python -m massing_families.cli docs`")


def test_readme_headline_counts_match(specs):
    """The README's headline numbers are prose, so they are checked rather than generated."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    st = docs.stats(specs)

    def claimed(pattern):
        m = re.search(pattern, text)
        assert m, f"README no longer states {pattern!r} — update the test or the README"
        return int(m.group(1).replace(",", ""))

    assert claimed(r"([\d,]+) families") == st["families"]
    assert claimed(r"([\d,]+) types") == st["types"]
    assert claimed(r"([\d,]+) discipline packs") == st["packs"]


def test_documented_builders_and_generators_exist():
    """CONTRIBUTING and SPEC name builders and generators; a rename must not leave docs lying."""
    from massing_families.builders import BUILDERS
    from massing_families.generators import GENERATORS

    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    spec = (ROOT / "docs" / "SPEC.md").read_text(encoding="utf-8")
    for name in BUILDERS:
        assert f"`{name}`" in contributing or f"`{name}`" in spec, \
            f"builder {name!r} is undocumented"
    for name in GENERATORS:
        assert f"`{name}`" in contributing or f"`{name}`" in spec, \
            f"generator {name!r} is undocumented"


def test_public_facing_docs_exist():
    for name in ("README.md", "CONTRIBUTING.md", "NOTICE.md", "PLAN.md",
                 "docs/SPEC.md", "docs/CATALOG.md", "upstream/README.md"):
        assert (ROOT / name).exists(), f"{name} missing"


def test_no_stale_private_repo_claims():
    """The repo is public. Docs that still tell users a token is required send them down a dead end."""
    for name in ("README.md", "upstream/README.md", "upstream/fetch_families.py"):
        text = (ROOT / name).read_text(encoding="utf-8").lower()
        assert "repo is private" not in text, f"{name} still describes the repo as private"
