"""Check that a massing checkout handles this library's geometry correctly.

Was `verify_patch.py`, which compared a patched module against an unpatched one. massing implemented
its own fix in v0.3.662, so there is nothing left to compare — what still matters is whether *the
massing you have* reads and edits real sections properly.

    python upstream/verify_geometry_support.py
    MASSING_ROOT=/path/to/massing python upstream/verify_geometry_support.py

Four behaviours, one per defect found against real content:

1. a real profile reports its dimensions rather than `dims: null`
2. resizing replaces the geometry instead of appending a box through it
3. a hollow section is not silently reshaped as a box  ← the subtle one
4. the ordinary box resize still works (regression)

Defect 3 exists because `IfcRectangleHollowProfileDef` is a *subtype* of
`IfcRectangleProfileDef`, so `is_a("IfcRectangleProfileDef")` is True for it. A resize guarded by
that test rewrites an HSS tube's XDim/YDim, leaves WallThickness alone, keeps the catalog name, and
produces a section in no steel catalog presented as a standard one.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MASSING = Path(os.environ.get("MASSING_ROOT", r"C:\Server\modelmaker"))
sys.path.insert(0, str(MASSING / "services" / "data" / "src"))
sys.path.insert(0, str(REPO / "src"))

import ifcopenshell.api  # noqa: E402

from massing_families.ifc import assign, extrude, new_library, placement2d  # noqa: E402


def _swept(model, profile, depth, ifc_class, name):
    typ = ifcopenshell.api.run("root.create_entity", model, ifc_class=ifc_class, name=name)
    assign(model, typ, extrude(model, profile, depth))
    return typ


def w_shape(model, name="W14X90"):
    return _swept(model, model.create_entity(
        "IfcIShapeProfileDef", ProfileType="AREA", ProfileName=name, Position=placement2d(model),
        OverallWidth=0.3683, OverallDepth=0.3556, WebThickness=0.011176,
        FlangeThickness=0.018034, FilletRadius=0.01524), 3.6576, "IfcColumnType", name)


def hss(model, name="HSS24X12X3/4"):
    return _swept(model, model.create_entity(
        "IfcRectangleHollowProfileDef", ProfileType="AREA", ProfileName=name,
        Position=placement2d(model), XDim=0.6096, YDim=0.3048, WallThickness=0.0177),
        3.6576, "IfcColumnType", name)


def main() -> int:
    if not (MASSING / "services" / "data" / "src" / "aec_data" / "families.py").exists():
        print(f"no massing checkout at {MASSING} — set MASSING_ROOT")
        return 2
    from aec_data import families as F

    results = []

    # 1 — real profile reports dimensions
    m = new_library()
    dims = F.type_detail(m, w_shape(m).GlobalId)["dims"]
    results.append(("real profile reports dims", dims is not None, dims))

    # 2 — resize replaces rather than appends
    m = new_library()
    t = w_shape(m)
    F.edit_type_params(m, t.GlobalId, dims=[0.4, 0.4, 3.0])
    maps = len(t.RepresentationMaps or [])
    results.append(("resize replaces geometry", maps == 1, f"{maps} RepresentationMap(s)"))

    # 3 — a hollow section is not silently reshaped into a box keeping its catalog name
    m = new_library()
    t = hss(m)
    before = t.RepresentationMaps[0].MappedRepresentation.Items[0].SweptArea
    before_dims = (float(before.XDim), float(before.YDim))
    try:
        F.edit_type_params(m, t.GlobalId, dims=[0.5, 0.5, 3.0])
    except Exception:                                       # refusing outright is a valid answer
        pass
    prof = t.RepresentationMaps[0].MappedRepresentation.Items[0].SweptArea
    mutated_in_place = (prof.is_a() == "IfcRectangleHollowProfileDef"
                        and (float(prof.XDim), float(prof.YDim)) != before_dims
                        and (prof.ProfileName or "") == "HSS24X12X3/4")
    results.append(("hollow section not falsified", not mutated_in_place,
                    f"{prof.is_a()} named {prof.ProfileName!r}"))

    # 4 — the ordinary box path still resizes in place (regression)
    m = new_library()
    guid = F.create_type(m, "IfcFurnitureType", "Desk", dims=[1.4, 0.7, 0.75])
    F.edit_type_params(m, guid, dims=[1.6, 0.8, 0.75])
    box = F.type_detail(m, guid)["dims"]
    ok = box == [1.6, 0.8, 0.75] and len(m.by_guid(guid).RepresentationMaps) == 1
    results.append(("box resize regression", ok, box))

    print(f"massing at {MASSING}\n")
    for name, passed, detail in results:
        print(f"  {'PASS' if passed else 'FAIL'}  {name:32} {detail}")
    failed = [n for n, p, _ in results if not p]
    print("\n" + ("all geometry behaviours supported"
                  if not failed else f"unsupported: {', '.join(failed)}"))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
