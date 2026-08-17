# Security policy

This is a content library and a generator. It has no server, no network calls at runtime, and handles
no user data — so the realistic risk surface is narrow but not empty.

## Reporting

Open a [security advisory](https://github.com/MassingCloud/massing-families/security/advisories/new),
or a normal issue if the finding is not sensitive.

Please include what you ran, what you expected, and what happened. If it concerns generated content,
name the pack and type — the type name is unique across the catalog.

## What counts

**In scope**

- Anything in `src/`, `tools/` or `upstream/` that executes attacker-controlled input unsafely — the
  build reads YAML and CSV, and `upstream/fetch_families.py` reads a release manifest and writes files
  to a path you supply.
- A published pack whose sha256 does not match its `manifest.json` entry, or a release asset that does
  not match the tag it claims. The fetch script verifies every pack before writing; a mismatch means
  either corruption or tampering and is worth reporting either way.
- Malformed IFC that causes a crash or resource exhaustion in a consumer parsing our packs.

**Out of scope**

- Dimensional inaccuracy in a family. That is a correctness bug — open a normal issue. Dimensions
  drive geometry, not design; see the note in [docs/GUIDE.md](docs/GUIDE.md).
- Vulnerabilities in IfcOpenShell or PyYAML. Report those upstream; tell us if a version pin here
  makes them reachable.

## What we do

The build is offline and deterministic: it reads `catalog/`, `data/` and nothing else, makes no
network calls, and writes only into the output directory. `upstream/fetch_families.py` is the only
component that touches the network, and it verifies each pack's sha256 against the release manifest
before writing anything to disk.

Releases are built by GitHub Actions from a tag, never uploaded by hand, so what ships is what the
tagged source produces.

## Verifying what you downloaded

Every release includes `manifest.json` with a sha256 per pack. `fetch_families.py` checks these
automatically; to verify by hand:

```bash
sha256sum massing-families-structural-steel-w-v0.1.5.ifc
```

and compare against the matching `sha256` entry in `manifest.json`.

Each pack also names its origin in its STEP header — author, organization, licence and source URL —
so a file that has drifted from its release can still be traced.
