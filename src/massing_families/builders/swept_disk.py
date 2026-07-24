"""L300 swept disk — a circular section swept along a path.

This is the builder that unlocks the largest block of missing content: **reinforcing bar** (straight
bars, hooked bars, stirrups), **handrails with real returns**, and any round member that bends. IFC has
a purpose-built entity for it — `IfcSweptDiskSolid` — so this is genuinely round geometry, not a
faceted approximation.

Spec usage:

    builder: swept_disk
    swept_disk:
      radius: '5/8"'                 # bar radius (or use `diameter:`)
      inner_radius: '1/2"'           # optional — makes it a tube
      path: [[0,0,0], [0,0,"20'-0\\""]]   # polyline in [E, N, Z], imperial

`path` points are imperial dimensions like everything else. A two-point path is a straight bar; more
points give bends (a stirrup, a hooked bar, a handrail with a wall return).
"""
from __future__ import annotations

from .. import ifc
from ..units import metres


def _path_metres(path):
    out = []
    for pt in path:
        if len(pt) != 3:
            raise ValueError(f"swept_disk path points need [x, y, z], got {pt!r}")
        out.append([metres(v) for v in pt])
    return out


def build(model, spec, variant):
    cfg = {**(spec.swept_disk or {}), **(variant.swept_disk or {})}
    if not cfg:
        return None

    if "radius" in cfg:
        radius = metres(cfg["radius"])
    elif "diameter" in cfg:
        radius = metres(cfg["diameter"]) / 2
    else:
        raise ValueError(f"family {spec.key!r}: swept_disk needs `radius` or `diameter`")
    if radius <= 0:
        raise ValueError(f"family {spec.key!r}: swept_disk radius must be positive")

    path = cfg.get("path")
    if not path or len(path) < 2:
        raise ValueError(f"family {spec.key!r}: swept_disk needs a `path` of at least two points")
    pts = _path_metres(path)

    inner = cfg.get("inner_radius")
    inner_m = metres(inner) if inner is not None else None
    if inner_m is not None and inner_m >= radius:
        raise ValueError(f"family {spec.key!r}: inner_radius must be smaller than radius")

    solid = model.create_entity(
        "IfcSweptDiskSolid",
        Directrix=ifc.polyline3d(model, pts),
        Radius=ifc.scaled(model, radius),
        InnerRadius=ifc.scaled(model, inner_m) if inner_m is not None else None,
    )
    return ifc.shape_representation(model, [solid], "AdvancedSweptSolid")
