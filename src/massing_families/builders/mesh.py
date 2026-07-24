"""Tessellated geometry — the landing format for imported or organic forms.

Per PLAN.md §8g tier 3, most content is fabricated parametrically; this builder exists for the minority
that genuinely cannot be (organic shapes, scanned or donated CC0 geometry). `IfcTriangulatedFaceSet` is
compact and universally supported.

Anything built here should also carry `MF_Library.GeometryStatus` so consumers can tell fabricated
geometry from imported geometry.

    builder: mesh
    mesh:
      vertices: [[0,0,0], ["4'-0\\"",0,0], ["4'-0\\"","2'-0\\"",0], [0,"2'-0\\"",0]]
      faces: [[1,2,3], [1,3,4]]        # 1-based indices, per the IFC spec
"""
from __future__ import annotations

from .. import ifc
from ..units import metres


def build(model, spec, variant):
    cfg = {**(spec.mesh or {}), **(variant.mesh or {})}
    if not cfg:
        return None
    verts = cfg.get("vertices")
    faces = cfg.get("faces")
    if not verts or not faces:
        raise ValueError(f"family {spec.key!r}: mesh needs `vertices` and `faces`")

    s = ifc.unit_scale(model)
    coords = []
    for v in verts:
        if len(v) != 3:
            raise ValueError(f"family {spec.key!r}: mesh vertices need [x, y, z], got {v!r}")
        coords.append(tuple(metres(c) / s for c in v))

    n = len(coords)
    for f in faces:
        if len(f) != 3:
            raise ValueError(f"family {spec.key!r}: mesh faces must be triangles, got {f!r}")
        if any(not (1 <= int(i) <= n) for i in f):
            raise ValueError(f"family {spec.key!r}: mesh face {f!r} indexes outside 1..{n} "
                             f"(IFC face indices are 1-based)")

    point_list = model.create_entity("IfcCartesianPointList3D", CoordList=coords)
    solid = model.create_entity(
        "IfcTriangulatedFaceSet",
        Coordinates=point_list,
        CoordIndex=[tuple(int(i) for i in f) for f in faces],
        Closed=bool(cfg.get("closed", False)),
    )
    return ifc.shape_representation(model, [solid], "Tessellation")
