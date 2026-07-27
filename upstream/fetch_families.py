"""Fetch the family library into a massing deployment.

Vendor this into massing as `scripts/fetch_families.py`. It downloads a tagged release of
`MassingCloud/massing-families` into `services/data/families/external/`, where `GET /families/library`
already lists it and `POST /projects/{id}/families/import` can pull types from it.

    python scripts/fetch_families.py --list
    python scripts/fetch_families.py                 # latest release, all packs
    python scripts/fetch_families.py --tag v0.1.1
    python scripts/fetch_families.py --packs structural-steel-w mechanical-ductwork

**Authentication.** The library repo is public, so no token is needed. If one is available the script
still uses it — `--token`, `$GITHUB_TOKEN`, `$GH_TOKEN`, then `gh auth token` — which raises the API
rate limit and keeps the script working if the repo is ever made private again. Assets are fetched
from the *API* asset URL with `Accept: application/octet-stream` rather than `browser_download_url`,
because that is the form that works in both cases.

Why fetch rather than commit: massing's .gitignore treats `*.ifc` as a build artifact ("data /
artifacts (do NOT commit models or tiles)"), and the library is ~6 MB across 40 packs that regenerate
on every catalog change. Packs ship as release assets with a sha256 per pack in `manifest.json`, which
this script verifies before writing anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "MassingCloud/massing-families"
API = f"https://api.github.com/repos/{REPO}/releases"
# services/data/families/external/ relative to the massing repo root
DEST = Path(__file__).resolve().parents[1] / "services" / "data" / "families" / "external"


def find_token(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    if shutil.which("gh"):
        try:
            out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True,
                                 timeout=15)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except Exception:                                   # noqa: BLE001
            pass
    return None


def _get(url: str, token: str | None, octet: bool = False) -> bytes:
    headers = {"User-Agent": "massing-fetch-families",
               "Accept": "application/octet-stream" if octet else "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403) and not token:
            raise SystemExit(
                f"HTTP {e.code} fetching {url}\n"
                f"Most likely the anonymous API rate limit. Set GITHUB_TOKEN, run `gh auth login`, "
                f"or pass --token.")
        raise SystemExit(f"HTTP {e.code} fetching {url}: {e.reason}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tag", help="release tag (default: latest)")
    ap.add_argument("--packs", nargs="*", help="pack names to fetch (default: all)")
    ap.add_argument("--dest", type=Path, default=DEST)
    ap.add_argument("--token", help="GitHub token (default: $GITHUB_TOKEN / $GH_TOKEN / gh CLI)")
    ap.add_argument("--list", action="store_true", help="list packs in the release and exit")
    args = ap.parse_args(argv)

    token = find_token(args.token)
    rel = json.loads(_get(f"{API}/tags/{args.tag}" if args.tag else f"{API}/latest", token))

    # the API asset url, not browser_download_url — this form works whether the repo is public or
    # private, so the script keeps working if visibility ever changes
    assets = {a["name"]: a["url"] for a in rel.get("assets", [])}
    if "manifest.json" not in assets:
        raise SystemExit(f"release {rel.get('tag_name')} has no manifest.json — cannot verify packs")
    manifest = json.loads(_get(assets["manifest.json"], token, octet=True))
    packs = manifest["packs"]

    if args.list:
        t = manifest["totals"]
        print(f"{REPO} {rel['tag_name']} — {t['families']} families, {t['types']} types, "
              f"{t['size_bytes'] / 1e6:.1f} MB")
        for p in sorted(packs, key=lambda x: x["discipline"]):
            print(f"  {p['discipline']:34} {p['families']:>3}f {p['types']:>5}t  "
                  f"{p['size_bytes'] / 1e6:>5.2f} MB")
        return 0

    wanted = set(args.packs) if args.packs else None
    if wanted:
        missing = wanted - {p["discipline"] for p in packs}
        if missing:
            raise SystemExit(f"no such pack(s): {sorted(missing)}. Use --list to see options.")
    selected = [p for p in packs if wanted is None or p["discipline"] in wanted]

    args.dest.mkdir(parents=True, exist_ok=True)
    total = 0
    for pack in selected:
        url = assets.get(pack["file"])
        if not url:
            print(f"  SKIP {pack['file']} — not attached to the release", file=sys.stderr)
            continue
        data = _get(url, token, octet=True)
        digest = hashlib.sha256(data).hexdigest()
        if digest != pack["sha256"]:
            raise SystemExit(f"checksum mismatch for {pack['file']}:\n"
                             f"  expected {pack['sha256']}\n  got      {digest}")
        (args.dest / pack["file"]).write_bytes(data)
        total += pack["types"]
        print(f"  {pack['file']:56} {pack['types']:>5} types  ok")

    (args.dest / "manifest.json").write_bytes(json.dumps(manifest, indent=2).encode())
    print(f"\n{len(selected)} pack(s), {total} types -> {args.dest}")
    print("Browse via GET /families/library; import with "
          "POST /projects/{id}/families/import.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
