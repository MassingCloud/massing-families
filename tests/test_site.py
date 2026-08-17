"""The catalog site is generated, so it must not drift from the catalog.

`docs/CATALOG.md` is a reference you read top to bottom; the site is for "show me every L300
structural family with ports", which 419 rows in markdown cannot answer. Both are rendered from the
same specs — a page describing content the release does not contain would be worse than no page.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from massing_families import __version__, site
from massing_families.spec import load_catalog

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "site" / "index.html"


@pytest.fixture(scope="module")
def specs(catalog_root):
    return load_catalog(catalog_root)


def test_site_is_current(specs):
    assert PAGE.exists(), "site/index.html missing — run `python -m massing_families.cli site`"
    assert PAGE.read_text(encoding="utf-8") == site.render(specs, __version__), (
        "site/index.html is stale — run `python -m massing_families.cli site`")


def test_every_family_is_listed(specs):
    html = PAGE.read_text(encoding="utf-8")
    assert html.count('<tr data-search=') == len(specs)
    for spec in specs[:25]:
        assert spec.key in html, f"{spec.key} missing from the site"


def test_site_is_self_contained():
    """No CDN, no external fonts, no analytics. A page that breaks when someone else's host changes
    is worse than a static table."""
    import re

    html = PAGE.read_text(encoding="utf-8")
    external = [u for u in re.findall(r'https?://[^\s"\'<>)]+', html)
                if not u.startswith("https://github.com/MassingCloud/massing-families")]
    assert not external, f"site references external hosts: {external[:3]}"
    assert "<script src=" not in html and "@import" not in html


def test_site_states_the_licence_and_the_proxy_caveat():
    html = PAGE.read_text(encoding="utf-8")
    assert "CC0" in html
    assert "proxy" in html and "bounding dimensions" in html, (
        "the site must explain what a proxy is — it is the field that stops a box being mistaken "
        "for detailed content")
