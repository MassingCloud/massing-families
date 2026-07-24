# Massing Family Library — Research & Development Plan

**Target platform:** [ibuilder/massing](https://github.com/ibuilder/massing) (local checkout: `C:\Server\modelmaker`, v0.3.653)
**This repo:** `C:\Server\massing_families` — the content library that ships as massing's offering catalog
**Date:** 2026-07-24

---

## 0. Status

| | |
|---|---|
| **Built** | 40 trade-scoped packs · **270 families** · **2,334 types** · IFC4 · 6.1 MB |
| **Tests** | 104 passing, 2 xfailed (the upstream defects — patch now written, see `upstream/`) |
| **IFC coverage** | **65 of 125** type classes (was 15) |
| **Builders** | all 8 — box, profile, swept_disk, revolve, boolean, taper, assembly, mesh |
| **Geometry** | **1,797 of 2,334 types (76%) real**, across 12 distinct IFC solid/profile kinds |
| **Routing** | `IfcDistributionPort`s on 59 families — duct, pipe, conduit, tray, sprinkler, plant |
| **Data** | 122 verified Uniclass codes, provenance with derived `GeometryStatus`, quantities, materials, layered assemblies |
| **Catalog index** | per-family metadata published in `manifest.json` — the data a browsable picker needs |
| **Typologies** | all six pass: core 35/35, residential 7/7, commercial 6/6, hotel 4/4, hospital 6/6, industrial 5/5, airport 5/5 |

### Upstream patch — written and verified, not applied

`upstream/` holds a reviewable patch for the two section 5 defects plus unit-aware type naming.
`upstream/verify_patch.py` runs both defect scenarios against the unpatched and patched modules:

```
UNPATCHED  type_detail dims for W14X90 : None                  -> defect 1
           RepresentationMaps 1 -> 2 [IShape, Rectangle]       -> defect 2
PATCHED    type_detail dims for W14X90 : [0.3683, 0.3556, 3.6576]   OK
           RepresentationMaps 1 -> 1 [Rectangle]                     OK
           box resize still works      : [1.6, 0.8, 0.75]            OK (no regression)
```

It is deliberately **not applied** to the massing checkout — that is your call.

### What "all six typologies pass" does and does not mean

`tests/test_completeness.py` asserts at least one family exists for every system a typology cannot be
built without — now 35 core systems (heat source, cooling source, pumps, terminal units, roof drainage
and reinforcement were added once the content landed) plus per-typology extras.

It remains a **floor, not v1.0 depth**. The section 8e target is ~800 families / ~7,500 types; this is
270 / 2,334. The gap is breadth-within-system, not absent systems.

### Enforced honesty

- **Classification** — a test fails the build on any code not in `data/uniclass_codes.csv`, which holds
  only codes checked against the published Uniclass Pr/Ss tables. This has caught **seven** wrong codes
  across four phases, including `Pr_20_29_29` for rebar (actually *Ferrules and sleeves*; correct is
  `Pr_20_96_71`) and `Pr_20_93_71` for steel columns (actually *Retaining wall units*).
- **PredefinedType** — schema-driven validation has caught nine invalid enums that massing's own
  `_set_predefined` would have silently swallowed.
- **GeometryStatus** — derived from the builder, never hand-set, so a box proxy is always labelled
  `proxy` and can never be mistaken for detailed content.
- **Nominal vs actual** — timber names `2x4` and builds 1 1/2" x 3 1/2"; the same discipline as the
  imperial/metric split in section 7b.

### Backlog

- Steel moment/shear connection assemblies and embeds
- Hollowcore with real voids (`voided_profile`, currently folded into `profile`)
- Curtain wall / storefront as assemblies rather than single panels
- Thumbnails (the one Phase 7 item still missing — the manifest index is done)
- License-gated third-party ingest pipeline
- More sizes per family across MEP equipment, fixtures and finishes

## 1. Executive summary

Massing already has a working *family system* — a type/instance spine, parametric variants, composites,
material sets, and an import path for external content. What it does not have is **content**. The catalog
is 46 families, and **every one of them is a box**.

The right move is therefore not to build a new subsystem but to build a **content pipeline** that feeds the
one that already exists. The integration contract is narrow and verified: massing ingests an **IFC4 file
containing named `IfcTypeProduct` entities with mapped representations**. Everything else — psets,
materials, classification, real swept geometry — rides along intact (verified empirically in §4).

That means the library can be developed as an **independent, versioned content repo** that emits IFC packs,
with near-zero coupling to massing's release cycle. Two upstream bug fixes are required first (§5).

**Recommended shape of the deliverable:** declarative family specs (YAML) + parametric Python builders on
IfcOpenShell → versioned, per-discipline `.ifc` packs + a `manifest.json`. Generated, not hand-modeled, so
it is diffable, license-clean, reproducible, and fully offline.

---

## 2. What massing does today (verified against source)

| Fact | Value |
|---|---|
| Families in catalog | **46** |
| Distinct IFC type classes used | **15** of 125 available in IFC4 |
| Categories | Furniture 11, Sanitary 6, Appliance 6, MEP 5, Openings 4, Structural 4, Enclosure 3, Lighting 3, Plant 3, Transport 1 |
| Named type catalogs | 8 families, 21 curated sizes |
| Composites (nested assemblies) | 3 |
| Geometry representations in use | **1** (`IfcRectangleProfileDef`) of 23 profile types |
| Families with real geometry | **0** |
| Committed `.ifc` content in repo | **0 bytes** (`families/` holds only `.gitkeep`) |

Core source files:

- `services/data/src/aec_data/families.py` — the catalog + type machinery (532 lines)
- `services/data/src/aec_data/build_family_library.py` — writes `services/data/families/library.ifc`
- `services/api/src/aec_api/routers/authoring.py:354-460` — the five family endpoints

### Existing capability worth building on

The type system is genuinely good and should not be reinvented:

- `ensure_type()` — find-or-build, deduped by `(ifc_class, Name)`
- `create_type()` — author any `IfcXxxType` with dims, PredefinedType, psets; idempotent
- `edit_type_params()` — mutates the type's solid **in place**, so a size change propagates to every
  placed occurrence at once, GUID-stably. This is the real Revit-parity feature.
- `assign_material_set()` — `IfcMaterialLayerSet` inherited by occurrences
- `type_detail()` — inspector: class, dims, psets, materials, occurrence list
- `import_types_from_ifc()` — appends every `IfcTypeProduct` from an external IFC via
  `project.append_asset`, deduped by `(class, name)`
- `TYPE_CATALOGS` / `COMPOSITES` — named sizes and nested assemblies

---

## 3. The integration contract (this constrains everything)

There are exactly **two** ways content enters the platform:

**A. Drop-in directory** — `services/data/families/external/*.ifc`
Listed by `GET /families/library` (returns filename + size only). This is the slot a shipped
library occupies.

**B. Upload endpoint** — `POST /projects/{pid}/families/import`
Reads the uploaded IFC, calls `import_types_from_ifc`, writes a new source-IFC version, audits it,
optionally republishes fragments.

**Consequence:** the deliverable format is **IFC4, containing `IfcTypeProduct` entities**. Not glTF, not
OBJ, not RFA. Anything else requires new platform code.

**Consequence:** `import_types_from_ifc` imports *every* type in the file. A monolithic 5,000-type library
would flood a project with unwanted types. **Packs must be granular and discipline-scoped** — this is a
hard design constraint, not a preference.

---

## 4. Verified: rich data survives the import path

Before planning around it, I tested the assumption end-to-end (build a rich type in a source file →
`import_types_from_ifc` → inspect the target).

**Test 1 — data richness.** A door type carrying `Pset_DoorCommon` + a custom `MF_Library` pset, an
`IfcMaterialLayerSet`, and a Uniclass `IfcClassificationReference`:

```
PSETS SURVIVED:      {'Pset_DoorCommon': {'FireRating': '60', 'IsExternal': True},
                      'MF_Library': {'Source': 'ACME', 'License': 'CC0'}}
MATERIAL SURVIVED:   IfcMaterialLayerSet(('Oak'), 'ACME Door 900x2100 assembly')
CLASSIFICATION:      [('Pr_30_59_24', 'Doorsets')]
HasAssociations:     ['IfcRelAssociatesClassification', 'IfcRelAssociatesMaterial']
GEOMETRY:            True
```

**Test 2 — real (non-box) geometry.** A true W14×90 `IfcIShapeProfileDef` swept 3.5 m:

```
SWEPT AREA CLASS:    IfcIShapeProfileDef  | ProfileName: W14X90
I-shape params:      0.3683  0.356  0.011   (preserved exactly)
```

**Conclusion: the data-rich, real-geometry strategy works with zero changes to massing's ingest code.**
This is the finding the whole plan rests on.

---

## 5. Verified blockers — two upstream fixes required first

Test 2 also surfaced a defect. Massing's type introspection assumes the box representation:

```
_type_dims(real_I_beam)   -> None      # type_detail reports dims: null
_rep_solid(real_I_beam)   -> None      # the in-place edit path can't find the solid
```

Both functions (`families.py:210-233`) match only `IfcExtrudedAreaSolid` whose `SweptArea` is an
`IfcRectangleProfileDef`. Any real profile falls through.

**The consequence is worse than a null reading.** Because `_rep_solid` returns `None`,
`edit_type_params(dims=...)` takes its `else` branch and *adds a box representation alongside* the real
geometry. Confirmed:

```
BEFORE edit: RepresentationMaps = 1  -> IfcIShapeProfileDef
AFTER  edit: RepresentationMaps = 2  -> IfcIShapeProfileDef
                                     -> IfcRectangleProfileDef   # duplicate, overlapping solid
```

A user who edits the size of a rich family gets a W-shape **and** a box rendered on top of each other.

**Required upstream PRs (Phase 0):**

1. **`_rep_solid` / `_type_dims` — handle parameterized profiles.** Read bounding dims from
   `IfcIShapeProfileDef`, `IfcCircleProfileDef`, `IfcRectangleHollowProfileDef`, etc., not just rectangles.
2. **`edit_type_params` — replace, never append.** Clear existing `RepresentationMaps` before assigning a
   new representation, and prefer editing the native profile's own parameters where the profile type
   supports it.
3. *(recommended)* **Namespaced dedup.** `(ifc_class, Name)` collides across vendors. Add a
   `MF_Library.Key` pset field as the identity, or mandate a `Vendor · Family - Type` naming convention.

These are small, well-scoped changes and should land upstream **before** any rich content ships.

---

## 6. Landscape research — what exists, and what we can legally use

### 6.1 Existing libraries

| Source | Content | IFC? | Usable as shipped catalog? |
|---|---|---|---|
| [BIMobject](https://www.bimobject.com/en) | 2,000+ manufacturers | Some | **No** — per-download terms, Revit-first |
| [NBS Source / National BIM Library](https://source.thenbs.com/en/gb/bimlibrary) | Generic + proprietary, UK | **Yes** | **No** — "free to use in projects" ≠ redistributable |
| [bimstore](https://www.bimstore.co/) | Manufacturer-approved | Some | **No** |
| [BIM&CO](https://www.bimandco.com/en/bim-objects) | Generic + manufacturer | Yes | **No** |
| [Modlar](https://www.modlar.com/search/format/ifc/) | Brand + generic | Yes | **No** |
| MEPcontent | MEP-heavy, IFC-filterable | Yes | **No** |
| [FreeCAD BIM](https://freecad-app.com/workbenches/bim/) | Small parametric door/window set + BIM Components addon | Yes | **Partially** — open source, check per-asset licence |
| SketchUp 3D Warehouse | Huge | No | **No** — not redistributable, no BIM data |

### 6.2 The licensing finding (most important research result)

**Every major BIM object portal licenses content as "free to download and use *in your projects*." None of
them grant redistribution rights.** Bundling their content into massing's shipped catalog would be
infringement. This is why "there is no great free openBIM library" — it is a licensing problem, not a
technical one.

**Therefore: generate our own content.** This is also what massing already concluded — `families.py`'s own
docstring says *"openBIM has no single great free family library and manufacturer content is Revit-first,
so we generate a small curated catalog parametrically."* The plan extends that decision rather than
reversing it.

Third-party content is supported through the **user-supplied ingest path** (§10, Phase 7): the user
downloads content under their own licence and imports it. We never redistribute it.

### 6.3 Open inputs we *can* use

- **AISC Shapes Database v16.0** — free Excel download from AISC; 222 new shapes in the 16th edition.
  Dimensional data drives real `IfcIShapeProfileDef` / `IfcRectangleHollowProfileDef` geometry.
  *Action: verify redistribution terms of the data file itself; deriving dimensions is low-risk, shipping
  their spreadsheet is not.*
- **buildingSMART Data Dictionary (bSDD)** — REST/GraphQL API for classifications, properties, units.
  IfcOpenShell ships bSDD support. *Note: per-dictionary licences vary (IFC's own is CC BY-ND 4.0), so
  check each before embedding.*
- **IFC4 / IFC4.3 standard property sets** — `Pset_DoorCommon`, `Pset_WallCommon` etc. are part of the
  published schema and are the correct data backbone.
- **Uniclass** (NBS, free download) and **OmniClass Table 23** (CSI, free) for classification.
  **MasterFormat is licensed** — support it as a user-supplied mapping, do not embed.
- Steel/timber/concrete dimensional standards are facts, not creative works — safe to derive from.

---

## 7. Strategy

1. **Generate, don't collect.** Parametric builders in Python/IfcOpenShell. Fully offline, reproducible,
   license-clean, diffable in git.
2. **Declarative source of truth.** Family specs in YAML; geometry archetype declared per family. Adding a
   family is a data edit, not a code change.
3. **Tiered geometry (LOD).** Box proxy always available as fallback; real parametric solids where they
   matter. Never regress the existing behaviour.
4. **Data richness is the differentiator.** SketchUp gives you a pretty box with no data. Our value is
   IFC-native psets + classification + materials + quantities on every object.
5. **Granular packs.** Discipline-scoped `.ifc` files, because import pulls in everything in the file.
6. **Independent release cadence.** Content ships on its own version line; only Phase 0 touches massing.

### Geometry tiers

| Tier | Meaning | Representation |
|---|---|---|
| **L200** | Sized box proxy — today's behaviour | `IfcRectangleProfileDef` extrusion |
| **L300** | Real parametric solid | Profile sweeps (I/C/L/T/Z/circle/hollow), revolutions, booleans |
| **L350** | Multi-part with connections/ports | `IfcElementAssembly`, `IfcDistributionPort` |

Every family declares a tier; L200 remains the fallback so nothing breaks.

---

## 7b. Units decision — imperial catalog, exact metric storage *(settled)*

**Unit conversion is already solved and is not the problem.** IFC stores an `IfcUnitAssignment` and every
length is scaled on read/write; massing calls `calculate_unit_scale` in ~50 places. Verified — the same
metric-authored family lands dimensionally correct in any unit system:

```
METERS        stored XDim=0.9        -> 0.9000 m
MILLIMETERS   stored XDim=900        -> 0.9000 m
FEET          stored XDim=2.95276    -> 0.9000 m
INCHES        stored XDim=35.4331    -> 0.9000 m
```

(Note: `grid.py` is **column gridlines** — `IfcGrid` axes A/B/C × 1/2/3 for snapping placement. It has
nothing to do with units. Unit conversion comes from `IfcUnitAssignment`, automatically.)

**What cannot be converted is nominal size — which types exist.** Today's catalog uses *rounded metric*
nominals, which convert into unbuildable US sizes:

| Family | Metric | Converts to | US standard |
|---|---|---|---|
| single_door | 0.9 × 2.1 | 2'-11 7/16" × 6'-10 11/16" | **3'-0" × 7'-0"** |
| double_door | 1.8 × 2.1 | 5'-10 7/8" × 6'-10 11/16" | **6'-0" × 7'-0"** |
| fixed_window | 1.2 × 1.5 | 3'-11 1/4" × 4'-11 1/16" | **4'-0" × 5'-0"** |
| partition_wall | 0.12 thick | 4 3/4" | **4 7/8"** (3⅝" stud + gyp) |

Dimensionally correct, professionally useless — no US door schedule reads 2'-11 7/16".

Designations are worse, because they aren't dimensions at all: **W14×90** has no metric conversion (the
metric analogue W360×134 is a different shape from a different mill standard). Same for rebar (#5 ≠ 16M),
and US lumber where a "2×4" is actually 1½" × 3½".

**Resolution: the tension is not metric-vs-imperial, it's *rounded* metric vs *exact* imperial-derived.**
The inch has been exactly 25.4 mm since 1959, so conversion is lossless in both directions. Author the
catalog from **imperial nominals**, store the **exact metric equivalent**. Verified:

```
3'-0" x 7'-0"  ->  exact metres [0.9144, 0.0508, 2.1336]
  FEET         stored XDim=3        depth=7
  INCHES       stored XDim=36       depth=84
  MILLIMETERS  stored XDim=914.4    depth=2133.6
```

Clean round numbers in *every* unit system. This is what Revit does — decimal feet internally, families
authored per market.

**Adopted policy:**
1. `catalog/**.yaml` declares sizes in **imperial nominal** (`3'-0" × 7'-0"`, `W14×90`, `2×4`, `#5`).
2. The builder converts to exact metres (×0.0254) at build time — never hand-rounded.
3. Type **names** carry the imperial designation, since names are what appear in schedules and the picker.
4. Metric-market packs become a later, separately-authored catalog (real metric nominals: 900×2100,
   HEA100, 16M) — *not* a conversion of the imperial one.

**One real code gap this exposes:** `families._variant_name` (`families.py:147`) hardcodes metric
formatting, so a 3'-0" door is named `Single door 0.9144×0.0508×2.1336 m`. Naming/display is the only
place massing is genuinely metric-bound. Add to the Phase 0 upstream PRs: unit-aware type naming driven by
the model's `IfcUnitAssignment`. Geometry needs no change.

---

## 8. Scope — a library sufficient to build a complete building

**Goal restated (2026-07-24):** a user must be able to model a complete, coordinated building in any of
six typologies — **residential, commercial, hotel, hospital, industrial, airport** — without hitting a
missing family. Where usable content exists and licensing permits, import it. Where it does not, we
fabricate the geometry ourselves. There is no third option: a blank in the catalog is a building the
user cannot finish.

### 8a. The coverage gap, measured

| | |
|---|---|
| IFC4 `IfcTypeProduct` subclasses | **125** |
| Covered by the catalog today | **15** |
| Not yet covered | **110** |

Roughly: 72 uncovered classes are distribution/MEP (ducts, pipes, cable, valves, pumps, terminals,
controls, medical devices), 32 are structural/envelope (slabs, roofs, stairs, railings, coverings,
members, plates, footings, piles, rebar, tendons, assemblies), and 6 are accessories/fasteners.

Not all 125 are worth building — several are abstract or generic supertypes
(`IfcDistributionElementType`, `IfcBuildingElementType`, `IfcElementType`) that exist only as schema
scaffolding. The meaningful target is **~95 concrete type classes**.

### 8b. Four kinds of content (they are not the same problem)

A "complete building" needs four distinct things, and conflating them is why library projects stall:

1. **Component families** — discrete placeable objects: fixtures, equipment, furniture, doors, windows,
   signage. *This is what most people mean by "family".*
2. **Assembly types for authored elements** — wall, slab, roof, ceiling, covering types carrying
   material layer sets. The user draws the geometry in massing; the library supplies the *assembly
   definition*. A complete library must ship these or every wall is an unnamed slab.
3. **Routing/segment types** — duct, pipe, conduit, cable tray, cable segments and their fittings, each
   with **`IfcDistributionPort`s** so massing's port-to-port connectivity works. Sized by standard trade
   increments, not modelled one-off.
4. **Composite assemblies** — stairs, railings, trusses, curtain wall, headwalls, workstations, jet
   bridges: multi-part `IfcElementAssembly` where the parts stay real, schedulable elements.

### 8c. Discipline matrices

**Architectural & finishes** — `IfcWallType`, `IfcSlabType`, `IfcRoofType`, `IfcCoveringType`,
`IfcStairType`/`IfcStairFlightType`, `IfcRampType`/`IfcRampFlightType`, `IfcRailingType`, `IfcDoorType`,
`IfcWindowType`, `IfcCurtainWallType`, `IfcPlateType`, `IfcMemberType`, `IfcShadingDeviceType`,
`IfcFurnitureType`, `IfcSystemFurnitureElementType`, `IfcBuildingElementProxyType`

Wall assemblies (stud/CMU/concrete/curtain/shaft/fire-rated), floor and roof assemblies, ceilings (ACT
grid, gyp, linear metal), flooring finishes (carpet tile, LVT, sheet vinyl, terrazzo, sealed concrete,
epoxy, raised access), wall finishes (paint, tile, panel, FRP, acoustic), doors (flush, glazed, HM,
sliding, overhead coiling, fire, lead-lined, ICU sliding, hangar), windows and storefront, curtain wall,
louvres, stairs (steel pan, concrete, monumental, ships ladder), railings and guards, toilet partitions,
lockers, casework, signage, specialties.

**Structural — steel** — `IfcColumnType`, `IfcBeamType`, `IfcMemberType`, `IfcPlateType`,
`IfcFootingType`, `IfcPileType`, `IfcElementAssemblyType`, `IfcMechanicalFastenerType`,
`IfcDiscreteAccessoryType`

W/HP/S/M/C/MC/L/WT/HSS/pipe sections (AISC v16.0-driven), joists and joist girders, metal deck (form,
composite, roof), base/cap/gusset/shear plates, bracing, trusses, steel stairs and railings, anchor
rods, bolts, welds, embeds, moment and shear connections.

**Structural — concrete** — `IfcColumnType`, `IfcBeamType`, `IfcSlabType`, `IfcWallType`,
`IfcFootingType`, `IfcPileType`, `IfcReinforcingBarType`, `IfcReinforcingMeshType`, `IfcTendonType`,
`IfcTendonAnchorType`

Cast-in-place columns/beams/slabs/walls/shear walls, spread and strip footings, pile caps, drilled
piers, precast (double-tee, hollowcore, spandrel, column, wall panel), post-tensioning tendons and
anchors, rebar (#3-#18, ASTM A615/A706), WWF mesh, accessories.

**Structural — timber** — `IfcColumnType`, `IfcBeamType`, `IfcMemberType`, `IfcPlateType`,
`IfcElementAssemblyType`

Dimensional lumber (2x4 through 2x12 — **nominal is not actual**; a 2x4 is 1 1/2" x 3 1/2"),
studs/plates/joists/rafters, engineered lumber (LVL, PSL, LSL, I-joists), glulam, CLT and mass-timber
panels, trusses, sheathing, connectors and hangers.

**Mechanical / HVAC** — `IfcDuctSegmentType`, `IfcDuctFittingType`, `IfcDuctSilencerType`,
`IfcAirTerminalType`, `IfcAirTerminalBoxType`, `IfcDamperType`, `IfcFanType`, `IfcCoilType`,
`IfcChillerType`, `IfcBoilerType`, `IfcCoolingTowerType`, `IfcCompressorType`, `IfcCondenserType`,
`IfcPumpType`, `IfcHeatExchangerType`, `IfcHumidifierType`, `IfcFilterType`, `IfcUnitaryEquipmentType`,
`IfcAirToAirHeatRecoveryType`, `IfcEvaporativeCoolerType`, `IfcSpaceHeaterType`, `IfcTankType`,
`IfcValveType`, `IfcVibrationIsolatorType`, `IfcChimneyType`

Round/rectangular/oval duct and full fitting families (elbow, tee, wye, transition, offset, tap, cap),
VAV/CAV/fan-powered boxes, diffusers/registers/grilles/linear slot, AHU/RTU/DOAS/ERV, split systems,
VRF, fan coil, PTAC (hotel), unit heaters, radiant panels, chillers, boilers, cooling towers, pumps,
heat exchangers, dampers (fire/smoke/balancing), louvres, exhaust fans, kitchen hoods, dust collection
(industrial), pressure-zone equipment (hospital).

**Electrical** — `IfcCableSegmentType`, `IfcCableFittingType`, `IfcCableCarrierSegmentType`,
`IfcCableCarrierFittingType`, `IfcElectricDistributionBoardType`, `IfcTransformerType`,
`IfcSwitchingDeviceType`, `IfcProtectiveDeviceType`, `IfcOutletType`, `IfcJunctionBoxType`,
`IfcLightFixtureType`, `IfcLampType`, `IfcElectricGeneratorType`, `IfcElectricMotorType`,
`IfcElectricFlowStorageDeviceType`, `IfcSolarDeviceType`, `IfcAudioVisualApplianceType`,
`IfcCommunicationsApplianceType`, `IfcMotorConnectionType`, `IfcElectricTimeControlType`

Conduit and fittings, cable tray/ladder/basket/wireway and fittings, busway, panelboards, switchboards,
MCCs, transformers (dry/pad), switchgear, generators and ATS, UPS and batteries, receptacles and
devices, lighting (troffer, downlight, linear, high-bay, wall pack, emergency, exit, site pole),
lighting controls, fire alarm devices, security/AV/data, nurse call (hospital), gate and baggage power
(airport).

**Plumbing** — `IfcPipeSegmentType`, `IfcPipeFittingType`, `IfcValveType`, `IfcSanitaryTerminalType`,
`IfcWasteTerminalType`, `IfcStackTerminalType`, `IfcInterceptorType`, `IfcTankType`, `IfcPumpType`,
`IfcFlowMeterType`, `IfcMedicalDeviceType`

Pipe (copper, PEX, CPVC, cast iron, carbon steel, PVC) by nominal size with fittings, valves, fixtures
(WC, urinal, lavatory, sink, shower, tub, drinking fountain, mop basin, emergency shower/eyewash),
carriers, floor/roof drains, cleanouts, traps, grease and oil interceptors, water heaters and storage,
booster pumps, backflow preventers, meters, **medical gas** (oxygen, vacuum, medical air, nitrous —
hospital), compressed air and process piping (industrial), fuel systems.

**Fire protection & fire sprinkler** — `IfcFireSuppressionTerminalType`, `IfcPipeSegmentType`,
`IfcPipeFittingType`, `IfcValveType`, `IfcAlarmType`, `IfcSensorType`, `IfcPumpType`, `IfcTankType`,
`IfcFlowMeterType`, `IfcProtectiveDeviceType`

Sprinkler heads (pendent, upright, sidewall, concealed, dry, **ESFR** for industrial/warehouse),
sprinkler pipe and fittings by schedule, risers, standpipes, FDC, hose valves, control and check
valves, backflow, flow/tamper switches, fire pumps and jockey pumps, water storage tanks, fire
extinguishers and cabinets, alarm devices (pull, horn/strobe, smoke, heat, duct detector), clean-agent
suppression (data/electrical rooms), kitchen hood suppression, fire and smoke dampers, fire-rated
assemblies and firestopping.

**Conveying** — `IfcTransportElementType`

Passenger/service/freight elevators (hydraulic and traction), escalators, moving walks (airport),
dumbwaiters, wheelchair lifts, material hoists, **overhead cranes and monorails** (industrial),
**jet bridges** and baggage handling conveyors (airport).

**Site & civil** — `IfcGeographicElementType`, `IfcCivilElementType`,
`IfcDistributionChamberElementType`, `IfcFootingType`, `IfcRailingType`, `IfcBuildingElementProxyType`

Paving and curbs, site walls, fencing and gates, bollards, site furnishings, planting, catch basins,
manholes, utility structures, transformer pads, dumpster enclosures, light poles, retaining walls,
loading docks and levelers, aprons and taxiway edges (airport).

**Construction operations** (differentiator) — `IfcBuildingElementProxyType`, `IfcElementAssemblyType`,
`IfcTransportElementType`

Scaffolding, shoring, formwork, tower and mobile cranes, hoists, temporary fencing and barricades,
jobsite trailers, dumpsters, laydown and staging, safety rails and netting, temporary power and
lighting. Plugs directly into the GC portal's logistics modules.

### 8d. Typology completeness matrix

The disciplines above cover the common core. Each typology then demands content the others do not —
this is the checklist that defines "done" for each:

| Typology | Typology-specific content that must exist |
|---|---|
| **Residential** | Residential appliances, kitchen/bath casework, closet systems, furnaces and split systems, water heaters, laundry, decks/balconies/railings, garage doors, egress windows, unit-separation and shaft assemblies |
| **Commercial** | Open-office systems furniture, core and restroom packages, elevator banks, curtain wall and storefront, VAV/FPB distribution, raised access floor, ACT ceiling grid, roof screens, loading dock |
| **Hotel** | Guestroom FF&E packages, PTAC/vertical fan coil, guest bath modules, corridor and BOH assemblies, commercial laundry, commercial kitchen, banquet/meeting FF&E, pool equipment, key-card and life-safety devices |
| **Hospital** | Headwalls and med-gas outlets, patient-room casework, OR equipment (lights, booms, tables), imaging (MRI/CT with RF and lead shielding), isolation-room pressure assemblies, nurse call, lead-lined doors and partitions, sterile processing, lab casework and fume hoods, ICU sliding doors, pneumatic tube |
| **Industrial** | High-bay lighting, ESFR sprinkler, overhead cranes and monorails, mezzanines and platforms, dock levelers/shelters/restraints, process equipment pads, trench and area drains, compressed air and process piping, dust collection, hazardous storage, guard rail and bollards |
| **Airport** | Long-span structure and roof, jet bridges, baggage handling and carousels, check-in and gate counters, security screening lines, moving walks, FIDS displays, terminal seating, glazed facade systems, apron and taxiway edge elements |

### 8e. Volume targets, revised

| Milestone | Families | Types | Notes |
|---|---|---|---|
| Today | 52 | 133 | 15 IFC classes; 26 types on real profiles |
| v0.3 | ~140 | ~1,200 | steel + concrete + timber complete (AISC-driven) |
| v0.5 | ~330 | ~3,000 | + full architectural, finishes, envelope, stairs/railings |
| v0.7 | ~560 | ~5,500 | + mechanical, electrical, plumbing with ports |
| v0.9 | ~700 | ~7,000 | + fire protection/sprinkler, conveying, site, construction ops |
| **v1.0** | **~800** | **~7,500** | + all six typology packages; every typology buildable end-to-end |

The type-to-family ratio (~9:1) is deliberate — most growth is *generated* variants (every AISC section,
every pipe size, every duct size), not hand-authored YAML.

### 8f. Geometry fabrication capability — the builders this requires

The current two builders (box, profile-sweep) cannot produce most of the above. All of the following is
verified present in IFC4 and IfcOpenShell 0.8.5, so it is buildable offline today:

| Builder | IFC entity | Unlocks |
|---|---|---|
| `revolve` | `IfcRevolvedAreaSolid` | Tanks, water heaters, domes, bollards, sanitary fixtures, valves |
| `swept_disk` | `IfcSweptDiskSolid` | **Pipe, conduit, rebar, handrails** — anything round along a path |
| `boolean` | `IfcBooleanResult` / `IfcBooleanClippingResult` | Vision panels, louvres, sink basins, penetrations, clipped members |
| `taper` | `IfcExtrudedAreaSolidTapered` | Duct transitions and reducers, tapered columns |
| `path_sweep` | `IfcSurfaceCurveSweptAreaSolid`, `IfcFixedReferenceSweptAreaSolid` | Duct/tray along a route, curved members |
| `voided_profile` | `IfcArbitraryProfileDefWithVoids` | Hollowcore, deck profiles, custom sections |
| `composite_profile` | `IfcCompositeProfileDef` | Built-up and back-to-back sections |
| `mesh` | `IfcTriangulatedFaceSet` / `IfcPolygonalFaceSet` | Organic/complex geometry; the landing format for imports |
| `assembly` | `IfcElementAssembly` + parts | Stairs, trusses, curtain wall, headwalls, jet bridges |
| `ports` | `IfcDistributionPort` | **MEP connectivity** — required for all routing content |

IfcOpenShell also ships purpose-built `geometry.add_door_representation`, `add_window_representation`,
`add_railing_representation`, `add_slab_representation`, `add_wall_representation`,
`add_mesh_representation` and `add_boolean`. These materially reduce the fabrication cost for exactly
the elements that are hardest to hand-roll, and should be preferred over bespoke code wherever they fit.

**Unverified assumption that gates all routing content:** whether `IfcDistributionPort` survives
`project.append_asset` (massing's import path) is **not yet tested**. Everything in mechanical,
electrical, plumbing and fire-sprinkler routing depends on it. This is the first task of Phase 3 and its
result may change that phase's design.

### 8g. Acquisition strategy — import where we can, fabricate where we cannot

Per section 6.2 no major BIM portal grants redistribution, so the *default is fabricate*. Decision order
for each family:

1. **Fabricate parametrically** (default) — dimensions come from public standards (AISC, ASTM, ASME,
   NFPA, ADA, nominal trade sizes). Dimensional facts are not copyrightable; the geometry is ours. This
   covers the large majority of the catalog.
2. **Derive from open data** — AISC Shapes Database, published nominal size tables, bSDD properties.
   Cite the source in the provenance pset; ship derived values, never the source file.
3. **Import permissively-licensed geometry** — only where fabrication is genuinely impractical (organic
   or highly detailed forms). Normalise into the pack, stamp licence and attribution in `MF_Library`,
   record the original licence in `THIRD_PARTY.md`.
4. **User-supplied ingest** — the license-gated path (Phase 7) for manufacturer content a deployment
   downloads under its own terms. We never redistribute it.

Any family that cannot honestly sit in tiers 1-3 ships as a **dimensionally-correct L200 proxy** flagged
`MF_Library.GeometryStatus = "proxy"`, rather than being omitted. A correct box the user can schedule
and coordinate beats a hole in the catalog — but it must be labelled, never passed off as detailed
content.

## 9. Repository architecture

```
massing_families/
├─ src/massing_families/
│  ├─ spec.py              # FamilySpec dataclass + schema validation
│  ├─ builders/
│  │  ├─ box.py            # L200 fallback (parity with today)
│  │  ├─ profile.py        # swept parameterized profiles (I/C/L/T/Z/hollow)
│  │  ├─ revolve.py        # revolutions (tanks, domes, fixtures)
│  │  ├─ boolean.py        # voids/subtractions (doors, louvres, sinks)
│  │  └─ assembly.py       # L350 multi-part + IfcDistributionPort
│  ├─ classification.py    # Uniclass / OmniClass reference attachment
│  ├─ psets.py             # IFC standard pset application + validation
│  ├─ quantities.py        # IfcElementQuantity (areas/volumes for takeoff)
│  ├─ thumbnails.py        # offscreen preview render → PNG
│  ├─ pack.py              # emit versioned .ifc pack + manifest entry
│  └─ validate.py          # round-trip / schema / duplicate-name gate
├─ catalog/                # ← declarative source of truth
│  ├─ architectural/       doors.yaml windows.yaml walls.yaml stairs.yaml …
│  ├─ structural/          steel.yaml concrete.yaml timber.yaml
│  ├─ mechanical/  plumbing/  electrical/  fire/  conveying/
│  ├─ site/  construction_ops/  specialties/
├─ data/
│  ├─ aisc_shapes_v16.csv          # derived dimensional data
│  ├─ uniclass_pr.csv
│  └─ omniclass_23.csv
├─ packs/                  # build output — versioned .ifc + manifest.json
├─ thumbnails/
├─ tests/
└─ PLAN.md
```

### Family spec example

```yaml
- key: steel_column_w
  label: W-Shape Column
  ifc_class: IfcColumnType
  predefined: COLUMN
  category: Structural
  discipline: structural
  tier: L300
  builder: profile
  profile:
    kind: IShape
    source: aisc            # expands one spec into every W-shape
    filter: "W8..W14"
  psets:
    Pset_ColumnCommon:
      Reference: "{shape}"
      LoadBearing: true
      IsExternal: false
  material: { name: "ASTM A992 Steel", category: steel }
  classification:
    uniclass: Pr_20_93_71
    omniclass: "23-13 11 11"
  license: CC0-1.0
  source: massing-families
```

One spec → dozens of real, correctly-dimensioned catalogued types.

---

## 10. Phased roadmap

Revised for the full-building scope (section 8). Phases 0-1 are complete. Durations assume one
developer; the generator-driven phases scale far better than the hand-authored ones.

### Phase 0 — Foundations + upstream fixes ✅ *complete*
Repo, spec schema validated against IFC4, box + profile builders, enrichment, pack emitter, manifest,
golden round-trip test. Upstream PRs for the two section-5 defects still outstanding and still gate
broad L300 rollout.

### Phase 1 — Port massing's built-ins to imperial ✅ *complete*
All 46 built-in families ported and mapped via `massing_key`; 52 families / 133 types across 8
discipline packs; 26 types on real parametric profiles.

### Phase 2 — Structural complete *(4 weeks)* ← **current**
- `generator: aisc` driven by AISC Shapes Database v16.0 — every W/HP/S/M/C/MC/L/WT/HSS/pipe section,
  replacing the hand-transcribed literals now flagged in `catalog/structural/steel.yaml`
- Concrete: cast-in-place, precast (double-tee, hollowcore, spandrel), footings, piles, pile caps
- Rebar (#3-#18) and WWF mesh via the new `swept_disk` builder; PT tendons and anchors
- Timber: dimensional lumber with **actual** dressed sizes, engineered lumber, glulam, CLT, I-joists
- New builders: `swept_disk`, `voided_profile`, `composite_profile`
- **Exit:** ~140 families / ~1,200 types; a structural frame is fully modellable in steel, concrete or
  timber

### Phase 3 — MEP + fire protection *(10 weeks)*
- **Week 1 is a spike:** does `IfcDistributionPort` survive `project.append_asset`? Everything else in
  this phase depends on the answer, and it is currently unverified (section 8f). If ports do not
  survive, the fallback is port metadata in a pset plus an upstream PR — decide before building content.
- Duct and pipe segment/fitting generators across standard trade sizes, with ports
- Conduit, cable tray, busway, cable segments
- Equipment: AHU/RTU/VAV, chillers, boilers, cooling towers, pumps, heat exchangers
- Electrical distribution: panelboards, switchgear, transformers, generators, devices, lighting
- Plumbing fixtures and specialties, drains, interceptors, backflow, medical gas
- Fire protection: sprinkler heads (incl. ESFR), sprinkler pipe, risers, standpipes, FDC, fire pumps,
  alarm devices, fire/smoke dampers
- New builders: `revolve`, `taper`, `path_sweep`, `ports`
- **Exit:** ~560 families / ~5,500 types; MEP and FP systems route and connect

### Phase 4 — Architectural, finishes, envelope *(8 weeks)*
- Wall/floor/roof/ceiling assembly types with full material layer sets (the section-8b item 2 gap)
- Finishes: flooring, wall finishes, ceilings, raised access floor
- Doors and windows at full matrix, incl. fire, lead-lined, ICU sliding, overhead coiling, hangar
- Curtain wall, storefront, louvres, shading devices
- Stairs, ramps, railings and guards as real assemblies
- Specialties: toilet partitions, lockers, casework, signage
- New builders: `boolean`, `assembly`; adopt IfcOpenShell's `add_door_representation`,
  `add_window_representation`, `add_railing_representation`, `add_slab_representation`
- **Exit:** ~700 families / ~7,000 types; a building envelope and interior are fully specifiable

### Phase 5 — Conveying, site, construction operations *(4 weeks)*
- Elevators, escalators, moving walks, dumbwaiters, lifts, hoists
- Overhead cranes and monorails (industrial); jet bridges and baggage handling (airport)
- Site: paving, curbs, walls, fencing, bollards, drainage structures, light poles, docks
- **Temporary works:** scaffolding, shoring, formwork, cranes, trailers, fencing, laydown
- **Exit:** the differentiating content, wired to the GC portal

### Phase 6 — Typology packages *(6 weeks)*
One pack per typology, each a curated bundle plus the specific content only it needs (section 8d):
residential, commercial, hotel, hospital, industrial, airport. Hospital and airport carry the most
unique content (med gas, headwalls, imaging shielding; jet bridges, baggage, security lines).
- Each typology ships a **completeness checklist test**: model a reference building of that type and
  assert no required system has a missing family. This is what makes "can build a full building"
  measurable rather than aspirational.
- **Exit:** ~800 families / ~7,500 types; all six typologies buildable end-to-end

### Phase 7 — Catalog UX, ingest, publishing *(4 weeks)*
- Thumbnails per type; manifest-driven browsable/searchable picker (upstream PR to `/families/library`)
- License-gated user-supplied ingest pipeline; `THIRD_PARTY.md` attribution
- Semver release process; packs dropped into `services/data/families/external/`
- **Exit:** v1.0 shipped and repeatable

### Cross-cutting, every phase
Classification (Uniclass Pr/Ss, verified against the published tables — never guessed), standard IFC
psets, quantities, materials, provenance including `GeometryStatus` for proxies, and a pack-size/convert
-time budget measured in CI.

## 11. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Redistribution of third-party content | Legal | Generate everything; ingest path is user-supplied only. Provenance pset on every object. |
| Rich geometry corrupts on edit (**verified live**) | High | Phase 0 upstream fix is a hard gate before any L300 content ships |
| Monolithic pack floods projects on import | High | Granular discipline packs; import is all-or-nothing per file |
| `(class, Name)` dedup collisions | Medium | Naming convention + `MF_Library.Key` identity |
| Ports may not survive append_asset | Medium | Explicit Phase 3 spike **before** committing to MEP scope |
| Pack size / fragment conversion cost | Medium | Budget polygon counts per tier; measure convert time in CI |
| AISC data redistribution terms | Low–Med | Derive dimensions, don't ship their file; verify before Phase 2 |
| Catalog outgrows a flat picker | Medium | Manifest + classification-driven search (Phase 6) |

---

## 12. Immediate next steps

1. Confirm this plan's scope and phase ordering.
2. Open the two Phase 0 bug PRs against `ibuilder/massing` — they block everything downstream.
3. Scaffold this repo and land the golden round-trip test.
4. Execute Phase 1 (real geometry, existing 46) as the end-to-end proof.
5. Verify AISC data terms before Phase 2 begins.

### Open questions for you

- **Priority:** lead with *breadth* (thin coverage everywhere, fast demo value) or *depth*
  (architectural + structural done properly first)? The plan above assumes depth.
- **Repo destiny:** stay a separate content repo, or land as a subdirectory in `ibuilder/massing`?
  Separate is recommended — independent release cadence, and content churn stays out of app history.
