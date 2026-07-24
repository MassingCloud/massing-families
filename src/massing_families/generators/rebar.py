"""Reinforcing bar generator — ASTM A615/A706 imperial bar sizes swept as real round bars.

Rebar was the largest single gap in the structural catalog, and it needs the `swept_disk` builder:
a #8 bar is a 1" round solid following a path, not a box. Straight bars, stirrups and hooked bars all
come from the same size table with different paths.

    generator: rebar
    generator_args: {sizes: [3, 4, 5, 6, 8], length: "20'-0\\"", shape: straight}

`shape`:
    straight   a single run of `length`
    stirrup    a closed rectangular tie of `width` x `height`
    hook       a straight run with a 90-degree hook of `hook` at the far end

Nominal diameters are the published ASTM A615 values: bar number / 8 inches for #3-#8, then the
tabulated values for #9-#18 (which are area-equivalent, not eighths).
"""
from __future__ import annotations

from ..spec import TypeVariant
from ..units import metres

# ASTM A615 nominal diameters, inches
BAR_DIAMETER = {
    3: 0.375, 4: 0.500, 5: 0.625, 6: 0.750, 7: 0.875, 8: 1.000,
    9: 1.128, 10: 1.270, 11: 1.410, 14: 1.693, 18: 2.257,
}


def _path(shape, length, width, height, hook):
    if shape == "straight":
        return [[0, 0, 0], [0, 0, length]]
    if shape == "hook":
        return [[0, 0, 0], [0, 0, length], [hook, 0, length]]
    if shape == "stirrup":                      # closed rectangular tie
        return [[0, 0, 0], [width, 0, 0], [width, 0, height], [0, 0, height], [0, 0, 0]]
    raise ValueError(f"unknown rebar shape {shape!r}; have straight, hook, stirrup")


def generate(spec) -> list[TypeVariant]:
    args = spec.generator_args or {}
    sizes = args.get("sizes") or sorted(BAR_DIAMETER)
    shape = args.get("shape", "straight")
    length = args.get("length", "20'-0\"")
    width = args.get("width", '12"')
    height = args.get("height", '20"')
    hook = args.get("hook", '6"')

    unknown = [s for s in sizes if int(s) not in BAR_DIAMETER]
    if unknown:
        raise ValueError(f"family {spec.key!r}: unknown bar size(s) {unknown}; "
                         f"have {sorted(BAR_DIAMETER)}")

    l_m, w_m, h_m, hk_m = metres(length), metres(width), metres(height), metres(hook)
    out = []
    for size in sizes:
        dia = BAR_DIAMETER[int(size)]
        dia_m = metres(dia)
        path = _path(shape, l_m, w_m, h_m, hk_m)
        if shape == "stirrup":
            dims = [w_m, dia_m, h_m]
            label = f"#{size} stirrup {width} x {height}"
        elif shape == "hook":
            dims = [hk_m, dia_m, l_m]
            label = f"#{size} hooked {length}"
        else:
            dims = [dia_m, dia_m, l_m]
            label = f"#{size} x {length}"
        out.append(TypeVariant(
            name=label,
            dims=[f"{d / 0.0254:g}" for d in dims],       # back to inches for the imperial pipeline
            swept_disk={"diameter": dia, "path": [[c / 0.0254 for c in p] for p in path]},
            psets={"MF_Structural": {"BarSize": f"#{size}", "NominalDiameter": dia,
                                     "BarShape": shape,
                                     "Specification": "ASTM A615 Grade 60"}},
        ))
    return out
