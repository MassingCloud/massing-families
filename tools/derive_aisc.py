"""Derive our steel section table from the AISC Shapes Database.

Per PLAN.md §8g tier 2: we ship **derived dimensional values**, never the source file. Dimensions of
standard mill shapes are facts, not creative work; the AISC spreadsheet itself is AISC's and is not
redistributed here.

Source: https://github.com/ambaker1/aisc-csv (MIT), `v15.0/Shapes-US.csv`, which is a CSV rendering of
the AISC Shapes Database **v15.0**, US customary units.

    python tools/derive_aisc.py path/to/Shapes-US.csv

Writes `data/aisc_shapes.csv` with only the columns the profile builders need, mapping each AISC family
to its IFC profile kind:

    W, M, S, HP    -> IShape           (OverallWidth, OverallDepth, WebThickness, FlangeThickness, FilletRadius)
    C, MC          -> UShape           (Depth, FlangeWidth, WebThickness, FlangeThickness, FilletRadius)
    L              -> LShape           (Depth, Width, Thickness, FilletRadius)
    WT, MT, ST     -> TShape           (Depth, FlangeWidth, WebThickness, FlangeThickness, FilletRadius)
    HSS rectangular-> RectangleHollow  (XDim, YDim, WallThickness, Outer/InnerFilletRadius)
    HSS round, PIPE-> CircleHollow     (Radius, WallThickness)

All values are inches. `2L` (double angles) is skipped — it is an assembly of two L shapes, not a
single parameterized profile, and belongs to the `assembly` builder in a later phase.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "aisc_shapes.csv"

I_SHAPES = {"W", "M", "S", "HP"}
CHANNELS = {"C", "MC"}
TEES = {"WT", "MT", "ST"}

FIELDS = ["label", "family", "kind", "d", "bf", "tw", "tf", "fillet", "b", "t",
          "ht", "B", "wall", "od", "radius"]


def _f(row, key):
    """A numeric cell, or None. AISC uses '-' and '' for not-applicable."""
    v = (row.get(key) or "").strip().strip("–-")
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def derive(src: Path) -> list[dict]:
    rows = list(csv.DictReader(src.open(encoding="utf-8-sig")))
    out: list[dict] = []
    for r in rows:
        fam = (r.get("Type") or "").strip()
        label = (r.get("AISC_Manual_Label") or "").strip()
        if not label or fam == "2L":
            continue
        rec = {k: "" for k in FIELDS}
        rec["label"], rec["family"] = label, fam

        if fam in I_SHAPES or fam in TEES:
            d, bf, tw, tf = _f(r, "d"), _f(r, "bf"), _f(r, "tw"), _f(r, "tf")
            if None in (d, bf, tw, tf):
                continue
            kdes = _f(r, "kdes")
            # k = flange thickness + fillet radius, so the fillet is k - tf
            fillet = max(0.0, round((kdes - tf), 4)) if kdes else 0.0
            rec.update(kind="TShape" if fam in TEES else "IShape",
                       d=d, bf=bf, tw=tw, tf=tf, fillet=fillet)

        elif fam in CHANNELS:
            d, bf, tw, tf = _f(r, "d"), _f(r, "bf"), _f(r, "tw"), _f(r, "tf")
            if None in (d, bf, tw, tf):
                continue
            kdes = _f(r, "kdes")
            fillet = max(0.0, round((kdes - tf), 4)) if kdes else 0.0
            rec.update(kind="UShape", d=d, bf=bf, tw=tw, tf=tf, fillet=fillet)

        elif fam == "L":
            d, b, t = _f(r, "d"), _f(r, "b"), _f(r, "t")
            if None in (d, b, t):
                continue
            rec.update(kind="LShape", d=d, b=b, t=t, fillet=0.0)

        elif fam in {"HSS", "PIPE"}:
            od, tdes = _f(r, "OD"), _f(r, "tdes")
            ht, B = _f(r, "Ht"), _f(r, "B")
            if od and tdes:                                   # round HSS / pipe
                rec.update(kind="CircleHollow", od=od, radius=round(od / 2, 4), wall=tdes)
            elif ht and B and tdes:                           # rectangular / square HSS
                rec.update(kind="RectangleHollow", ht=ht, B=B, wall=tdes)
            else:
                continue
        else:
            continue
        out.append(rec)
    return out


def main(argv) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    src = Path(argv[1])
    if not src.exists():
        print(f"source not found: {src}", file=sys.stderr)
        return 1
    rows = derive(src)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    counts = Counter(r["family"] for r in rows)
    print(f"derived {len(rows)} shapes -> {OUT}")
    for k, v in sorted(counts.items()):
        print(f"   {k:5} {v:>4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
