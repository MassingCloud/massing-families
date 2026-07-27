# Changelog

Versions are the tag on the GitHub release; each release attaches one `.ifc` per pack plus a
`manifest.json` with a sha256 for every pack.

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
