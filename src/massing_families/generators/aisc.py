"""AISC steel section generator — every standard mill shape as a real parametric profile.

Reads `data/aisc_shapes.csv` (produced by `tools/derive_aisc.py` from the AISC Shapes Database v15.0,
US customary) and expands one family spec into one catalogued type per section, with the correct IFC
profile and its true dimensions. This replaces hand-transcribed section literals — PLAN.md §10 Phase 2.

Spec usage:

    - key: steel_column_w
      generator: aisc
      generator_args: {family: W, series: [W8, W10, W12, W14], length: "12'-0\\""}

`generator_args`:
    family    AISC type code — W, M, S, HP, C, MC, L, WT, MT, ST, HSS, PIPE  (required)
    series    optional list of nominal-depth prefixes, e.g. [W8, W10] -> W8X31, W10X33, ...
    shape     optional 'round' | 'rect' filter, for splitting HSS
    max_depth optional inches; drop sections deeper than this
    length    sweep length for the member (default 10'-0")
    limit     optional cap, for keeping a pack small
"""
from __future__ import annotations

import csv
from pathlib import Path

from ..spec import TypeVariant

DATA = Path(__file__).resolve().parents[3] / "data" / "aisc_shapes.csv"

# profile kind -> (IFC param name, csv column) mapping, plus how to derive the bounding box
_PARAMS = {
    "IShape": [("OverallWidth", "bf"), ("OverallDepth", "d"),
               ("WebThickness", "tw"), ("FlangeThickness", "tf"), ("FilletRadius", "fillet")],
    "TShape": [("FlangeWidth", "bf"), ("Depth", "d"),
               ("WebThickness", "tw"), ("FlangeThickness", "tf"), ("FilletRadius", "fillet")],
    "UShape": [("FlangeWidth", "bf"), ("Depth", "d"),
               ("WebThickness", "tw"), ("FlangeThickness", "tf"), ("FilletRadius", "fillet")],
    "LShape": [("Width", "b"), ("Depth", "d"), ("Thickness", "t"), ("FilletRadius", "fillet")],
    "RectangleHollow": [("XDim", "B"), ("YDim", "ht"), ("WallThickness", "wall")],
    "CircleHollow": [("Radius", "radius"), ("WallThickness", "wall")],
}
_BBOX = {                      # (width column, depth column)
    "IShape": ("bf", "d"), "TShape": ("bf", "d"), "UShape": ("bf", "d"),
    "LShape": ("b", "d"), "RectangleHollow": ("B", "ht"), "CircleHollow": ("od", "od"),
}

_cache: list[dict] | None = None


def _rows() -> list[dict]:
    global _cache
    if _cache is None:
        if not DATA.exists():
            raise FileNotFoundError(
                f"{DATA} missing — run: python tools/derive_aisc.py <Shapes-US.csv>")
        _cache = list(csv.DictReader(DATA.open(encoding="utf-8")))
    return _cache


def _num(row, key):
    v = (row.get(key) or "").strip()
    return float(v) if v else None


def _series_of(label: str) -> str:
    """'W14X90' -> 'W14'; 'HSS6X6X1/2' -> 'HSS6'; 'Pipe6STD' -> 'Pipe6'."""
    return label.split("X")[0]


def generate(spec) -> list[TypeVariant]:
    args = spec.generator_args or {}
    family = args.get("family")
    if not family:
        raise ValueError(f"family {spec.key!r}: generator_args.family is required for the aisc "
                         f"generator (e.g. W, HSS, L, C, PIPE)")
    series = {s.upper() for s in (args.get("series") or [])}
    shape = (args.get("shape") or "").lower()
    max_depth = args.get("max_depth")
    length = args.get("length", "10'-0\"")
    limit = args.get("limit")

    out: list[TypeVariant] = []
    for row in _rows():
        if row["family"] != family:
            continue
        kind = row["kind"]
        if shape == "round" and kind != "CircleHollow":
            continue
        if shape == "rect" and kind != "RectangleHollow":
            continue
        if series and _series_of(row["label"]).upper() not in series:
            continue
        wcol, dcol = _BBOX[kind]
        w, d = _num(row, wcol), _num(row, dcol)
        if w is None or d is None:
            continue
        if max_depth and d > float(max_depth):
            continue

        params = {}
        for ifc_name, col in _PARAMS[kind]:
            v = _num(row, col)
            if v is not None:
                params[ifc_name] = v            # inches — units.metres treats bare numbers as inches
        if kind == "RectangleHollow" and "WallThickness" in params:
            t = params["WallThickness"]
            params["OuterFilletRadius"] = round(2 * t, 4)
            params["InnerFilletRadius"] = round(t, 4)

        out.append(TypeVariant(
            name=row["label"],
            dims=[w, d, length],
            profile={"kind": kind, "params": params, "name": row["label"]},
            psets={"MF_Structural": {"Section": row["label"], "SectionFamily": family,
                                     "SectionSource": "AISC Shapes Database v15.0 (US)"}},
        ))
        if limit and len(out) >= int(limit):
            break

    if not out:
        raise ValueError(f"family {spec.key!r}: aisc generator matched no sections for "
                         f"{args!r} — check family/series/shape filters")
    return out
