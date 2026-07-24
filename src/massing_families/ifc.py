"""IFC file/context helpers shared by every builder.

Note the unit asymmetry in IfcOpenShell's geometry API, which is easy to get wrong: **profile
parameters must be pre-scaled into file units**, while **`depth` is passed in metres** and scaled
internally by `geometry.add_profile_representation`. Massing's own `_assign_box_representation` does
exactly this (`XDim=w / scale` but `depth=h`). We mirror it, and route every builder through
`scaled()` / `extrude()` so the rule lives in one place.

Packs are authored in METRES (scale == 1), so this only matters if a builder is ever pointed at a
non-metric target file — but getting it right costs nothing and prevents a silent 3.28x geometry bug.
"""
from __future__ import annotations

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.util.unit as uunit

SCHEMA = "IFC4"


def new_library(name: str = "Massing Family Library") -> ifcopenshell.file:
    """A minimal IFC4 project with a Body context — the shell every pack is written into."""
    model = ifcopenshell.api.run("project.create_file", version=SCHEMA)
    ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcProject", name=name)
    ifcopenshell.api.run("unit.assign_unit", model, length={"is_metric": True, "raw": "METERS"})
    ctx = ifcopenshell.api.run("context.add_context", model, context_type="Model")
    ifcopenshell.api.run("context.add_context", model, context_type="Model",
                         context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)
    return model


def body_context(model: ifcopenshell.file):
    """The Body/MODEL_VIEW subcontext types are represented in."""
    for c in model.by_type("IfcGeometricRepresentationSubContext"):
        if c.ContextIdentifier == "Body":
            return c
    for c in model.by_type("IfcGeometricRepresentationContext"):
        if c.ContextType == "Model":
            return c
    return None


def unit_scale(model: ifcopenshell.file) -> float:
    """Metres per file unit."""
    return uunit.calculate_unit_scale(model)


def scaled(model: ifcopenshell.file, metres: float) -> float:
    """Metres -> file units. Use for every *profile parameter*."""
    return float(metres) / unit_scale(model)


def point2d(model: ifcopenshell.file, x: float = 0.0, y: float = 0.0):
    return model.create_entity("IfcCartesianPoint", (float(x), float(y)))


def placement2d(model: ifcopenshell.file, x: float = 0.0, y: float = 0.0):
    return model.create_entity("IfcAxis2Placement2D", Location=point2d(model, x, y),
                               RefDirection=model.create_entity("IfcDirection", (1.0, 0.0)))


def extrude(model: ifcopenshell.file, profile, depth_m: float):
    """Sweep a profile. `depth_m` is METRES — the API scales it internally (see module docstring)."""
    return ifcopenshell.api.run("geometry.add_profile_representation", model,
                                context=body_context(model), profile=profile, depth=float(depth_m))


def point3d(model: ifcopenshell.file, x: float, y: float, z: float):
    return model.create_entity("IfcCartesianPoint", (float(x), float(y), float(z)))


def polyline3d(model: ifcopenshell.file, pts_m) -> "ifcopenshell.entity_instance":
    """A 3D polyline directrix from [[x, y, z], ...] in METRES (scaled here to file units)."""
    s = unit_scale(model)
    return model.create_entity("IfcPolyline", Points=[
        point3d(model, p[0] / s, p[1] / s, p[2] / s) for p in pts_m])


def placement3d(model: ifcopenshell.file, origin_m=(0.0, 0.0, 0.0), axis=None, ref=None):
    s = unit_scale(model)
    kw = {"Location": point3d(model, origin_m[0] / s, origin_m[1] / s, origin_m[2] / s)}
    if axis:
        kw["Axis"] = model.create_entity("IfcDirection", tuple(float(v) for v in axis))
    if ref:
        kw["RefDirection"] = model.create_entity("IfcDirection", tuple(float(v) for v in ref))
    return model.create_entity("IfcAxis2Placement3D", **kw)


def shape_representation(model: ifcopenshell.file, items, rep_type: str):
    """Wrap solids in an IfcShapeRepresentation on the Body context.

    `rep_type` must match what the items actually are — viewers and downstream tools key off it:
      SweptSolid          IfcExtrudedAreaSolid / IfcRevolvedAreaSolid
      AdvancedSweptSolid  IfcSweptDiskSolid / IfcExtrudedAreaSolidTapered
      CSG                 IfcBooleanResult
      Clipping            IfcBooleanClippingResult
      Tessellation        IfcTriangulatedFaceSet / IfcPolygonalFaceSet
    """
    return model.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=body_context(model),
        RepresentationIdentifier="Body",
        RepresentationType=rep_type,
        Items=list(items),
    )


def assign(model: ifcopenshell.file, product, representation) -> None:
    ifcopenshell.api.run("geometry.assign_representation", model, product=product,
                         representation=representation)


def clear_representations(model: ifcopenshell.file, type_product) -> None:
    """Drop any existing RepresentationMaps before assigning a new one.

    This is the discipline massing's `edit_type_params` is missing (PLAN.md §5): assigning without
    clearing *appends* a second map, so a real profile ends up rendered with a box on top of it.
    """
    for rm in list(getattr(type_product, "RepresentationMaps", None) or []):
        try:
            model.remove(rm)
        except Exception:
            pass
    if hasattr(type_product, "RepresentationMaps"):
        type_product.RepresentationMaps = None
