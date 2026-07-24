# Upstream patch for `ibuilder/massing`

Fixes the two defects in `services/data/src/aec_data/families.py` documented in
[PLAN.md §5](../PLAN.md), plus unit-aware type naming from [§7b](../PLAN.md).

These are **not applied to your massing checkout** — this directory holds a reviewable patch and a
verification script. Apply it yourself when you're ready.

## The defects

Both come from the same assumption: that a type's geometry is always the box
`_assign_box_representation` builds. That was true when every family was a box. It stopped being true
the moment real content existed.

**1. `_type_dims` / `_rep_solid` only match `IfcRectangleProfileDef`.**
Any real profile — a W-shape, a hollow section, a pipe — falls through and `type_detail` reports
`dims: null`. Manufacturer content imported through `/families/import` is affected too.

**2. `edit_type_params` *appends* a box instead of replacing.**
Worse than the null reading. Because `_rep_solid` returns `None` for real geometry, the resize path
takes its `else` branch and calls `_assign_box_representation`, which adds a second
`RepresentationMap`. The result renders a W-shape **and** a box on top of each other:

```
BEFORE edit: RepresentationMaps = 1  -> IfcIShapeProfileDef
AFTER  edit: RepresentationMaps = 2  -> IfcIShapeProfileDef
                                     -> IfcRectangleProfileDef
```

**3. `_variant_name` hardcodes metric.** A 3'-0" × 7'-0" door in an imperial project is named
`Single door 0.9144×0.0508×2.1336 m`. Naming is the only place massing is genuinely metric-bound —
geometry already converts correctly via `IfcUnitAssignment`.

## What the patch does

| | |
|---|---|
| `_rep_solid(typ, box_only=True)` | gains a flag. Default keeps the strict box match for the *edit* path, which can only resize a rectangle. `box_only=False` finds any extruded solid, for reading. |
| `_PROFILE_BOUNDS` + `_profile_bounds()` | new: bounding width/depth for 13 parameterized profile types, so `_type_dims` can read real geometry. |
| `_clear_representation_maps()` | new: drops existing maps so a new representation *replaces* rather than adds. |
| `edit_type_params` | clears before assigning when no editable box exists. |
| `_variant_name(label, dims, model=None)` | formats per the model's `IfcUnitAssignment` — feet-and-inches in an imperial project, mm in a millimetre project, metres otherwise. |

The in-place box resize path — the GUID-stable propagation that makes type edits work — is untouched.

## Verify

```bash
python upstream/verify_patch.py
```

Runs both defect scenarios plus a regression check against the unpatched and patched modules:

```
=== UNPATCHED (current massing) ===
  type_detail dims for W14X90 : None   -> NULL (defect 1)
  RepresentationMaps 1 -> 2 ['IfcIShapeProfileDef', 'IfcRectangleProfileDef']   -> DUPLICATE GEOMETRY
  box resize still works      : [1.6, 0.8, 0.75]   -> OK

=== PATCHED ===
  type_detail dims for W14X90 : [0.3683, 0.3556, 3.6576]   -> OK
  RepresentationMaps 1 -> 1 ['IfcRectangleProfileDef']   -> OK
  box resize still works      : [1.6, 0.8, 0.75]   -> OK
```

## Apply

```bash
git -C /path/to/massing apply /path/to/massing_families/upstream/0001-family-geometry-fixes.patch
```

`families.patched.py` is the full patched file if you'd rather diff or copy it directly.

## After it lands

The two `xfail` markers in `tests/test_roundtrip_golden.py` flip to `xpass` — that is the signal that
L300 content is safe to ship broadly. Remove the markers at that point.
