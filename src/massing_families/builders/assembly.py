"""L350 assembly — one type whose geometry is several positioned solids.

Stairs (stringers + treads), trusses (chords + webs), headwalls, curtain-wall modules: things that read
as one placeable, schedulable object but are visibly made of parts. Each part is a real positioned
solid in the same representation, so the object looks like what it is instead of a bounding box.

    builder: assembly
    assembly:
      parts:
        - {kind: Rectangle, params: {XDim: '2"', YDim: '12"'}, depth: "10'-0\\"",
           at: [0, 0, 0], name: Stringer}
        - {kind: Rectangle, params: {XDim: "4'-0\\"", YDim: '11"'}, depth: '2"',
           at: [0, 0, '7"'], name: Tread 1}
"""
from __future__ import annotations

from .. import ifc
from ..units import metres
from .profile import build_profile_entity


def build(model, spec, variant):
    cfg = {**(spec.assembly or {}), **(variant.assembly or {})}
    if not cfg:
        return None
    parts = cfg.get("parts")
    if not parts:
        raise ValueError(f"family {spec.key!r}: assembly needs a `parts` list")

    solids = []
    for i, part in enumerate(parts):
        depth = part.get("depth")
        if depth is None:
            raise ValueError(f"family {spec.key!r}: assembly part {i} needs a `depth`")
        prof = build_profile_entity(model, spec, variant, part,
                                    name=part.get("name") or f"{variant.name} part {i + 1}")
        at = part.get("at") or [0, 0, 0]
        if len(at) != 3:
            raise ValueError(f"family {spec.key!r}: assembly part {i} `at` needs [x, y, z]")
        origin = [metres(v) for v in at]
        solids.append(model.create_entity(
            "IfcExtrudedAreaSolid",
            SweptArea=prof,
            Position=ifc.placement3d(model, origin),
            ExtrudedDirection=model.create_entity("IfcDirection", (0.0, 0.0, 1.0)),
            Depth=ifc.scaled(model, metres(depth)),
        ))
    return ifc.shape_representation(model, solids, "SweptSolid")


def repeat(count: int, step, base_at=(0, 0, 0), **part):
    """Helper for catalog authors writing repetitive assemblies (stair treads, truss webs) in Python
    rather than by hand in YAML. Not used by the YAML path; exported for tooling."""
    out = []
    for i in range(count):
        at = [base_at[0] + step[0] * i, base_at[1] + step[1] * i, base_at[2] + step[2] * i]
        out.append({**part, "at": at, "name": f"{part.get('name', 'part')} {i + 1}"})
    return out
