"""Geometry builders, one per tier/archetype.

A spec declares `builder:` and the registry dispatches. Every builder returns an IfcShapeRepresentation
ready to assign to a type product, or None if it cannot build (caller falls back to the box).

    box          L200  sized rectangle extrusion — parity with massing today, and the fallback
    profile      L300  parameterized profile sweeps (I/T/U/L-shape, hollow, circle)
    swept_disk   L300  circular section along a path — rebar, handrails, bent tube
    revolve      L300  profile revolved about an axis — tanks, domes, fixtures
    boolean      L300  base solid minus voids — vision panels, louvres, penetrations
    taper        L300  section changing end to end — duct transitions, reducers
    assembly     L350  several positioned solids as one type — stairs, trusses, headwalls
    mesh         --    tessellated faces — landing format for imported/organic geometry
"""
from __future__ import annotations

from . import assembly, boolean, box, mesh, profile, revolve, swept_disk, taper

BUILDERS = {
    "box": box.build,
    "profile": profile.build,
    "swept_disk": swept_disk.build,
    "revolve": revolve.build,
    "boolean": boolean.build,
    "taper": taper.build,
    "assembly": assembly.build,
    "mesh": mesh.build,
}


def build_geometry(model, spec, variant):
    """Dispatch to the spec's builder, falling back to the box proxy if it yields nothing."""
    fn = BUILDERS.get(spec.builder)
    if fn is None:
        raise ValueError(f"unknown builder {spec.builder!r} for family {spec.key!r}; "
                         f"have {sorted(BUILDERS)}")
    rep = fn(model, spec, variant)
    if rep is None and spec.builder != "box":
        rep = box.build(model, spec, variant)
    return rep


__all__ = ["BUILDERS", "build_geometry", "assembly", "boolean", "box", "mesh", "profile",
           "revolve", "swept_disk", "taper"]
