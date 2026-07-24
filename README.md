# massing-families

IFC4 family/type content library for [massing](https://github.com/ibuilder/massing).

Generates versioned, discipline-scoped `.ifc` packs of data-rich `IfcTypeProduct` content that import
into any massing project through the existing `/families/import` endpoint — no platform changes needed.

**40 packs · 270 families · 2,355 types · 65 of 125 IFC4 type classes · 76% real geometry across 12 IFC solid kinds.**
All six target typologies (residential, commercial, hotel, hospital, industrial, airport) pass their
completeness checklist — see `tests/test_completeness.py` and PLAN.md §0 for what that does and does not
claim.

See [PLAN.md](PLAN.md) for the research, architecture and roadmap, and [upstream/](upstream/) for the
verified patch fixing the two massing defects that gate rich geometry.

## Quick start

```bash
python -m venv .venv && ./.venv/Scripts/python.exe -m pip install -e ".[dev]"
```

```bash
python -m massing_families.cli list
```

```bash
python -m massing_families.cli build
```

Packs land in `packs/` alongside a `manifest.json` (counts, categories, licences, sha256).

## How it works

```
catalog/**.yaml   →   spec validation   →   geometry builder   →   enrichment   →   pack
(imperial nominal)    (against IFC4)        (box / profile)        (psets, class-      (.ifc + manifest)
                                                                    ification,
                                                                    materials, qtys)
```

- **Authored imperial, stored metric.** `3'-0"` is the catalog entry; `0.9144 m` is what's written, so
  it reads as a clean `3.0 ft` / `36 in` / `914.4 mm` in any unit system. Nominal *size* can't be
  unit-converted — 0.9 m is `2'-11 7/16"`, which is not a door anyone builds. See PLAN.md §7b.
- **Validated against the real IFC4 schema.** Bad class names and illegal `PredefinedType` enums fail
  the build instead of being silently swallowed.
- **Packs are discipline-scoped, never monolithic**, because `import_types_from_ifc` imports *every*
  type in the file it is handed.

## Adding a family

Family specs are data, not code:

```yaml
- key: door_single_flush
  label: Single Flush Door
  massing_key: single_door          # maps to massing's built-in catalog entry
  ifc_class: IfcDoorType
  predefined: DOOR
  category: Doors
  discipline: architectural
  builder: box                      # or `profile` for real parametric geometry
  tier: L200
  classification: {uniclass: Pr_30_59_24, omniclass: 23-17 11 00}
  material: {name: Solid Core Wood, category: wood}
  types:
    - {name: 3'-0" x 7'-0", dims: ["3'-0\"", '1 3/4"', "7'-0\""]}
```

## Tests

```bash
python -m pytest
```

The golden round-trip test runs against a real massing checkout (`MASSING_ROOT`, default
`C:\Server\modelmaker`) and asserts that geometry, psets, provenance, materials and classification all
survive `import_types_from_ifc`. It skips cleanly if no checkout is present.

Two tests are `xfail` by design — they pin the upstream defects in PLAN.md §5 and will `xpass` when
those fixes land, which is the signal that L300 content is safe to ship broadly.

## Licence

Content is CC0-1.0 — generated parametrically, so it carries no third-party redistribution
restrictions. No content is scraped from BIM object portals; see PLAN.md §6.2 for why that matters.
