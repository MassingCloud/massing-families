"""Build the library.

    python -m massing_families.cli build            # all disciplines -> packs/
    python -m massing_families.cli build -d structural
    python -m massing_families.cli list             # what the catalog declares, without building
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from . import __version__
from .pack import write_manifest, write_pack
from .spec import load_catalog

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "catalog"
PACKS = ROOT / "packs"


def cmd_build(args) -> int:
    specs = load_catalog(CATALOG, args.discipline)
    if not specs:
        print("no family specs found", file=sys.stderr)
        return 1
    by_discipline: dict[str, list] = defaultdict(list)
    for s in specs:
        by_discipline[s.pack_name].append(s)

    # Clear stale packs first. Pack filenames carry the discipline and version, so renaming a pack or
    # bumping the version leaves orphans behind — and anything globbing `packs/*.ifc` (a deployment
    # fetch, a stats script) then picks up content that is no longer in the catalog.
    args.out.mkdir(parents=True, exist_ok=True)
    stale = sorted(args.out.glob("*.ifc"))
    for old in stale:
        old.unlink()
    if stale:
        print(f"  removed {len(stale)} stale pack(s)")

    entries = []
    for discipline in sorted(by_discipline):
        entry = write_pack(by_discipline[discipline], args.out, discipline, args.version)
        entries.append(entry)
        print(f"  {entry['file']:52} {entry['families']:>3} families  {entry['types']:>4} types  "
              f"{entry['size_bytes']:>9,} B  tiers={','.join(entry['tiers'])}")
    manifest = write_manifest(entries, args.out, args.version, specs)
    total_t = sum(e["types"] for e in entries)
    total_f = sum(e["families"] for e in entries)
    print(f"\n{len(entries)} pack(s), {total_f} families, {total_t} types -> {args.out}")
    print(f"manifest: {manifest}")
    return 0


def cmd_list(args) -> int:
    specs = load_catalog(CATALOG, args.discipline)
    from .generators import expand
    for s in sorted(specs, key=lambda x: (x.discipline, x.category, x.key)):
        variants = expand(s)
        print(f"{s.discipline:14} {s.category:12} {s.tier:5} {s.builder:8} {s.key:22} "
              f"{len(variants):>3} types  {s.label}")
    print(f"\n{len(specs)} families, {sum(len(expand(s)) for s in specs)} types")
    return 0


def cmd_docs(args) -> int:
    from . import docs
    specs = load_catalog(CATALOG)
    path = docs.write(specs, ROOT)
    st = docs.stats(specs)
    print(f"{st['families']} families, {st['types']} types -> {path}")
    return 0


def cmd_site(args) -> int:
    from . import site
    specs = load_catalog(CATALOG)
    path = site.write(specs, ROOT, args.version)
    print(f"{len(specs)} families -> {path} ({path.stat().st_size / 1024:.0f} KB)")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="massing-families")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build IFC packs")
    b.add_argument("-d", "--discipline", default=None)
    b.add_argument("-o", "--out", type=Path, default=PACKS)
    # on the subcommand, not the parent: `build --version X` is the natural form, and an argparse
    # parent-level flag would have to precede the subcommand to be accepted.
    b.add_argument("--version", default=__version__, help="library version stamped into packs")
    b.set_defaults(func=cmd_build)

    ls = sub.add_parser("list", help="list catalog contents")
    ls.add_argument("-d", "--discipline", default=None)
    ls.set_defaults(func=cmd_list)

    dc = sub.add_parser("docs", help="regenerate docs/CATALOG.md from the catalog")
    dc.set_defaults(func=cmd_docs)

    st = sub.add_parser("site", help="regenerate the browsable catalog site (site/index.html)")
    st.add_argument("--version", default=__version__)
    st.set_defaults(func=cmd_site)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
