"""L300 revolution — a profile swept about an axis.

Real rotational geometry: tank and water-heater domes, bollard caps, sanitary fixtures, valve bodies.
A revolved profile is genuinely round, unlike an extruded circle which is only a straight cylinder.

    builder: revolve
    revolve:
      profile: {kind: Rectangle, params: {XDim: '10"', YDim: '30"'}}
      angle: 360                      # degrees
      axis_offset: '11"'              # distance from the profile origin to the axis of revolution
"""
from __future__ import annotations

from .. import ifc
from ..units import metres
from .profile import build_profile_entity


def build(model, spec, variant):
    cfg = {**(spec.revolve or {}), **(variant.revolve or {})}
    if not cfg:
        return None

    pdef = cfg.get("profile")
    if not pdef:
        raise ValueError(f"family {spec.key!r}: revolve needs a `profile` definition")
    prof = build_profile_entity(model, spec, variant, pdef, name=variant.name)

    angle = float(cfg.get("angle", 360))
    if not 0 < angle <= 360:
        raise ValueError(f"family {spec.key!r}: revolve angle must be in (0, 360], got {angle}")

    offset = metres(cfg.get("axis_offset", 0)) if cfg.get("axis_offset") else 0.0
    # revolve about the Y axis, displaced by axis_offset in X — the usual "spin a section" setup
    axis = model.create_entity(
        "IfcAxis1Placement",
        Location=ifc.point3d(model, ifc.scaled(model, offset), 0.0, 0.0),
        Axis=model.create_entity("IfcDirection", (0.0, 1.0, 0.0)),
    )
    solid = model.create_entity(
        "IfcRevolvedAreaSolid",
        SweptArea=prof,
        Position=ifc.placement3d(model),
        Axis=axis,
        Angle=angle,
    )
    return ifc.shape_representation(model, [solid], "SweptSolid")
