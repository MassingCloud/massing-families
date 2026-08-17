"""The declared version must be real.

`cli build` stamps `__version__` into every pack filename, the manifest, each pack's STEP header and
every type's `MF_Library.Version`. It sat at 0.1.0 through five releases, so any build that did not
pass `--version` explicitly mislabelled its output — a full current catalog reached a deployment's
shelf labelled v0.1.0, which is worse than being out of date because nothing says so.

CI releases were unaffected (the workflow passes the tag), which is exactly why it went unnoticed.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from massing_families import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_version_is_a_release_number():
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__), __version__


def test_pyproject_takes_the_version_from_the_package():
    """Declared in one place only, so the two cannot drift apart."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'dynamic = ["version"]' in text
    assert 'version = {attr = "massing_families.__version__"}' in text
    assert not re.search(r'(?m)^version\s*=\s*"', text), "a static version would shadow the dynamic one"


def test_changelog_documents_this_version():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## v{__version__}" in text, (
        f"CHANGELOG has no entry for v{__version__} — bump one or the other")


def test_changelog_top_section_is_this_version():
    """New work must land under a new heading, not be appended to a released one.

    Four commits were once documented under `## v0.1.5` that the v0.1.5 release did not contain —
    the changelog described a release honestly right up until the next batch of work was written into
    it. Requiring the newest heading to equal `__version__` means the only way to document new work
    is to bump the version first.
    """
    import re

    headings = re.findall(r"(?m)^## (v\d+\.\d+\.\d+)$",
                          (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
    assert headings, "CHANGELOG has no version headings"
    assert headings[0] == f"v{__version__}", (
        f"newest CHANGELOG section is {headings[0]} but __version__ is {__version__} — bump the "
        f"version before documenting new work, or the entry claims to be in a shipped release")


def test_version_is_not_behind_the_latest_tag():
    """A stale __version__ is how mislabelled packs happen; catch it before the next build."""
    try:
        out = subprocess.run(["git", "tag", "--list", "v*"], cwd=ROOT,
                             capture_output=True, text=True, timeout=15)
    except Exception:                                       # noqa: BLE001
        pytest.skip("git unavailable")
    tags = [t[1:] for t in out.stdout.split() if re.fullmatch(r"v\d+\.\d+\.\d+", t)]
    if not tags:
        pytest.skip("no release tags yet")
    key = lambda v: tuple(int(p) for p in v.split("."))      # noqa: E731
    latest = max(tags, key=key)
    assert key(__version__) >= key(latest), (
        f"__version__ is {__version__} but v{latest} is already tagged — local builds would stamp "
        f"the older number into every pack")

    # And if there is unreleased work, the version must already be past the tag, so that work is
    # documented under its own heading rather than appended to a shipped release.
    ahead = subprocess.run(["git", "rev-list", "--count", f"v{latest}..HEAD"], cwd=ROOT,
                           capture_output=True, text=True, timeout=15)
    if ahead.returncode == 0 and ahead.stdout.strip().isdigit() and int(ahead.stdout.strip()) > 0:
        assert key(__version__) > key(latest), (
            f"{ahead.stdout.strip()} commit(s) since v{latest} but __version__ is still "
            f"{__version__} — bump it so the work is documented under its own version")
