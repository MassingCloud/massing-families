"""L300 tapered extrusion — a solid whose section changes end to end.

Duct transitions and reducers, tapered columns, hoppers. IFC has `IfcExtrudedAreaSolidTapered`, which
carries both end profiles, so the taper is parametric rather than faked with a mesh.

    builder: taper
    taper:
      start: {kind: Circle, params: {Radius: '8"'}}
      end:   {kind: Circle, params: {Radius: '6"'}}
      depth: '12"'
"""
from __future__ import annotations

from .. import ifc
from ..units import metres
from .profile import build_profile_entity


def build(model, spec, variant):
    cfg = {**(spec.taper or {}), **(variant.taper or {})}
    if not cfg:
        return None
    for key in ("start", "end"):
        if not cfg.get(key):
            raise ValueError(f"family {spec.key!r}: taper needs both `start` and `end` profiles")

    start = build_profile_entity(model, spec, variant, cfg["start"], name=f"{variant.name} start")
    end = build_profile_entity(model, spec, variant, cfg["end"], name=f"{variant.name} end")

    depth = cfg.get("depth")
    if depth is None:
        dims = variant.dims_metres or spec.dims_metres
        depth_m = dims[2] if dims else None
    else:
        depth_m = metres(depth)
    if not depth_m or depth_m <= 0:
        raise ValueError(f"family {spec.key!r} type {variant.name!r}: taper needs a positive depth")

    solid = model.create_entity(
        "IfcExtrudedAreaSolidTapered",
        SweptArea=start,
        Position=ifc.placement3d(model),
        ExtrudedDirection=model.create_entity("IfcDirection", (0.0, 0.0, 1.0)),
        Depth=ifc.scaled(model, depth_m),
        EndSweptArea=end,
    )
    return ifc.shape_representation(model, [solid], "AdvancedSweptSolid")
