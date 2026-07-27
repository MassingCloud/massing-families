# Adding to the catalog

Family specs are data. Adding content is a YAML edit in `catalog/<discipline>/`, then:

```bash
python -m massing_families.cli list      # validate + see what you added
pytest                                    # the guards below run here
python -m massing_families.cli docs      # refresh docs/CATALOG.md
```

## The five rules

These are enforced by tests, not convention. A PR that breaks one fails the build.

### 1. Never guess a classification code

Look it up at [uniclass.thenbs.com](https://uniclass.thenbs.com), then add the code **and its
published title** to `data/uniclass_codes.csv`. `tests/test_classification.py` fails on any code not
in that file.

This is not bureaucracy. Codes that read plausibly are routinely wrong:

| assumed for | code | what it actually is |
|---|---|---|
| steel columns | `Pr_20_93_71` | Retaining wall units |
| steel beams | `Pr_20_93_52` | Masonry walling units |
| duct, pipe, sprinklers | `Pr_65_52_15` and three others | do not exist in the Pr table |

Use **Pr** (Products) for manufactured articles and **Ss** (Systems) for assemblies — a wall is a
system, a valve is a product. A test enforces that Ss codes never land on discrete product classes.

### 2. Author in imperial nominals

Sizes go in as `3'-0"`, `1 3/4"`, `W14X90`, `#5`, `2x4` — the designation a US drawing uses. The
builder converts to exact metres. Do not pre-convert; `0.9 m` is not a door size.

Where nominal differs from actual, name the nominal and build the actual: a `2x4` is 1½" × 3½".

Decimal inches are fine for machined parts (`0.285"` web thickness).

### 3. Pick the right builder and tier

| builder | tier | for |
|---|---|---|
| `box` | L200 | a correct bounding box is enough — furniture, equipment cabinets, appliances |
| `profile` | L300 | anything with a real cross-section — structure, pipe, duct, conduit, tray |
| `revolve`, `swept_disk`, `boolean`, `taper` | L300 | tanks, rebar and handrails, openings and voids, transitions |
| `assembly` | L350 | multi-part things whose parts stay real elements |
| `mesh` | — | tessellated geometry; the landing format for imported content |

`GeometryStatus` is derived from the builder, so a `box` family is automatically labelled `proxy`.
Ship a labelled proxy rather than omitting a family — a correct box the user can schedule and
coordinate beats a hole in the catalog.

### 4. Don't duplicate an existing family

Check `docs/CATALOG.md` first. Two families with the same label, class and discipline fail
`test_no_duplicate_families`. If your version is richer, merge into the existing key rather than
adding a parallel one — and keep its `massing_key`, which maps to massing's built-in catalog.

Seven duplicate pairs accumulated once (two "Copper Pipe Type L", two water closets, two task
chairs). Merging is cheap; noticing late is not.

A separate guard, `test_no_type_name_collisions`, catches the harder failure: massing dedupes types
by `(ifc_class, Name)`, so two families emitting the same type name would silently drop one on
import.

### 5. Use a generator for size runs

Hand-listing 283 W-sections is unmaintainable. Reach for:

- **`aisc`** — any AISC family (W, HP, S, M, C, MC, L, WT, HSS, PIPE), filtered by series or depth
- **`sizes`** — nominal trade sizes; `entries` for round, `sections` for rectangular
- **`rebar`** — bar sizes and bend shapes

```yaml
generator: aisc
generator_args: {family: W, series: [W8, W10, W12, W14], length: "12'-0\""}
```

## Pack scoping

`pack:` overrides which release asset a family lands in. Keep packs trade-scoped and under ~1,000
types — massing's import pulls in **every** type in a file, so an oversized pack floods a user's
project with content they never asked for. A test enforces the ceiling.

## Where dimensions may come from

In order of preference:

1. **Public standards** — AISC, ASTM, ASME, NFPA, ADA, IBC, nominal trade sizes. Dimensions of
   standard articles are facts. This covers nearly everything.
2. **Open data** — cite the source in `NOTICE.md`; ship derived values, never the source file.
3. **Permissively-licensed geometry** — only where fabrication is impractical. Record licence and
   attribution in `MF_Library` and `NOTICE.md`.

**Never** copy from a BIM object portal. Their terms allow use in projects, not redistribution.
Anything that cannot honestly reach tiers 1–3 ships as a labelled L200 proxy.

## Checklist

- [ ] Classification code looked up and added to `data/uniclass_codes.csv` with its title
- [ ] Sizes in imperial nominals; nominal-vs-actual handled
- [ ] `PredefinedType` valid for the IFC class (the schema validator will tell you)
- [ ] Not a duplicate — checked `docs/CATALOG.md`
- [ ] `material`, and `ports` if it carries flow
- [ ] `pytest` green
- [ ] `python -m massing_families.cli docs` re-run

## Layout

```
catalog/<discipline>/*.yaml    family specs — the source of truth
src/massing_families/          generator: spec, builders, generators, enrichment, pack
  builders/                    one module per geometry archetype
  generators/                  aisc, sizes, rebar
data/                          derived reference data (see NOTICE.md)
docs/CATALOG.md                generated — do not hand-edit
upstream/                      integration with massing: fetch script + geometry patch
packs/                         build output — gitignored, published as release assets
```

See [docs/SPEC.md](docs/SPEC.md) for every spec field and [PLAN.md](PLAN.md) for why the architecture
is shaped this way.
