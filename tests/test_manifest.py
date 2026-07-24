"""Provenance honesty and the manifest family index.

`GeometryStatus` is the label that stops a dimensionally-correct box being mistaken for detailed
content (PLAN.md §8g). It is *derived from the builder*, never hand-set, so it cannot drift.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from massing_families.enrich import GEOMETRY_STATUS, geometry_status
from massing_families.pack import build_model, write_manifest, write_pack
from massing_families.spec import load_catalog

PACKS = Path(__file__).resolve().parents[1] / "packs"


def test_every_builder_declares_a_geometry_status():
    from massing_families.builders import BUILDERS
    assert set(GEOMETRY_STATUS) == set(BUILDERS), \
        "a builder without a declared GeometryStatus would ship as 'unknown'"


def test_box_is_labelled_a_proxy_and_profiles_are_not():
    class S:
        builder = "box"
    assert geometry_status(S) == "proxy"
    S.builder = "profile"
    assert geometry_status(S) == "parametric"
    S.builder = "assembly"
    assert geometry_status(S) == "assembly"
    S.builder = "mesh"
    assert geometry_status(S) == "tessellated"


def test_provenance_carries_geometry_status(catalog_root):
    specs = [s for s in load_catalog(catalog_root) if s.key in {"door_single_flush",
                                                                "concrete_column"}]
    model, _ = build_model(specs, "test")
    import ifcopenshell.util.element as ue
    statuses = {ue.get_psets(t, psets_only=True)["MF_Library"]["GeometryStatus"]
                for t in model.by_type("IfcTypeProduct")}
    assert statuses == {"proxy", "parametric"}


def test_family_index_is_written(tmp_path, catalog_root):
    specs = [s for s in load_catalog(catalog_root) if s.discipline == "conveying"]
    entry = write_pack(specs, tmp_path, "conveying", "test")
    write_manifest([entry], tmp_path, "test")
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))

    index = manifest["packs"][0]["index"]
    assert len(index) == len(specs)
    row = index[0]
    for field in ("key", "label", "category", "ifc_class", "tier", "geometry",
                  "classification", "license", "type_count", "types"):
        assert field in row, f"picker needs {field!r} in the family index"
    assert row["type_count"] >= 1
    assert row["types"], "index must list type names for search"


@pytest.mark.skipif(not (PACKS / "manifest.json").exists(),
                    reason="packs not built; run `python -m massing_families.cli build`")
def test_built_manifest_is_self_consistent():
    manifest = json.loads((PACKS / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["totals"]["families"] == sum(len(p["index"]) for p in manifest["packs"])
    for pack in manifest["packs"]:
        assert (PACKS / pack["file"]).exists(), f"{pack['file']} listed but missing"
        assert pack["types"] == sum(f["type_count"] for f in pack["index"])
        assert len(pack["sha256"]) == 64


def test_build_removes_stale_packs(tmp_path, catalog_root):
    """A renamed pack or bumped version must not leave orphans behind.

    Regression: `packs/` accumulated 41 stale files across earlier builds, and anything globbing
    `packs/*.ifc` — a deployment fetch, a stats script — then counted content no longer in the
    catalog. The build now clears the output directory first.
    """
    from massing_families.cli import cmd_build
    from argparse import Namespace

    orphan = tmp_path / "massing-families-oldname-v0.0.1.ifc"
    orphan.write_bytes(b"stale")

    cmd_build(Namespace(discipline="conveying", out=tmp_path, version="test"))

    assert not orphan.exists(), "stale pack survived the build"
    on_disk = {p.name for p in tmp_path.glob("*.ifc")}
    listed = {p["file"] for p in
              json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))["packs"]}
    assert on_disk == listed, "every file on disk must be listed in the manifest"
