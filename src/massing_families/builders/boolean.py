"""L300 boolean — a base solid with material cut out of it.

This is what makes a door a door rather than a slab: a leaf with a vision panel, a louvre with its
blade openings, a sink with a basin, a member with a penetration.

    builder: boolean
    boolean:
      base:  {kind: Rectangle, params: {XDim: "3'-0\\"", YDim: '1 3/4"'}, depth: "7'-0\\""}
      voids:
        - {kind: Rectangle, params: {XDim: '10"', YDim: '4"'}, depth: '24"',
           at: ['13"', 0, "4'-6\\""]}
"""
from __future__ import annotations

from .. import ifc
from ..units import metres
from .profile import build_profile_entity


def _solid(model, spec, variant, pdef, at=None):
    prof = build_profile_entity(model, spec, variant, pdef, name=pdef.get("name") or variant.name)
    depth = pdef.get("depth")
    if depth is None:
        raise ValueError(f"family {spec.key!r}: boolean solids each need a `depth`")
    origin = [metres(v) for v in at] if at else (0.0, 0.0, 0.0)
    return model.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=prof,
        Position=ifc.placement3d(model, origin),
        ExtrudedDirection=model.create_entity("IfcDirection", (0.0, 0.0, 1.0)),
        Depth=ifc.scaled(model, metres(depth)),
    )


def build(model, spec, variant):
    cfg = {**(spec.boolean or {}), **(variant.boolean or {})}
    if not cfg:
        return None
    base_def = cfg.get("base")
    if not base_def:
        raise ValueError(f"family {spec.key!r}: boolean needs a `base` solid")
    result = _solid(model, spec, variant, base_def)

    voids = cfg.get("voids") or []
    if not voids:
        raise ValueError(f"family {spec.key!r}: boolean with no `voids` — use the profile builder")
    for void in voids:
        cut = _solid(model, spec, variant, void, at=void.get("at"))
        result = model.create_entity("IfcBooleanResult", Operator="DIFFERENCE",
                                     FirstOperand=result, SecondOperand=cut)
    return ifc.shape_representation(model, [result], "CSG")
