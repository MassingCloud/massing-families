# Integration with `ibuilder/massing`

## Status: the platform side is done

As of massing **v0.3.670** the integration is implemented upstream and this directory is mostly
history. What massing now has:

| | |
|---|---|
| `aec_data/family_shapes.py` | a family can be a real section, not a box (W10-2) |
| `aec_data/family_packs.py` + `POST /families/import-pack` | server-side pack shelf — import a pack already on the server by name, without download-and-re-upload |
| `GET /families/library` | now serves manifest metadata, and reports a manifest that over-promises |
| `scripts/fetch_families.py` | vendored from this directory |
| `test_family_geometry.py`, `test_family_shapes.py`, `test_family_coverage.py` | the platform's own gates |

`fetch_families.py` here remains the reference copy. `verify_geometry_support.py` replaces the old `verify_patch.py`: it checks whether the
massing you have handles this library's geometry, rather than comparing a patch against a baseline.

## The geometry patch has been withdrawn

`0001-family-geometry-fixes.patch` and `families.patched.py` were **deleted**, not superseded quietly.
massing implemented its own fix (v0.3.662) after reproducing each defect against real content, and
that implementation is strictly better. Keeping a worse patch in a public repo, presented as a
recommendation, would eventually get someone to apply it.

The patch covered defects 1, 2 and 4 below. It **caused** defect 3.

### What the four defects were

All four share one root assumption: that a type's geometry is always the box massing's own builder
makes. True while every family was a box; false the moment this library existed.

1. **Real sections read as sizeless.** `_type_dims` understood only `IfcRectangleProfileDef`, so
   403 of 403 types in the steel-W pack reported `dims: null` and nothing downstream could schedule
   or take off imported content.
2. **Resizing appended a box rather than replacing it.** The type kept its original section *and*
   gained a box drawn through it — rendered both, took off both.
3. **Hollow sections were silently reshaped as boxes.** ← *this one is the lesson*
4. **Variant names were hardcoded metric.** Names now follow the project's `IfcUnitAssignment`.

### Defect 3, the one worth remembering

`IfcRectangleHollowProfileDef` is a **subtype** of `IfcRectangleProfileDef`, so:

```python
hollow.is_a("IfcRectangleProfileDef")   # -> True
```

A resize path guarded by that test therefore matched HSS tubes, rewrote `XDim`/`YDim` while leaving
`WallThickness` untouched, and kept the catalog name. An `HSS24X12X3/4` became a 500×500 tube still
labelled `HSS24X12X3/4` — a section in no steel catalog, presented as a standard one.

A `null` is honest. That was a plausible wrong answer, which is worse, and it is exactly what the
withdrawn patch would have produced: its guard read
`it.SweptArea.is_a("IfcRectangleProfileDef") or not box_only`.

**The general lesson: in IFC, `is_a("X")` is a subtype test, not an equality test.** When behaviour
depends on the exact class — and for a *mutation* path it usually does — compare `is_a()` with no
argument instead.

This library's own code was checked and contains no such guard, but the trap generalises: two other
gaps in the withdrawn patch came from the same direction — it read only `BottomFlangeWidth` on an
asymmetric I-shape rather than the wider of the two flanges, and covered neither
`IfcTrapeziumProfileDef` nor `IfcArbitraryClosedProfileDef`.

## The coverage lesson

massing's `test_family_coverage.py` asks a question this library's own completeness test was asking
badly: *for each typology, does the shelf carry every system class needed to model one?*

It immediately found **413 families and zero `IfcFootingType`**. Every typology was unbuildable for
the same reason, and breadth everywhere else did not substitute for a building with no foundations.

This library's `tests/test_completeness.py` had a `foundations` requirement reading
`ifc_class in {"IfcFootingType", "IfcPileType"}` — an OR, satisfied by a single HP pile while zero
footings existed. **An OR over two classes only proves one of them exists.** That check has been split
into separate `footings` and `piles` requirements, and the other multi-class requirements were audited
the same way: `outlets`/`switches` and `fire alarm notification`/`fire detection` are now separate.
`cooling source` stays an OR deliberately — an air-cooled chiller needs no tower.

Foundations are now covered: 6 `IfcFootingType` families, 4 `IfcPileType`.

## Fetching packs

```bash
python scripts/fetch_families.py --list
python scripts/fetch_families.py --packs structural-steel-w mechanical-ductwork
```

massing's vendored copy is a leaner rewrite of this one and **works as-is** against the published
releases — verified fetching v0.1.5. It resolves the correct slug and needs no refresh. (An earlier
note here said it still carried a no-release fallback; that was already fixed upstream.)

No token is required: the repo is public. Releases are at
[MassingCloud/massing-families](https://github.com/MassingCloud/massing-families).

The shelf under `services/data/families/external/` was refreshed to v0.1.5 in
[ibuilder/massing#290](https://github.com/ibuilder/massing/pull/290). Its packs had been named
`v0.1.0` while holding current content — the library's `__version__` sat at `0.1.0` through five
releases and `cli build` uses it as the default, so any build not passing `--version` mislabelled
everything it produced. Fixed here in `d1f4c79`; `tests/test_version.py` now fails if `__version__`
falls behind the latest tag.

## Checking a massing checkout

```bash
python upstream/verify_geometry_support.py
MASSING_ROOT=/path/to/massing python upstream/verify_geometry_support.py
```

Against massing v0.3.718 all four behaviours pass:

```
PASS  real profile reports dims        [0.3683, 0.3556, 3.6576]
PASS  resize replaces geometry         1 RepresentationMap(s)
PASS  hollow section not falsified     IfcRectangleProfileDef named None
PASS  box resize regression            [1.6, 0.8, 0.75]
```

Check 3 reads the way it should: rather than mutating the hollow profile in place and keeping the
name, massing replaces it with a plain box carrying no catalog name. The geometry is no longer an
HSS, and it no longer claims to be one.
