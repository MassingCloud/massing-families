# Changelog

Versions are the tag on the GitHub release; each release attaches one `.ifc` per pack plus a
`manifest.json` with a sha256 for every pack.

## v0.1.5

Lessons pulled back from massing v0.3.662–v0.3.718, which implemented the platform side, plus
forward-looking documentation.

- **Completeness gate tightened.** massing's own coverage gate found 413 families and **zero
  `IfcFootingType`** — every typology unbuildable for the same reason. This library's check could not
  have caught it: its `foundations` requirement read `ifc_class in {IfcFootingType, IfcPileType}`, and
  a single HP pile satisfied the OR while no footings existed. An OR over two classes only proves one
  of them exists. Split into `footings` and `piles`, and the other multi-class requirements audited
  the same way — `outlets`/`switches` and `fire alarm notification`/`fire detection` are now separate.
  `cooling source` stays an OR deliberately, since an air-cooled chiller needs no tower.
  Core systems: 35 -> 38, all passing.
- **The geometry patch is withdrawn.** `upstream/0001-family-geometry-fixes.patch` and
  `families.patched.py` deleted. massing implemented its own fix after reproducing each defect against
  real content, and it is strictly better: the patch covered three of four defects and *caused* the
  fourth. `IfcRectangleHollowProfileDef` is a subtype of `IfcRectangleProfileDef`, so a resize guarded
  by `is_a("IfcRectangleProfileDef")` matched HSS tubes, rewrote their dimensions while leaving wall
  thickness alone, and kept the catalog name — an `HSS24X12X3/4` becoming a 500x500 tube still
  labelled as a standard section. In IFC, `is_a("X")` is a subtype test, not an equality test; a
  mutation path almost always wants exact-class comparison. This library's own code was audited and
  carries no such guard.
- `upstream/verify_patch.py` -> `verify_geometry_support.py`: checks whether the massing you have
  handles this library's geometry, rather than comparing a patch against a baseline. Four behaviours,
  all passing against v0.3.718.
- `upstream/README.md` rewritten around what massing now provides — `family_shapes.py`,
  `family_packs.py`, `POST /families/import-pack`, manifest metadata on `GET /families/library`.
- **[ROADMAP.md](ROADMAP.md)** — where the library stands, the honest gap (320 of 419 families are
  L200 proxies; 53 IFC4 type classes untouched), what is next and what is deliberately not planned.
- **Tier corrected on 13 families.** They declared `tier: L200` while using `revolve` or
  `swept_disk` builders, so "how many families are still proxies" had two answers — 333 by declared
  tier, 320 by derived `GeometryStatus`. Only the derived number is true. Tiers fixed to L300 and a
  guard added (`test_tier_agrees_with_builder`) so a declared tier can no longer contradict the
  geometry actually built. Caught by the new roadmap-metrics test before it shipped.
- **[docs/GUIDE.md](docs/GUIDE.md)** — a consumer guide. Which packs to take and why not to take them
  all, both import routes, what every type carries, how to read `GeometryStatus` before committing to
  a detail, and which overlapping families are real products rather than duplicates.

## v0.1.4

Licensing carried by the artifacts themselves, and public-facing documentation.

- **IFC packs now declare their licence in the STEP header.** IfcOpenShell's default is
  `FILE_NAME('/dev/null', …, 'Nobody')` with no author or organization; packs now carry the filename,
  `massing-families` as author, `Massing.Cloud` as organization, and `CC0-1.0` plus the repository URL
  as authorization, with the library version in `FILE_DESCRIPTION`. `IfcProject.Description` carries
  the same for viewers that show it but not the header. Once a pack is downloaded and separated from
  `manifest.json`, the header is the only place left that says what the terms are.
- Licence stated in `docs/CATALOG.md`, `docs/SPEC.md`, `NOTICE.md` and the README, which now spells
  out that the declaration lives in three places.
- `CONTRIBUTING.md` gains an inbound-licence section: content CC0, code MIT, and an explicit note
  that geometry from a BIM object portal or a manufacturer's Revit family cannot be contributed no
  matter how it was re-authored.
- Documentation: generated `docs/CATALOG.md`, rewritten README, `CONTRIBUTING.md`, `docs/SPEC.md`,
  this changelog. `tests/test_docs.py` fails the build if the catalog reference goes stale, if the
  README's counts stop matching, if a builder or generator is undocumented, or if any document still
  describes the repo as private.
- `LICENSE` carves out `upstream/`, which holds a derivative of a source file from `ibuilder/massing`
  and follows that project's terms.

## v0.1.3

Duplicate families merged and guarded.

- Seven duplicate pairs folded into one family each — two "Copper Pipe Type L", two cast-iron no-hub,
  two water closets, two urinals, two showers, two kitchen sinks, two task chairs. Merged in favour
  of the richer definition (the newer ones carried ports and fixture-unit psets), keeping the
  canonical key, label and `massing_key`. All 46 massing built-in mappings verified intact.
- `sink_service` deliberately kept separate — a molded-stone mop sink at 3 DFU is a different product
  from a stainless kitchen sink at 2 DFU. The redundant `Mop basin` type was dropped from `sink`.
- New guards: `test_no_duplicate_families` (same label + class + discipline) and
  `test_no_type_name_collisions` — the latter catches the `(ifc_class, Name)` identity massing dedupes
  on, which would otherwise silently drop a type on import.
- Depth batches across foundations, fire, electrical, mechanical, architectural, interiors, conveying
  and site.

**419 families · 2,769 types · 57 packs**

## v0.1.2

Licensing declared.

- A shelf reading `manifest.json` saw no `license` key and correctly reported the packs unlicensed.
  The declaration existed per-pack and per-family but never at the top level, and the repo had no
  `LICENSE` file at all.
- Manifest gains `license` (SPDX id for the packs), a `licensing` block with code licence,
  attribution and links, and `repository`. Derived from the specs, not hardcoded — if any family
  declares something other than CC0 the manifest reports `MIXED` rather than overstating.
- `LICENSE` (MIT, generator), `LICENSE-CONTENT` (CC0-1.0, catalog and packs), `NOTICE.md` (provenance
  for derived AISC and Uniclass data, and what is deliberately not used).
- Plumbing depth batch classified against looked-up Uniclass codes.

## v0.1.1

Release-pipeline fixes found by the first CI run.

- `--version` moved onto the `build` subcommand; as a parent-parser flag it had to precede the
  subcommand and the release workflow was rejected.
- The build now clears its output directory. Renamed packs and older versions had accumulated as
  orphans — 41 stale files — and anything globbing `packs/*.ifc` counted content no longer in the
  catalog. This had inflated a reported type count to 2,355 when the manifest total of 2,334 was
  correct throughout.
- `fetch_families.py` corrected: right repository, and token resolution from
  `--token` / `$GITHUB_TOKEN` / `$GH_TOKEN` / the `gh` CLI.

## v0.1.0

First release.

- 8 geometry builders — box, profile, swept_disk, revolve, boolean, taper, assembly, mesh — all
  verified to survive massing's `import_types_from_ifc`.
- Generators: `aisc` (every AISC mill section), `sizes` (nominal trade sizes), `rebar`.
- Authored in US imperial nominals, stored in exact metres.
- Classification verified against the published Uniclass Pr/Ss tables, enforced by a test.
- Validated against the real IFC4 schema — bad classes and illegal `PredefinedType` enums fail the
  build.
- All six target typologies pass a completeness checklist.
- `upstream/` — verified patch for the two massing geometry defects, plus the fetch script.
