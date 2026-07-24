"""Fetch the family library into a massing deployment.

Vendor this into massing as `scripts/fetch_families.py`. It downloads a tagged release of
`ibuilder/massing-families` into `services/data/families/external/`, where `GET /families/library`
already lists it and `POST /projects/{id}/families/import` can pull types from it.

    python scripts/fetch_families.py                 # latest release, all packs
    python scripts/fetch_families.py --tag v0.1.0
    python scripts/fetch_families.py --packs structural-steel-w mechanical-ductwork
    python scripts/fetch_families.py --list

Why fetch rather than commit: massing's .gitignore treats `*.ifc` as a build artifact ("data /
artifacts (do NOT commit models or tiles)"), and the full library is ~6 MB across 40 packs that
regenerate on every catalog change. Packs are published as release assets with a sha256 per pack in
`manifest.json`, which this script verifies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

REPO = "ibuilder/massing-families"
API = f"https://api.github.com/repos/{REPO}/releases"
# services/data/families/external/ relative to the massing repo root
DEST = Path(__file__).resolve().parents[1] / "services" / "data" / "families" / "external"


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "massing-fetch-families"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def release(tag: str | None) -> dict:
    url = f"{API}/tags/{tag}" if tag else f"{API}/latest"
    try:
        return json.loads(_get(url))
    except Exception as e:                                  # noqa: BLE001
        raise SystemExit(f"could not fetch release {tag or 'latest'} from {REPO}: {e}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tag", help="release tag (default: latest)")
    ap.add_argument("--packs", nargs="*", help="pack names to fetch (default: all)")
    ap.add_argument("--dest", type=Path, default=DEST)
    ap.add_argument("--list", action="store_true", help="list packs in the release and exit")
    args = ap.parse_args(argv)

    rel = release(args.tag)
    assets = {a["name"]: a["browser_download_url"] for a in rel.get("assets", [])}
    if "manifest.json" not in assets:
        raise SystemExit(f"release {rel.get('tag_name')} has no manifest.json — cannot verify packs")

    manifest = json.loads(_get(assets["manifest.json"]))
    packs = manifest["packs"]

    if args.list:
        print(f"{REPO} {rel['tag_name']} — {manifest['totals']['families']} families, "
              f"{manifest['totals']['types']} types")
        for p in sorted(packs, key=lambda x: x["discipline"]):
            print(f"  {p['discipline']:34} {p['families']:>3}f {p['types']:>5}t  "
                  f"{p['size_bytes'] / 1e6:>5.1f} MB")
        return 0

    wanted = set(args.packs) if args.packs else None
    selected = [p for p in packs if wanted is None or p["discipline"] in wanted]
    if wanted:
        missing = wanted - {p["discipline"] for p in packs}
        if missing:
            raise SystemExit(f"no such pack(s): {sorted(missing)}. Use --list to see options.")

    args.dest.mkdir(parents=True, exist_ok=True)
    total = 0
    for pack in selected:
        url = assets.get(pack["file"])
        if not url:
            print(f"  SKIP {pack['file']} — not attached to the release", file=sys.stderr)
            continue
        data = _get(url)
        digest = hashlib.sha256(data).hexdigest()
        if digest != pack["sha256"]:
            raise SystemExit(f"checksum mismatch for {pack['file']}:\n"
                             f"  expected {pack['sha256']}\n  got      {digest}")
        (args.dest / pack["file"]).write_bytes(data)
        total += pack["types"]
        print(f"  {pack['file']:56} {pack['types']:>5} types  ok")

    (args.dest / "manifest.json").write_bytes(json.dumps(manifest, indent=2).encode())
    print(f"\n{len(selected)} pack(s), {total} types -> {args.dest}")
    print("Import into a project with POST /projects/{id}/families/import, or browse "
          "via GET /families/library.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
