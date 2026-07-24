"""The six builders beyond box/profile — swept_disk, revolve, boolean, taper, assembly, mesh.

Each produces a distinct IFC solid type with the correct RepresentationType, because viewers and
downstream tooling key off that string. All six are verified to survive massing's import in
`test_roundtrip_golden.py`.
"""
from __future__ import annotations

import pytest

from massing_families.builders import BUILDERS, build_geometry
from massing_families.generators.rebar import BAR_DIAMETER, generate as gen_rebar
from massing_families.ifc import new_library
from massing_families.spec import FamilySpec

BASE = {"key": "t", "label": "T", "category": "C", "discipline": "d", "tier": "L300"}


def _rep(extra, ifc_class="IfcBuildingElementProxyType"):
    spec = FamilySpec.from_dict({**BASE, "ifc_class": ifc_class, **extra})
    model = new_library()
    return model, spec, build_geometry(model, spec, spec.resolved_types()[0])


def test_all_builders_registered():
    assert set(BUILDERS) == {"box", "profile", "swept_disk", "revolve", "boolean",
                             "taper", "assembly", "mesh"}


def test_swept_disk_is_a_real_round_solid():
    _, _, rep = _rep({"builder": "swept_disk", "dims": ['1"', '1"', "20'-0\""],
                      "swept_disk": {"diameter": '1"', "path": [[0, 0, 0], [0, 0, "20'-0\""]]}})
    assert rep.RepresentationType == "AdvancedSweptSolid"
    solid = rep.Items[0]
    assert solid.is_a() == "IfcSweptDiskSolid"
    assert solid.Radius == pytest.approx(0.0127)          # 1/2" in exact metres
    assert len(solid.Directrix.Points) == 2


def test_swept_disk_follows_a_bent_path():
    _, _, rep = _rep({"builder": "swept_disk", "dims": ['1"', '1"', "10'-0\""],
                      "swept_disk": {"diameter": '5/8"',
                                     "path": [[0, 0, 0], [0, 0, "10'-0\""], ['9"', 0, "10'-0\""]]}})
    assert len(rep.Items[0].Directrix.Points) == 3


def test_swept_disk_tube_has_inner_radius():
    _, _, rep = _rep({"builder": "swept_disk", "dims": ['2"', '2"', "10'-0\""],
                      "swept_disk": {"radius": '1"', "inner_radius": '3/4"',
                                     "path": [[0, 0, 0], [0, 0, "10'-0\""]]}})
    assert rep.Items[0].InnerRadius == pytest.approx(0.01905)


def test_swept_disk_rejects_inner_radius_larger_than_outer():
    with pytest.raises(ValueError, match="inner_radius must be smaller"):
        _rep({"builder": "swept_disk", "dims": ['2"', '2"', '2"'],
              "swept_disk": {"radius": '1/2"', "inner_radius": '1"',
                             "path": [[0, 0, 0], [0, 0, '12"']]}})


def test_revolve_produces_a_revolved_solid():
    _, _, rep = _rep({"builder": "revolve", "dims": ['22"', '22"', '60"'],
                      "revolve": {"profile": {"kind": "Rectangle",
                                              "params": {"XDim": '11"', "YDim": '60"'}},
                                  "angle": 360, "axis_offset": '11"'}})
    assert rep.RepresentationType == "SweptSolid"
    assert rep.Items[0].is_a() == "IfcRevolvedAreaSolid"
    assert rep.Items[0].Angle == 360


def test_boolean_actually_cuts_the_base():
    _, _, rep = _rep({"builder": "boolean", "dims": ["3'-0\"", '1 3/4"', "7'-0\""],
                      "boolean": {"base": {"kind": "Rectangle",
                                           "params": {"XDim": "3'-0\"", "YDim": '1 3/4"'},
                                           "depth": "7'-0\""},
                                  "voids": [{"kind": "Rectangle",
                                             "params": {"XDim": '10"', "YDim": '4"'},
                                             "depth": '24"', "at": ['13"', 0, "4'-6\""]}]}})
    assert rep.RepresentationType == "CSG"
    result = rep.Items[0]
    assert result.is_a() == "IfcBooleanResult"
    assert result.Operator == "DIFFERENCE"
    assert result.FirstOperand.is_a() == "IfcExtrudedAreaSolid"


def test_boolean_without_voids_is_rejected():
    with pytest.raises(ValueError, match="no `voids`"):
        _rep({"builder": "boolean", "dims": ['1"', '1"', '1"'],
              "boolean": {"base": {"kind": "Rectangle", "params": {"XDim": '1"', "YDim": '1"'},
                                   "depth": '1"'}}})


def test_taper_carries_both_end_profiles():
    _, _, rep = _rep({"builder": "taper", "dims": ['16"', '16"', '12"'],
                      "taper": {"start": {"kind": "Circle", "params": {"Radius": '8"'}},
                                "end": {"kind": "Circle", "params": {"Radius": '6"'}},
                                "depth": '12"'}})
    assert rep.RepresentationType == "AdvancedSweptSolid"
    solid = rep.Items[0]
    assert solid.is_a() == "IfcExtrudedAreaSolidTapered"
    assert solid.SweptArea.Radius == pytest.approx(0.2032)      # 8"
    assert solid.EndSweptArea.Radius == pytest.approx(0.1524)   # 6"


def test_assembly_produces_multiple_positioned_solids():
    _, _, rep = _rep({"builder": "assembly", "dims": ["4'-0\"", "10'-0\"", "10'-0\""],
                      "assembly": {"parts": [
                          {"kind": "Rectangle", "params": {"XDim": '2"', "YDim": '12"'},
                           "depth": "10'-0\"", "at": [0, 0, 0], "name": "Stringer"},
                          {"kind": "Rectangle", "params": {"XDim": "4'-0\"", "YDim": '11"'},
                           "depth": '2"', "at": [0, 0, '7"'], "name": "Tread"}]}})
    assert len(rep.Items) == 2
    assert all(i.is_a() == "IfcExtrudedAreaSolid" for i in rep.Items)
    # the second part is genuinely offset in Z, not stacked at the origin
    assert rep.Items[1].Position.Location.Coordinates[2] == pytest.approx(0.1778)   # 7"


def test_mesh_produces_a_triangulated_face_set():
    _, _, rep = _rep({"builder": "mesh", "dims": ["4'-0\"", "2'-0\"", '1"'],
                      "mesh": {"vertices": [[0, 0, 0], ["4'-0\"", 0, 0],
                                            ["4'-0\"", "2'-0\"", 0], [0, "2'-0\"", 0]],
                               "faces": [[1, 2, 3], [1, 3, 4]]}})
    assert rep.RepresentationType == "Tessellation"
    fs = rep.Items[0]
    assert fs.is_a() == "IfcTriangulatedFaceSet"
    assert len(fs.Coordinates.CoordList) == 4
    assert len(fs.CoordIndex) == 2


def test_mesh_rejects_out_of_range_face_index():
    with pytest.raises(ValueError, match="indexes outside"):
        _rep({"builder": "mesh", "dims": ['1"', '1"', '1"'],
              "mesh": {"vertices": [[0, 0, 0], [1, 0, 0], [1, 1, 0]], "faces": [[1, 2, 9]]}})


def test_unknown_builder_is_rejected():
    with pytest.raises(ValueError, match="unknown builder"):
        _rep({"builder": "origami", "dims": ['1"', '1"', '1"']})


# --- rebar generator -------------------------------------------------------

def test_rebar_uses_published_astm_diameters():
    assert BAR_DIAMETER[3] == 0.375 and BAR_DIAMETER[8] == 1.0
    assert BAR_DIAMETER[11] == 1.410 and BAR_DIAMETER[18] == 2.257


@pytest.mark.parametrize("shape,points", [("straight", 2), ("hook", 3), ("stirrup", 5)])
def test_rebar_shapes_produce_expected_paths(shape, points):
    spec = FamilySpec.from_dict({**BASE, "ifc_class": "IfcReinforcingBarType",
                                 "builder": "swept_disk", "generator": "rebar",
                                 "generator_args": {"sizes": [5], "shape": shape}})
    variant = gen_rebar(spec)[0]
    assert len(variant.swept_disk["path"]) == points
    assert variant.psets["MF_Structural"]["BarSize"] == "#5"


def test_rebar_rejects_unknown_bar_size():
    spec = FamilySpec.from_dict({**BASE, "ifc_class": "IfcReinforcingBarType",
                                 "builder": "swept_disk", "generator": "rebar",
                                 "generator_args": {"sizes": [13]}})
    with pytest.raises(ValueError, match="unknown bar size"):
        gen_rebar(spec)
