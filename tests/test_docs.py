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
    for name in ("README.md", "CONTRIBUTING.md", "NOTICE.md", "PLAN.md", "ROADMAP.md",
                 "CHANGELOG.md", "SECURITY.md", "CODE_OF_CONDUCT.md",
                 "docs/SPEC.md", "docs/CATALOG.md", "docs/GUIDE.md",
                 "upstream/README.md", ".github/PULL_REQUEST_TEMPLATE.md"):
        assert (ROOT / name).exists(), f"{name} missing"


def test_no_stale_private_repo_claims():
    """The repo is public. Docs that still tell users a token is required send them down a dead end."""
    for name in ("README.md", "upstream/README.md", "upstream/fetch_families.py"):
        text = (ROOT / name).read_text(encoding="utf-8").lower()
        assert "repo is private" not in text, f"{name} still describes the repo as private"


def test_roadmap_metrics_match_the_catalog(specs):
    """The roadmap argues from numbers — proxy count, untouched IFC classes. If those drift the
    argument stops being true, which is worse than the doc simply being out of date."""
    from massing_families.spec import TYPE_CLASSES

    text = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    st = docs.stats(specs)
    proxies = sum(1 for s in specs if s.builder == "box")
    untouched = len(TYPE_CLASSES) - st["ifc_classes"]

    assert f"**{st['families']}**" in text, "roadmap family count is stale"
    assert f"{proxies} of {st['families']}" in text, (
        f"roadmap should say {proxies} of {st['families']} families are L200 proxies")
    assert f"{untouched} IFC4 type classes" in text, (
        f"roadmap should say {untouched} type classes are untouched")


def test_changelog_covers_the_current_release():
    """Every tagged release needs an entry; the top entry is the one being prepared or shipped."""
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for version in ("v0.1.0", "v0.1.1", "v0.1.2", "v0.1.3", "v0.1.4", "v0.1.5"):
        assert f"## {version}" in text, f"CHANGELOG missing an entry for {version}"
