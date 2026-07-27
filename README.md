# massing-families

**An openBIM family library you can actually redistribute.**

419 families · 2,769 types · 57 discipline packs · IFC4 · CC0

Generated parametrically from public standards — AISC section tables, ASME nominal pipe sizes, ASTM
bar diameters, IBC and ADA dimensional requirements — so it carries no third-party redistribution
restriction. Built for [massing](https://github.com/ibuilder/massing), but the output is plain IFC4
and imports anywhere.

[Catalog reference](docs/CATALOG.md) · [Adding a family](CONTRIBUTING.md) ·
[Spec reference](docs/SPEC.md) · [Design notes](PLAN.md) · [Releases](../../releases)

---

## Why this exists

Every major BIM object portal — BIMobject, NBS Source, bimstore, BIM&CO, Modlar — licenses content
for free use *in your projects*, not for redistribution. That makes them unusable as a shipped
catalog. It is a licensing problem, not a technical one, and the way through it is to **fabricate the
content rather than aggregate it**.

Dimensions of standard manufactured articles are facts, not creative works. A W14×90 is 14.5" wide
because AISC says so; a 3'-0" door is 3'-0". Generating from those tables produces content that is
both correct and free.

## Use it

Download a release — no token, no account:

```bash
python upstream/fetch_families.py --list
```

```bash
python upstream/fetch_families.py --packs structural-steel-w mechanical-ductwork
```

Each release attaches one `.ifc` per pack plus a `manifest.json` carrying a sha256 for every pack,
which the fetch script verifies before writing. Packs are trade-scoped on purpose: massing's import
pulls in *every* type in a file, so a single 2,769-type library would flood a project.

For a massing deployment, vendor `upstream/fetch_families.py` as `scripts/fetch_families.py`; it
writes into `services/data/families/external/`, where `GET /families/library` already looks. See
[upstream/README.md](upstream/README.md).

## Build it

```bash
python -m venv .venv && ./.venv/bin/pip install -e ".[dev]"
```

```bash
python -m massing_families.cli list
python -m massing_families.cli build
python -m massing_families.cli docs
```

## How it works

```
catalog/**.yaml   →   validation    →   builder      →   enrichment      →   pack
imperial nominal      against IFC4      8 geometry       psets, Uniclass,     .ifc + manifest
                      schema            builders         materials, ports,
                                                         quantities
```

Family specs are data, not code — adding one is a YAML edit:

```yaml
- key: door_single_flush
  label: Single Flush Door
  massing_key: single_door          # maps to massing's built-in catalog
  ifc_class: IfcDoorType
  predefined: DOOR
  category: Doors
  discipline: architectural
  builder: box
  tier: L200
  classification: {uniclass: Pr_30_59_24}
  material: {name: Solid Core Wood, category: wood}
  types:
    - {name: 3'-0" x 7'-0", dims: ["3'-0\"", '1 3/4"', "7'-0\""]}
```

Three generators expand a single spec into a whole size run: `aisc` (every mill section from the
Shapes Database), `sizes` (nominal trade sizes for duct, pipe, conduit, tray) and `rebar`.

## Design decisions worth knowing

**Authored imperial, stored metric.** `3'-0"` in the YAML becomes exactly `0.9144 m` in the IFC. This
is not a formatting preference — nominal *size* cannot be unit-converted. Rounded metric nominals
convert to unbuildable US sizes (0.9 m is 2'-11 7/16", which is not a door anyone makes), and
designations like W14×90 or a #5 bar have no metric equivalent at all. Storing the exact conversion
gives clean numbers in every unit system: 3.0 ft / 36 in / 914.4 mm. See [PLAN.md §7b](PLAN.md).

**Nominal is not actual.** A 2x4 is named `2x4` and built 1½" × 3½".

**Classification is verified, never guessed.** `data/uniclass_codes.csv` holds only codes checked
against the published Uniclass Pr/Ss tables, and a test fails the build on anything else. This has
caught seven wrong codes — `Pr_20_93_71`, which reads plausibly for steel columns, is actually
*Retaining wall units*.

**Validated against the real IFC4 schema.** Bad class names and illegal `PredefinedType` enums fail
the build rather than being silently swallowed. Nine invalid enums have been caught this way.

**Proxies are labelled.** A dimensionally-correct box is a legitimate deliverable when detailed
geometry isn't warranted, but every type declares `MF_Library.GeometryStatus`, derived from its
builder, so a proxy can never be mistaken for detailed content.

## Coverage

Six building typologies — residential, commercial, hotel, hospital, industrial, airport — each pass a
completeness checklist asserting at least one family exists for every system that typology cannot be
built without (`tests/test_completeness.py`). That is a floor, not a depth claim: 419 families against
a longer-term target of ~800. The gap is breadth within systems, not absent systems.

See [docs/CATALOG.md](docs/CATALOG.md) for the full inventory.

## Tests

```bash
pytest
```

The golden round-trip runs against a real massing checkout (`MASSING_ROOT`, default
`C:\Server\modelmaker`) and asserts geometry, psets, provenance, materials, classification and
distribution ports all survive `import_types_from_ifc`. It skips cleanly without one; CI clones
massing so every PR verifies against the real platform.

## Licence

| | |
|---|---|
| `catalog/` and generated packs | **CC0-1.0** — [LICENSE-CONTENT](LICENSE-CONTENT) |
| `src/`, `tools/`, `tests/` | **MIT** — [LICENSE](LICENSE) |
| `data/` | derived reference data — [NOTICE.md](NOTICE.md) |
| `upstream/` | derivative of [ibuilder/massing](https://github.com/ibuilder/massing); follows that project's terms |

The declaration travels with the content, in three places, so it survives being separated from this
repository:

- every type carries `MF_Library.License`, so it follows the object into any model that imports it
- every pack's STEP header records it — `FILE_NAME` authorization and `FILE_DESCRIPTION`
- `manifest.json` declares it at the top level, which is what a catalog shelf reads

Contributions are accepted under the same terms — see [CONTRIBUTING.md](CONTRIBUTING.md).
