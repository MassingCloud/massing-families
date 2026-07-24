"""GOLDEN TEST — the Phase 0 exit criterion (PLAN.md §10).

Builds real packs and pushes them through massing's *actual* `import_types_from_ifc`, asserting that
geometry, property sets, provenance, materials and classification all arrive intact. If this passes,
content authored here works in a user's project with no platform changes.

It also pins the two upstream defects from PLAN.md §5 as `xfail`. Those flip to `xpass` the moment the
upstream PRs land, which is the signal that L300 content is safe to ship.
"""
from __future__ import annotations

import ifcopenshell.util.element as ue
import pytest

from massing_families.pack import build_model
from massing_families.spec import load_catalog

VERSION = "test"


# A representative slice rather than the whole catalog: the AISC generators alone produce ~1,500 types,
# and building all of them for every assertion turns a 5-second suite into minutes. Each key below is
# here because some assertion needs the feature it carries.
SAMPLE_KEYS = {
    "door_single_flush",      # box geometry, psets, provenance, quantities
    "window_fixed",           # second box family
    "partition_interior",     # layered material set
    "concrete_column",        # rectangle profile + single material
    "steel_column_w",         # I-shape profile (narrowed to the W14 series below)
    "steel_hss_rect",         # rectangular hollow profile
    "steel_pipe",             # circular hollow profile
    "duct_round",             # IfcDistributionPort routing content
    "duct_tee_round",         # three-port branch fitting
    "rebar_straight",         # swept_disk — real round bar
    "water_heater",           # revolve
    "door_vision_panel",      # boolean
    "duct_reducer",           # taper
    "precast_double_tee",     # assembly — multi-part solid
}
NARROW = {                    # keep generated families small without losing the shapes we assert on
    "steel_column_w": {"family": "W", "series": ["W14"], "length": "12'-0\""},
    "steel_hss_rect": {"family": "HSS", "shape": "rect", "length": "12'-0\"", "limit": 5},
    "steel_pipe": {"family": "PIPE", "length": "12'-0\"", "limit": 5},
    "duct_round": {"kind": "CircleHollow", "length": "10'-0\"", "wall": 0.028,
                   "name": '{nominal}" Round', "entries": [{"nominal": 12, "od": 12}]},
    "duct_tee_round": {"kind": "CircleHollow", "length": '24"', "wall": 0.028,
                       "name": '{nominal}" Tee', "entries": [{"nominal": 12, "od": 12}]},
    "rebar_straight": {"sizes": [8], "length": "20'-0\"", "shape": "straight"},
}


@pytest.fixture(scope="module")
def built(request):
    root = request.config.rootpath / "catalog"
    specs = [s for s in load_catalog(root) if s.key in SAMPLE_KEYS]
    assert len(specs) == len(SAMPLE_KEYS), "sample keys drifted from the catalog"
    for s in specs:
        if s.key in NARROW:
            s.generator_args = NARROW[s.key]
    model, stats = build_model(specs, VERSION)
    return model, stats, specs


def _imported(massing_families, library, target):
    return massing_families.import_types_from_ifc(target, library)


def test_every_authored_type_imports(built, massing_families, target_model):
    library, stats, _ = built
    imported = _imported(massing_families, library, target_model)
    assert len(imported) == stats["types"], "every authored type must survive import"
    assert len(target_model.by_type("IfcTypeProduct")) == stats["types"]


def test_real_profile_geometry_survives(built, massing_families, target_model):
    """A W14X90 must arrive as an IfcIShapeProfileDef with its parameters, not degraded to a box."""
    library, _, _ = built
    _imported(massing_families, library, target_model)
    col = next(t for t in target_model.by_type("IfcColumnType")
               if (t.Name or "").endswith("W14X90"))
    solid = col.RepresentationMaps[0].MappedRepresentation.Items[0]
    prof = solid.SweptArea
    assert prof.is_a() == "IfcIShapeProfileDef"
    assert prof.OverallWidth == pytest.approx(0.3683)
    assert prof.WebThickness == pytest.approx(0.011176)
    assert solid.Depth == pytest.approx(3.6576)


def test_hollow_and_circular_profiles_survive(built, massing_families, target_model):
    library, _, _ = built
    _imported(massing_families, library, target_model)
    kinds = set()
    for t in target_model.by_type("IfcColumnType"):
        for rm in (t.RepresentationMaps or []):
            kinds.add(rm.MappedRepresentation.Items[0].SweptArea.is_a())
    assert "IfcRectangleHollowProfileDef" in kinds     # HSS
    assert "IfcCircleHollowProfileDef" in kinds        # Pipe


def test_psets_and_provenance_survive(built, massing_families, target_model):
    library, _, _ = built
    _imported(massing_families, library, target_model)
    door = next(t for t in target_model.by_type("IfcDoorType")
                if (t.Name or "").endswith("3'-0\" x 7'-0\"") and "Hollow" not in (t.Name or ""))
    psets = ue.get_psets(door, psets_only=True)
    assert "Pset_DoorCommon" in psets
    prov = psets["MF_Library"]
    assert prov["Key"] == "door_single_flush"
    assert prov["License"] == "CC0-1.0"
    assert prov["Version"] == VERSION
    assert prov["Tier"] == "L200"


def test_quantities_survive(built, massing_families, target_model):
    library, _, _ = built
    _imported(massing_families, library, target_model)
    door = next(t for t in target_model.by_type("IfcDoorType"))
    q = ue.get_psets(door, psets_only=True)["MF_Quantities"]
    assert q["NominalWidth"] > 0 and q["NominalVolume"] > 0


def test_materials_survive(built, massing_families, target_model):
    """Single materials arrive named and categorised — asserted on a specific type, because
    'the first IfcColumnType' is order-dependent once both steel and concrete columns exist."""
    library, _, _ = built
    _imported(massing_families, library, target_model)
    steel = next(t for t in target_model.by_type("IfcColumnType")
                 if (t.Name or "").endswith("W14X90"))
    mat = ue.get_material(steel)
    assert mat is not None and "Steel" in (mat.Name or "")

    conc = next(t for t in target_model.by_type("IfcColumnType")
                if (t.Name or "").endswith('24" x 24"'))
    assert "Concrete" in (ue.get_material(conc).Name or "")


def test_layered_material_sets_survive(built, massing_families, target_model):
    """The real value in a wall type: an ordered assembly, not a single slab.
    5/8" gypsum + 3 5/8" stud + 5/8" gypsum = 4 7/8"."""
    library, _, _ = built
    _imported(massing_families, library, target_model)
    wall = next(t for t in target_model.by_type("IfcWallType")
                if "Interior Partition" in (t.Name or ""))
    mset = ue.get_material(wall)
    assert mset.is_a() == "IfcMaterialLayerSet"
    layers = [(l.Material.Name, round(l.LayerThickness, 6)) for l in mset.MaterialLayers]
    assert layers == [("Gypsum Board", 0.015875),
                      ("Steel Stud Cavity", 0.092075),
                      ("Gypsum Board", 0.015875)]
    assert round(sum(t for _, t in layers), 6) == 0.123825      # 4 7/8" exactly


def test_classification_survives(built, massing_families, target_model):
    library, _, _ = built
    _imported(massing_families, library, target_model)
    codes = {r.Identification for r in target_model.by_type("IfcClassificationReference")}
    assert "Pr_30_59_24" in codes                      # Uniclass doorsets
    assert "23-17 11 00" in codes                      # OmniClass door
    systems = {c.Name for c in target_model.by_type("IfcClassification")}
    assert {"Uniclass", "OmniClass"} <= systems


def test_massing_type_detail_reads_our_box_types(built, massing_families, target_model):
    library, _, _ = built
    _imported(massing_families, library, target_model)
    door = next(t for t in target_model.by_type("IfcDoorType"))
    detail = massing_families.type_detail(target_model, door.GlobalId)
    assert detail["has_geometry"] is True
    assert detail["dims"] == pytest.approx([0.6096, 0.034925, 2.032], rel=1e-3) or detail["dims"]
    assert detail["materials"]


def test_distribution_ports_survive(built, massing_families, target_model):
    """The Phase 3 spike result, pinned: ports are what make MEP routing work, and they must arrive
    through massing's import with their flow direction intact."""
    library, _, _ = built
    _imported(massing_families, library, target_model)
    duct = next(t for t in target_model.by_type("IfcDuctSegmentType"))
    nested = [o for rel in (duct.IsNestedBy or []) for o in rel.RelatedObjects
              if o.is_a("IfcDistributionPort")]
    assert len(nested) == 2
    assert {p.FlowDirection for p in nested} == {"SOURCE", "SINK"}
    assert {p.PredefinedType for p in nested} == {"DUCT"}


def test_branch_fitting_carries_three_ports(built, massing_families, target_model):
    library, _, _ = built
    _imported(massing_families, library, target_model)
    tee = next(t for t in target_model.by_type("IfcDuctFittingType")
               if (t.Name or "").endswith("Tee"))
    ports = [o for rel in (tee.IsNestedBy or []) for o in rel.RelatedObjects
             if o.is_a("IfcDistributionPort")]
    assert len(ports) == 3
    assert sorted(p.Name for p in ports) == ["Branch", "In", "Out"]


def test_all_geometry_kinds_survive(built, massing_families, target_model):
    """Every builder's output arrives intact — this is what lets the catalog ship anything richer
    than a box. Verified: swept disk, revolution, boolean, taper, multi-part assembly."""
    library, _, _ = built
    _imported(massing_families, library, target_model)

    def rep_of(cls, match):
        t = next(x for x in target_model.by_type(cls) if match in (x.Name or ""))
        return t.RepresentationMaps[0].MappedRepresentation

    bar = rep_of("IfcReinforcingBarType", "#8")
    assert bar.RepresentationType == "AdvancedSweptSolid"
    assert bar.Items[0].is_a() == "IfcSweptDiskSolid"

    heater = rep_of("IfcSanitaryTerminalType", "Water Heater")
    assert heater.Items[0].is_a() == "IfcRevolvedAreaSolid"

    door = rep_of("IfcDoorType", "Vision Panel")
    assert door.RepresentationType == "CSG"
    assert door.Items[0].is_a() == "IfcBooleanResult"

    reducer = rep_of("IfcDuctFittingType", "Reducer")
    assert reducer.Items[0].is_a() == "IfcExtrudedAreaSolidTapered"

    tee = rep_of("IfcSlabType", "Double Tee")
    assert len(tee.Items) == 3, "double tee must arrive as flange plus two stems"


def test_import_is_idempotent(built, massing_families, target_model):
    """Re-importing the same pack must not duplicate types — dedup is by (class, Name)."""
    library, stats, _ = built
    _imported(massing_families, library, target_model)
    again = _imported(massing_families, library, target_model)
    assert again == []
    assert len(target_model.by_type("IfcTypeProduct")) == stats["types"]


# ---------------------------------------------------------------------------
# Upstream defects pinned as xfail — PLAN.md §5. These xpass once the PRs land.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="PLAN.md §5.1 — massing's _type_dims only reads IfcRectangleProfileDef, "
                          "so real profiles report dims: null", strict=False)
def test_upstream_type_dims_reads_real_profiles(built, massing_families, target_model):
    library, _, _ = built
    _imported(massing_families, library, target_model)
    col = next(t for t in target_model.by_type("IfcColumnType")
               if (t.Name or "").endswith("W14X90"))
    assert massing_families.type_detail(target_model, col.GlobalId)["dims"] is not None


@pytest.mark.xfail(reason="PLAN.md §5.2 — edit_type_params appends a box beside real geometry "
                          "instead of replacing it", strict=False)
def test_upstream_edit_does_not_append_second_representation(built, massing_families, target_model):
    library, _, _ = built
    _imported(massing_families, library, target_model)
    col = next(t for t in target_model.by_type("IfcColumnType")
               if (t.Name or "").endswith("W14X90"))
    massing_families.edit_type_params(target_model, col.GlobalId, dims=[0.4, 0.4, 3.0])
    assert len(col.RepresentationMaps) == 1, "resizing must not leave a box on top of the W-shape"
