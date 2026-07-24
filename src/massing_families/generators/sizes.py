"""Nominal-size generator — the workhorse for routing content.

Duct, conduit, cable tray, copper and plastic pipe are all "one shape, many trade sizes". This expands
a size table into catalogued types, computing the profile parameters (radius from OD, fillets from wall)
so the YAML stays a readable size schedule rather than repeated geometry.

Two modes:

    entries:  round/tubular — [{nominal, od, wall?}, ...]      -> Circle | CircleHollow
    sections: rectangular   — [[width, height], ...]           -> Rectangle | RectangleHollow

All dimensions are inches. `wall` may be given once at the top level (sheet-metal gauge, tray depth)
or per entry (pipe schedules, where it varies by size).
"""
from __future__ import annotations

from ..spec import TypeVariant

ROUND = {"Circle", "CircleHollow"}
RECT = {"Rectangle", "RectangleHollow"}


def _fmt(template: str, **kw) -> str:
    try:
        return template.format(**kw)
    except KeyError as e:
        raise ValueError(f"name template {template!r} references unknown field {e}") from None


def generate(spec) -> list[TypeVariant]:
    args = spec.generator_args or {}
    kind = args.get("kind")
    if kind not in ROUND | RECT:
        raise ValueError(f"family {spec.key!r}: generator_args.kind must be one of "
                         f"{sorted(ROUND | RECT)}, got {kind!r}")
    length = args.get("length", "10'-0\"")
    default_wall = args.get("wall")
    psets = dict(args.get("psets") or {})
    out: list[TypeVariant] = []

    if kind in ROUND:
        entries = args.get("entries")
        if not entries:
            raise ValueError(f"family {spec.key!r}: round kinds need generator_args.entries")
        template = args.get("name", '{nominal}"')
        for e in entries:
            od = float(e["od"])
            wall = e.get("wall", default_wall)
            params = {"Radius": round(od / 2, 5)}
            if kind == "CircleHollow":
                if wall is None:
                    raise ValueError(f"family {spec.key!r}: CircleHollow needs a wall thickness "
                                     f"(top-level `wall` or per-entry)")
                params["WallThickness"] = float(wall)
            out.append(TypeVariant(
                name=_fmt(template, **e),
                dims=[od, od, length],
                profile={"kind": kind, "params": params, "name": _fmt(template, **e)},
                psets={**psets, "MF_Routing": {"NominalSize": str(e["nominal"]),
                                               "OutsideDiameter": od}},
            ))
    else:
        sections = args.get("sections")
        if not sections:
            raise ValueError(f"family {spec.key!r}: rectangular kinds need generator_args.sections")
        template = args.get("name", '{w}" x {h}"')
        for sec in sections:
            w, h = float(sec[0]), float(sec[1])
            params = {"XDim": w, "YDim": h}
            if kind == "RectangleHollow":
                wall = default_wall if len(sec) < 3 else sec[2]
                if wall is None:
                    raise ValueError(f"family {spec.key!r}: RectangleHollow needs a wall thickness")
                wall = float(wall)
                params.update(WallThickness=wall,
                              OuterFilletRadius=round(2 * wall, 5),
                              InnerFilletRadius=round(wall, 5))
            name = _fmt(template, w=f"{w:g}", h=f"{h:g}")
            out.append(TypeVariant(
                name=name,
                dims=[w, h, length],
                profile={"kind": kind, "params": params, "name": name},
                psets={**psets, "MF_Routing": {"NominalSize": name}},
            ))

    if not out:
        raise ValueError(f"family {spec.key!r}: sizes generator produced nothing")
    return out
