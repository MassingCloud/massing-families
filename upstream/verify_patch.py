"""Verify the upstream patch actually fixes the two PLAN.md §5 defects.

Loads `families.patched.py` as a drop-in replacement for massing's `aec_data.families` and re-runs the
exact scenarios that fail against the unpatched module (the two `xfail`s in
`tests/test_roundtrip_golden.py`).

    python upstream/verify_patch.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MASSING_SRC = Path(r"C:\Server\modelmaker\services\data\src")
sys.path.insert(0, str(MASSING_SRC))
sys.path.insert(0, str(REPO / "src"))

import ifcopenshell.api  # noqa: E402

from massing_families.ifc import assign, extrude, new_library, placement2d  # noqa: E402


def load(name: str, path: Path):
    """Load a families module.

    It must be loaded *inside* the `aec_data` package — `_assign_box_representation` does a lazy
    `from .edit import _body_context`, which only resolves with a package context.
    """
    import aec_data                                        # noqa: F401  (establishes the package)
    spec = importlib.util.spec_from_file_location(name, path,
                                                  submodule_search_locations=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "aec_data"
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def make_w_shape(model, name="W14X90"):
    """A type carrying real (non-box) geometry — the case both defects mishandle."""
    prof = model.create_entity(
        "IfcIShapeProfileDef", ProfileType="AREA", ProfileName=name,
        Position=placement2d(model),
        OverallWidth=0.3683, OverallDepth=0.3556, WebThickness=0.011176,
        FlangeThickness=0.018034, FilletRadius=0.01524)
    typ = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcColumnType", name=name)
    assign(model, typ, extrude(model, prof, 3.6576))
    return typ


def check(mod, label):
    print(f"\n=== {label} ===")

    # Defect 1 — type_detail must report dims for real profiles
    m = new_library()
    typ = make_w_shape(m)
    dims = mod.type_detail(m, typ.GlobalId)["dims"]
    ok1 = dims is not None
    print(f"  type_detail dims for W14X90 : {dims}   -> {'OK' if ok1 else 'NULL (defect 1)'}")

    # Defect 2 — resizing must replace geometry, not append a box beside it
    m2 = new_library()
    typ2 = make_w_shape(m2)
    before = len(typ2.RepresentationMaps or [])
    mod.edit_type_params(m2, typ2.GlobalId, dims=[0.4, 0.4, 3.0])
    after = len(typ2.RepresentationMaps or [])
    kinds = [rm.MappedRepresentation.Items[0].SweptArea.is_a()
             for rm in (typ2.RepresentationMaps or [])]
    ok2 = after == 1
    print(f"  RepresentationMaps {before} -> {after} {kinds}"
          f"   -> {'OK' if ok2 else 'DUPLICATE GEOMETRY (defect 2)'}")

    # Regression — the ordinary box path must still resize in place, GUID-stably
    m3 = new_library()
    guid = mod.create_type(m3, "IfcFurnitureType", "Desk", dims=[1.4, 0.7, 0.75])
    mod.edit_type_params(m3, guid, dims=[1.6, 0.8, 0.75])
    box_dims = mod.type_detail(m3, guid)["dims"]
    ok3 = box_dims == [1.6, 0.8, 0.75] and len(m3.by_guid(guid).RepresentationMaps) == 1
    print(f"  box resize still works      : {box_dims}   -> {'OK' if ok3 else 'REGRESSION'}")

    return ok1, ok2, ok3


if __name__ == "__main__":
    before = check(load("aec_data.families", MASSING_SRC / "aec_data" / "families.py"),
                   "UNPATCHED (current massing)")
    after = check(load("patched_families", REPO / "upstream" / "families.patched.py"),
                  "PATCHED")

    print("\n--- summary ---")
    for i, name in enumerate(["type_detail reads real profiles",
                              "resize replaces instead of appending",
                              "box resize regression"]):
        print(f"  {name:38} before={'PASS' if before[i] else 'FAIL'}  "
              f"after={'PASS' if after[i] else 'FAIL'}")
    raise SystemExit(0 if all(after) else 1)
