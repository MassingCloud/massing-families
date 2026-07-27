# Roadmap

Where the library is and what comes next. [PLAN.md](PLAN.md) holds the research and the reasoning
behind the architecture; this is the forward view. Release history is in
[CHANGELOG.md](CHANGELOG.md).

## Where it stands

| | |
|---|---|
| Families | **419** |
| Types | **2,769** |
| Packs | 57, trade-scoped |
| IFC4 type classes | **72 of 125** |
| Geometry | 320 L200 proxies · 97 L300 real solids · 2 L350 assemblies |
| Routing | distribution ports on 97 families |
| Typologies | all six pass the completeness gate (38 core systems + per-typology) |

The platform side is finished: massing v0.3.670 carries a pack shelf, real-section support and its
own coverage gate. Integration is no longer the constraint — **depth is**.

## The honest gap

The completeness gate proves no *system* is missing. It says nothing about whether a system has enough
sizes to detail with, and that is where the remaining work lives.

Two numbers name it:

- **320 of 419 families are L200 box proxies.** Correct bounding dimensions, no detail. Legitimate for
  a chiller cabinet; not for a door leaf you intend to draw in elevation.
- **53 IFC4 type classes are still untouched**, and the long-term target is ~800 families against
  today's 419.

Nothing below is a blocker for modelling a building. It is the difference between modelling one and
documenting one.

## Next

### 1 · Depth over breadth *(the main line)*

Breadth is adequate; per-family size runs are thin. Priorities, in order of how often the absence
bites:

- **Doors and windows** — the widest matrices in any real project, currently a handful of types each
- **MEP equipment** — one or two sizes per family where a schedule needs a range
- **Fixtures and finishes** — same
- **Structural connections** — moment and shear assemblies, embeds, base plates. Needs the `assembly`
  builder, which exists but is used by only 2 families

Measure: L300 share, and types-per-family in the disciplines above.

### 2 · Promote proxies where detail earns its keep

Not every box should become a solid — a labelled proxy is a legitimate deliverable, and the
`GeometryStatus` pset says so honestly. But some are worth promoting:

- **Doors and windows** — leaf, frame, glazing, vision panel. IfcOpenShell's `add_door_representation`
  and `add_window_representation` do most of it
- **Stairs and railings** — `add_railing_representation` likewise
- **Hollowcore and precast** — real voids via `voided_profile`
- **Curtain wall** — an assembly of mullions and panels, not a single panel

### 3 · Thumbnails

The last Phase 7 item. `manifest.json` already carries the per-family index a picker needs — class,
tier, geometry status, classification, type names — but no preview. An offscreen render per family,
published alongside the packs.

### 4 · Third-party ingest

A documented, licence-gated path for content a deployment downloads under its own terms: normalise
names, stamp provenance, validate, namespace to avoid collisions. We never redistribute it; see
[NOTICE.md](NOTICE.md) for why that line matters.

### 5 · Metric market packs

Authored, **not converted**. A metric catalog uses real metric nominals — 900 × 2100 doors, HEA
sections, 16M bar — because converting imperial nominals produces sizes nobody builds. The machinery
already handles either; only the catalog is imperial. See [PLAN.md §7b](PLAN.md).

## Not planned

- **Aggregating portal content.** BIMobject, NBS Source, bimstore and the rest license content for use
  in projects, not redistribution. Fabricating from public standards is the whole premise.
- **MasterFormat codes.** Licensed by CSI. The spec field exists so a deployment can supply its own.
- **RFA output.** Revit families need Revit. Out of scope; IFC4 is the deliverable.

## How progress is measured

Every claim here is checked by a test, so the roadmap cannot quietly drift from reality:

| claim | gate |
|---|---|
| no system missing for any typology | `tests/test_completeness.py` |
| classification codes are real | `tests/test_classification.py` |
| no duplicate families or type-name collisions | `tests/test_classification.py` |
| packs stay importable and trade-scoped | `tests/test_generators.py`, `tests/test_manifest.py` |
| content survives massing's import intact | `tests/test_roundtrip_golden.py` |
| documentation matches the catalog | `tests/test_docs.py` |
| the installed massing handles our geometry | `upstream/verify_geometry_support.py` |
