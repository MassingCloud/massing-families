"""L200 box proxy — a sized rectangle extruded to height.

Deliberately identical in output to massing's `_assign_box_representation` so this tier is a drop-in
parity baseline: existing behaviour is never regressed, and any family without a richer builder still
produces exactly what the platform produces today.
"""
from __future__ import annotations

from .. import ifc


def build(model, spec, variant):
    dims = variant.dims_metres or spec.dims_metres
    if not dims:
        return None
    w, d, h = dims
    prof = model.create_entity(
        "IfcRectangleProfileDef", ProfileType="AREA",
        ProfileName=spec.type_name(variant),
        Position=ifc.placement2d(model),
        XDim=ifc.scaled(model, w), YDim=ifc.scaled(model, d),
    )
    return ifc.extrude(model, prof, h)
