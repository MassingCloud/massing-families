"""Geometry builders — box parity and real parametric profiles."""
from __future__ import annotations

import pytest

from massing_families.builders import build_geometry
from massing_families.builders.profile import _length_attrs
from massing_families.ifc import new_library
from massing_families.spec import FamilySpec

BOX = {"key": "b", "label": "Box", "ifc_class": "IfcFurnitureType", "category": "C",
       "discipline": "d", "builder": "box", "dims": ["4'-0\"", "2'-0\"", "2'-6\""]}

WSHAPE = {"key": "w", "label": "W Column", "ifc_class": "IfcColumnType", "category": "C",
          "discipline": "structural", "builder": "profile", "tier": "L300",
          "profile": {"kind": "IShape"},
          "types": [{"name": "W14X90", "dims": ['14.5"', '14.0"', "12'-0\""],
                     "profile": {"params": {"OverallWidth": '14.5"', "OverallDepth": '14.0"',
                                            "WebThickness": '0.440"', "FlangeThickness": '0.710"',
                                            "FilletRadius": '0.600"'}}}]}


def _solid(model, rep):
    return rep.Items[0]


def test_box_builds_rectangle_profile():
    model = new_library()
    spec = FamilySpec.from_dict(BOX)
    rep = build_geometry(model, spec, spec.resolved_types()[0])
    solid = _solid(model, rep)
    assert solid.SweptArea.is_a() == "IfcRectangleProfileDef"
    assert solid.SweptArea.XDim == pytest.approx(1.2192)      # 4'-0"
    assert solid.Depth == pytest.approx(0.762)                # 2'-6"


def test_profile_builds_real_ishape_with_exact_params():
    """The headline: a steel column is an actual W-shape, not a cube."""
    model = new_library()
    spec = FamilySpec.from_dict(WSHAPE)
    rep = build_geometry(model, spec, spec.types[0])
    prof = _solid(model, rep).SweptArea
    assert prof.is_a() == "IfcIShapeProfileDef"
    assert prof.OverallWidth == pytest.approx(0.3683)         # 14.5"
    assert prof.OverallDepth == pytest.approx(0.3556)         # 14.0"
    assert prof.WebThickness == pytest.approx(0.011176)       # 0.440"
    assert prof.FlangeThickness == pytest.approx(0.018034)    # 0.710"
    assert _solid(model, rep).Depth == pytest.approx(3.6576)  # 12'-0"


def test_length_params_scaled_but_angles_are_not():
    """Scaling is decided by the IFC schema's measure types, not a hardcoded list."""
    assert "OverallWidth" in _length_attrs("IfcIShapeProfileDef")
    assert "FlangeSlope" not in _length_attrs("IfcIShapeProfileDef")   # plane angle
    assert "LegSlope" not in _length_attrs("IfcLShapeProfileDef")
    assert {"Radius", "WallThickness"} <= _length_attrs("IfcCircleHollowProfileDef")


def test_unknown_profile_attribute_is_rejected():
    bad = {**WSHAPE, "types": [{"name": "T", "dims": [1, 1, 1],
                                "profile": {"params": {"Bogus": '1"'}}}]}
    spec = FamilySpec.from_dict(bad)
    model = new_library()
    with pytest.raises(ValueError, match="has no attribute"):
        build_geometry(model, spec, spec.types[0])


def test_unknown_profile_kind_is_rejected():
    bad = {**WSHAPE, "profile": {"kind": "Hexagon"},
           "types": [{"name": "T", "dims": [1, 1, 1]}]}
    spec = FamilySpec.from_dict(bad)
    model = new_library()
    with pytest.raises(ValueError, match="unknown profile kind"):
        build_geometry(model, spec, spec.types[0])
