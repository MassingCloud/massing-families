"""AISC generator — real mill-shape dimensions, correct IFC profile per family."""
from __future__ import annotations

import pytest

from massing_families.builders import build_geometry
from massing_families.generators import expand
from massing_families.generators.aisc import DATA, generate
from massing_families.ifc import new_library
from massing_families.spec import FamilySpec, load_catalog

pytestmark = pytest.mark.skipif(not DATA.exists(),
                                reason="data/aisc_shapes.csv not derived yet")

BASE = {"key": "s", "label": "Sec", "ifc_class": "IfcColumnType", "category": "C",
        "discipline": "structural", "builder": "profile", "tier": "L300", "generator": "aisc"}


def _spec(**args):
    return FamilySpec.from_dict({**BASE, "generator_args": args})


def test_w_shapes_carry_true_aisc_dimensions():
    """W14X90: bf 14.5, d 14.0, tw 0.440, tf 0.710 — the published section."""
    v = {x.name: x for x in generate(_spec(family="W", series=["W14"]))}
    p = v["W14X90"].profile["params"]
    assert (p["OverallWidth"], p["OverallDepth"]) == (14.5, 14.0)
    assert (p["WebThickness"], p["FlangeThickness"]) == (0.44, 0.71)


@pytest.mark.parametrize("family,kind,args", [
    ("W", "IShape", {}),
    ("HP", "IShape", {}),
    ("C", "UShape", {}),
    ("MC", "UShape", {}),
    ("L", "LShape", {}),
    ("WT", "TShape", {}),
    ("HSS", "RectangleHollow", {"shape": "rect"}),
    ("HSS", "CircleHollow", {"shape": "round"}),
    ("PIPE", "CircleHollow", {}),
])
def test_each_family_maps_to_its_ifc_profile(family, kind, args):
    variants = generate(_spec(family=family, limit=3, **args))
    assert variants
    assert all(v.profile["kind"] == kind for v in variants)


def test_fillet_radius_derived_from_k_dimension():
    """AISC publishes k (kdes), not the fillet: fillet = k - flange thickness, never negative."""
    for v in generate(_spec(family="W", series=["W14"])):
        p = v.profile["params"]
        assert p["FilletRadius"] >= 0


def test_generated_sections_build_real_geometry():
    spec = _spec(family="W", series=["W14"])
    model = new_library()
    variant = next(v for v in expand(spec) if v.name == "W14X90")
    rep = build_geometry(model, spec, variant)
    prof = rep.Items[0].SweptArea
    assert prof.is_a() == "IfcIShapeProfileDef"
    assert prof.OverallWidth == pytest.approx(0.3683)      # 14.5" in exact metres
    assert prof.ProfileName == "W14X90"


def test_section_provenance_is_stamped():
    v = generate(_spec(family="W", series=["W14"]))[0]
    assert v.psets["MF_Structural"]["SectionSource"].startswith("AISC Shapes Database")


def test_unknown_family_is_rejected():
    with pytest.raises(ValueError, match="matched no sections"):
        generate(_spec(family="ZZ"))


def test_missing_family_arg_is_rejected():
    with pytest.raises(ValueError, match="generator_args.family is required"):
        generate(_spec(length="10'-0\""))


def test_whole_catalog_expands(catalog_root):
    """Smoke test: every spec in the real catalog expands without error, and packs stay scoped.

    Deliberately does not build geometry — that is what makes it fast enough to keep in the main
    suite while the golden round-trip runs on a representative subset.
    """
    specs = load_catalog(catalog_root)
    from collections import Counter
    per_pack = Counter()
    total = 0
    for s in specs:
        n = len(expand(s))
        assert n > 0, f"{s.key} expanded to nothing"
        per_pack[s.pack_name] += n
        total += n
    assert total > 1500, "catalog should be well past 1,500 types after the AISC generator"
    biggest, count = per_pack.most_common(1)[0]
    assert count < 1000, (f"pack {biggest!r} has {count} types — import pulls in every type in a "
                          f"file, so packs must stay trade-scoped (PLAN.md §3)")
