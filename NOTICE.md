# Third-party data notice

> Library content is CC0-1.0 ([LICENSE-CONTENT](LICENSE-CONTENT)); the generator is MIT
> ([LICENSE](LICENSE)). This file covers the reference data those two do not.

The library generates its own geometry (see [LICENSE-CONTENT](LICENSE-CONTENT)), but two files under
`data/` are **derived from third-party sources**. Neither source file is redistributed here — only
values derived from them, which is the tier-2 rule in [PLAN.md §8g](PLAN.md).

## `data/aisc_shapes.csv` — steel section dimensions

**Derived from:** AISC Shapes Database v15.0 (US customary), via
[ambaker1/aisc-csv](https://github.com/ambaker1/aisc-csv) (MIT), by `tools/derive_aisc.py`.

Contains section dimensions (depth, flange width, web and flange thickness, fillet radius, wall
thickness) for 1,452 standard mill shapes, reduced to only the columns the geometry builders need.
The AISC spreadsheet itself is not included.

Dimensions of standard mill shapes are factual measurements, not creative expression. The American
Institute of Steel Construction is not affiliated with this project and does not endorse it. Section
properties beyond geometry — areas, moments of inertia, design values — are **not** reproduced here;
consult the AISC Steel Construction Manual for engineering use.

> ⚠ These values drive geometry, not engineering. Verify against a current AISC source before relying
> on them for design.

## `data/uniclass_codes.csv` — classification codes

**Derived from:** Uniclass Pr (Products) and Ss (Systems) tables, published by
[NBS](https://uniclass.thenbs.com).

A de-minimis extract: only the ~122 codes this catalog actually references, with their published
titles, held as a validation fixture so `tests/test_classification.py` can fail the build on any code
that does not exist. The full tables (7,892 Pr rows alone) are not redistributed.

Uniclass is maintained and published by NBS. Consult
[uniclass.thenbs.com](https://uniclass.thenbs.com) for the authoritative tables and current terms.

## Not used

**MasterFormat** (CSI) is licensed, so no MasterFormat codes are shipped. The `masterformat` field is
supported in family specs so a deployment can supply its own mapping.

**BIM object portals** — BIMobject, NBS Source, bimstore, BIM&CO, Modlar, MEPcontent — license content
for free use *in projects*, not for redistribution. No content is taken from any of them. See
[PLAN.md §6.2](PLAN.md).
