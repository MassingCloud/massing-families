# Using the library

For people placing this content in a model. If you are adding families, see
[CONTRIBUTING.md](../CONTRIBUTING.md); for the spec fields, [SPEC.md](SPEC.md).

## Getting packs

```bash
python upstream/fetch_families.py --list
```

Lists every pack in the latest release with its family and type counts. Then take what you need:

```bash
python upstream/fetch_families.py --packs structural-steel-w mechanical-ductwork
```

Public repo, no token, no account. Each pack is checked against the sha256 in `manifest.json` before
it is written.

### Take packs, not the library

The whole library is 2,769 types. **massing's import pulls in every type in the file it is given**, so
importing everything means a project full of content nobody asked for — 403 W-shapes in a residential
job, 516 HSS sizes in a fit-out.

Packs are trade-scoped for exactly this reason. Pull `structural-steel-w` when you are framing in
steel; leave `typology-airport` alone unless you are building a terminal.

## Getting them into massing

Two routes, depending on where the pack already is:

| situation | route |
|---|---|
| pack sits on the server's shelf (`services/data/families/external/`) | `POST /families/import-pack` — resolves by name, no upload |
| you have a pack locally | `POST /projects/{id}/families/import` — multipart upload |

`GET /families/library` lists what is on the shelf, with manifest metadata.

Imported types are placeable through the normal flow — `GET /projects/{id}/types` to find them, then
place by GUID. Nothing about them is special; they are ordinary `IfcTypeProduct` entities.

## What you get on every type

Content is data-rich by design. Each type carries:

**`MF_Library`** — provenance. `Key`, `Family`, `TypeName`, `Version`, `License`, `Source`, `Tier`,
`Builder`, `Discipline`, `GeometryStatus`, and `MassingKey` where the family maps to a massing
built-in.

**`MF_Quantities`** — `NominalWidth`, `NominalDepth`, `NominalHeight`, `NominalFootprintArea`,
`NominalVolume`. Deliberately labelled *Nominal*: they are the type's bounding box, not a tessellated
volume. Good enough to schedule and sanity-check; not a substitute for a real takeoff on detailed
geometry.

**Standard IFC psets** where one fits — `Pset_DoorCommon`, `Pset_WallCommon`, `Pset_ColumnCommon` and
so on, so downstream tools that read the schema find what they expect.

**Classification** — a Uniclass `IfcClassificationReference`, every code checked against the published
Pr/Ss tables. Filter or schedule by it.

**Materials** — a single `IfcMaterial`, or an ordered `IfcMaterialLayerSet` for assemblies. A 4⅞"
partition really is ⅝" gypsum + 3⅝" stud + ⅝" gypsum, so thermal and takeoff reads are meaningful.

**Ports** on routing content — `IfcDistributionPort` with flow direction, attached via `IfcRelNests`.
97 families carry them: duct, pipe, conduit, tray, sprinkler, plant.

## Reading `GeometryStatus` before you draw

This is the field to check before committing to a detail.

| value | what it means |
|---|---|
| `proxy` | a box with correct bounding dimensions and no detail |
| `parametric` | a real swept solid — I-shape, hollow section, circle, revolve |
| `assembly` | multi-part, parts are real elements |
| `tessellated` | faceted mesh |

A `proxy` is honest, useful content — right for a chiller cabinet, a jobsite trailer, an MRI envelope.
It coordinates, clashes and schedules correctly. It is *not* what you want in a wall section at 1½"
scale. The field is derived from the builder, never hand-set, so it cannot overstate.

## Units

Everything is authored in US imperial nominals and stored in exact metres. A 3'-0" door is
`0.9144 m` — so it reads as **3.0 ft**, **36 in** or **914.4 mm** depending on your project's units,
with no rounding drift.

Type *names* carry the imperial designation, because that is what appears on a schedule:
`Single Flush Door - 3'-0" x 7'-0"`, `W-Shape Column - W14X90`.

Where nominal differs from actual, the name is nominal and the geometry is actual — a `2x4` is built
1½" × 3½".

## Choosing between similar families

Some overlaps are real products, not duplicates:

- **HSS round vs Pipe** — both round tubes at overlapping sizes, different mill standards (A500 vs
  A53) and different catalog names. Pick by what the structural drawings call out.
- **EMT vs RMC vs PVC conduit** — same trade sizes, different wall thicknesses and materials.
- **`sink` vs `sink_service`** — a stainless kitchen sink at 2 DFU is not a molded-stone mop sink at
  3 DFU.

The catalog reference lists every family with its class, tier and classification:
[CATALOG.md](CATALOG.md).

## Verifying a massing checkout

If imported content reads as sizeless, or resizing a section leaves a box drawn through it, the
massing you are on predates the v0.3.662 geometry fixes:

```bash
python upstream/verify_geometry_support.py
```

Four behaviours, each a defect found against real content. See
[upstream/README.md](../upstream/README.md).

## Licence

Content is CC0-1.0 — public domain, no attribution required, commercial use fine. The declaration
travels in three places so it survives being separated from this repo: `MF_Library.License` on every
type, the pack's STEP header, and the top level of `manifest.json`.

Derived reference data (AISC section dimensions, Uniclass codes) has its own provenance —
[NOTICE.md](../NOTICE.md).

> **On engineering use:** dimensions drive geometry. They are transcribed from published standards and
> checked, but this is a modelling library, not a design authority. Verify against a current source
> before relying on a section for design.
