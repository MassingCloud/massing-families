## What this changes

<!-- One or two lines. If it adds content, say which discipline. -->

## Checklist

Adding or changing families — the tests enforce all of these, so this is really a pre-flight:

- [ ] Classification code **looked up** at [uniclass.thenbs.com](https://uniclass.thenbs.com) and added
      to `data/uniclass_codes.csv` with its published title — never guessed
- [ ] Sizes in US imperial nominals; nominal-vs-actual handled (a `2x4` is built 1½" × 3½")
- [ ] Not a duplicate — checked [`docs/CATALOG.md`](../blob/main/docs/CATALOG.md)
- [ ] `tier` matches the builder (`L200` ⟺ `box`)
- [ ] `material` set, and `ports` if it carries flow
- [ ] Dimensions come from a published standard — not from a BIM object portal or a manufacturer's
      Revit family, however re-authored
- [ ] `pytest` green
- [ ] `python -m massing_families.cli docs` re-run if the catalog changed

## Where the dimensions come from

<!-- AISC, ASME B36.10, ASTM, NFPA, IBC, ADA, nominal trade sizes… -->
