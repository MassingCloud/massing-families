# Family spec reference

Every file under `catalog/` is a YAML list of family specs. Each spec produces one family and one or
more catalogued **types** — the Revit "one family, many types" model, which is also how massing's own
`TYPE_CATALOGS` works.

Validation runs against the real IFC4 schema via IfcOpenShell, so an unknown class or an illegal
`PredefinedType` fails the build rather than being silently dropped.

## Identity

| field | required | notes |
|---|---|---|
| `key` | ✔ | unique across the whole catalog; snake_case |
| `label` | ✔ | human name; combined with each type's name to form the IFC type name |
| `ifc_class` | ✔ | must be an IFC4 `IfcTypeProduct` subclass — 125 exist |
| `predefined` | | must be legal for that class; the validator lists valid values on error |
| `category` | ✔ | picker grouping, e.g. `Doors`, `Central Plant` |
| `discipline` | ✔ | top-level grouping and default pack name |
| `pack` | | overrides the release asset this family lands in |
| `massing_key` | | the equivalent key in massing's built-in `CATALOG`, so a pack can replace it upstream |

The IFC type name is `"{label} - {type name}"` — for example `Single Flush Door - 3'-0" x 7'-0"`.
That string is massing's dedup identity, so it must be unique across families.

## Geometry

| field | notes |
|---|---|
| `builder` | `box`, `profile`, `revolve`, `swept_disk`, `boolean`, `taper`, `assembly`, `mesh` |
| `tier` | `L200` proxy, `L300` real parametric solid, `L350` multi-part assembly |
| `dims` | default `[width, depth, height]` in imperial nominals |
| `profile` | `{kind, params, depth}` for profile-swept geometry |

`box` falls back automatically if a richer builder yields nothing, so a family never ends up with no
geometry at all.

### Profile kinds

`Rectangle`, `RectangleHollow`, `RoundedRectangle`, `Circle`, `CircleHollow`, `Ellipse`, `IShape`,
`AsymmetricIShape`, `LShape`, `TShape`, `UShape`, `CShape`, `ZShape`, `Trapezium`.

`params` are the IFC entity's own attribute names — `OverallWidth`, `WebThickness`, `Radius`,
`WallThickness`. The builder reads the schema to decide which are lengths (scaled into file units) and
which are not (`FlangeSlope` and `LegSlope` are plane angles and pass through untouched), so adding a
profile kind needs no scaling table.

```yaml
builder: profile
tier: L300
profile: {kind: IShape}
types:
  - name: W14X90
    dims: ['14.5"', '14.0"', "12'-0\""]
    profile: {params: {OverallWidth: '14.5"', OverallDepth: '14.0"',
                       WebThickness: '0.440"', FlangeThickness: '0.710"'}}
```

## Types

`types` is a list of `{name, dims, profile?, psets?}`. Omit it and the family builds one `Standard`
type from the spec-level `dims`.

```yaml
types:
  - {name: 3'-0" x 7'-0", dims: ["3'-0\"", '1 3/4"', "7'-0\""]}
```

Type names must not contain a comma inside YAML flow mapping — `{name: A, B, dims: ...}` parses `B`
as a key. Use a slash, or block syntax.

## Generators

`generator` + `generator_args` expand one spec into a whole size run.

### `aisc`

Reads `data/aisc_shapes.csv` (derived from the AISC Shapes Database — see `NOTICE.md`).

| arg | notes |
|---|---|
| `family` | `W`, `M`, `S`, `HP`, `C`, `MC`, `L`, `WT`, `MT`, `ST`, `HSS`, `PIPE` |
| `series` | nominal-depth prefixes, e.g. `[W8, W10]` |
| `shape` | `round` or `rect`, for splitting HSS |
| `max_depth` | inches |
| `length` | sweep length (default `10'-0"`) |
| `limit` | cap, for keeping a pack small |

### `sizes`

| arg | notes |
|---|---|
| `kind` | `Circle`, `CircleHollow`, `Rectangle`, `RectangleHollow` |
| `entries` | round: `[{nominal, od, wall?}, …]` |
| `sections` | rectangular: `[[width, height], …]` |
| `wall` | one thickness for all entries, or per entry |
| `name` | template, e.g. `'{nominal}" Copper L'` |
| `length` | sweep length |

### `rebar`

Bar sizes and bend shapes.

## Data

| field | notes |
|---|---|
| `classification` | `{uniclass: Pr_…}` — must exist in `data/uniclass_codes.csv`; `omniclass` and `masterformat` also accepted |
| `material` | `{name, category}` for a single material, or `{name, layers: [{material, thickness, category}]}` for a layered assembly |
| `psets` | `{PsetName: {prop: value}}` — use standard `Pset_*` names where one fits |
| `ports` | `{system, names?, flows?}` — `DUCT`, `PIPE`, `CABLE`, `CABLECARRIER` |
| `license` | SPDX id, default `CC0-1.0`. Only change it if the family vendors third-party geometry — record the source in `NOTICE.md`. A non-CC0 family makes the pack's manifest report `MIXED` rather than overstating how freely it can be redistributed. |
| `source` | provenance, default `massing-families` |

Layer thicknesses are imperial too — a `4 7/8"` partition is `5/8"` gypsum + `3 5/8"` stud + `5/8"`
gypsum.

Ports attach to the type via `IfcRelNests` and survive massing's import with `FlowDirection` intact —
verified, and pinned by `test_distribution_ports_survive`.

## Emitted automatically

Every type gets these without being asked:

- **`MF_Library`** — key, family, type name, version, licence, source, tier, builder, discipline,
  `GeometryStatus`, and `MassingKey` when mapped
- **`MF_Quantities`** — nominal width, depth, height, footprint area, volume. Labelled *Nominal*
  because they are the type's bounding box, not a tessellated volume
- **`IfcClassificationReference`** for each declared code
- **material association**, single or layered

`GeometryStatus` is derived from the builder — `box` → `proxy`, the parametric builders →
`parametric`, `assembly` → `assembly`, `mesh` → `tessellated`. It is never hand-set, so it cannot
drift out of date.

The licence is stamped in three places so it survives the file being moved: `MF_Library.License` on
every type, the pack's STEP header (`FILE_NAME` authorization and `FILE_DESCRIPTION`), and the
top-level `license` key in `manifest.json`.

## Units

Accepted dimension forms: `3'-0"`, `3'-6 1/2"`, `7'`, `36"`, `1 1/2"`, `5/8"`, `8.00"`, `0.285"`, and
bare numbers (treated as inches).

Stored in exact metres. The inch has been exactly 25.4 mm since 1959, so `3'-0"` → `0.9144 m` is
lossless and reads back as 3.0 ft / 36 in / 914.4 mm depending on the consuming model's units. See
[PLAN.md §7b](../PLAN.md) for why nominal size cannot simply be unit-converted.
