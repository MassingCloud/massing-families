"""Generate the browsable catalog site.

`docs/CATALOG.md` is a reference — fine to search with ctrl-F, useless for "show me every L300
structural family with ports". 419 families across 111 categories needs filtering.

Rendered from the catalog like everything else, so it cannot drift: `cli site` regenerates it and
`tests/test_site.py` fails the build if it is stale. Self-contained — no CDN, no build step, no
JavaScript dependencies — because a page that stops working when a CDN changes is worse than a table.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .enrich import geometry_status
from .generators import expand
from .spec import TYPE_CLASSES, FamilySpec

REPO = "https://github.com/MassingCloud/massing-families"

_CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--muted:#666;--line:#e3e3e3;--accent:#0b5;--chip:#f4f4f5;--card:#fafafa}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#111316;--fg:#e8e8ea;--muted:#9a9aa2;
--line:#2a2d33;--accent:#3ddc84;--chip:#1c1f24;--card:#16181c}}
:root[data-theme=dark]{--bg:#111316;--fg:#e8e8ea;--muted:#9a9aa2;--line:#2a2d33;--accent:#3ddc84;
--chip:#1c1f24;--card:#16181c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,
"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:2rem 1.25rem 4rem}
h1{font-size:1.7rem;margin:0 0 .35rem}
.sub{color:var(--muted);margin:0 0 1.25rem}
.stats{display:flex;flex-wrap:wrap;gap:.5rem;margin:0 0 1.5rem}
.stat{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:.5rem .8rem}
.stat b{display:block;font-size:1.25rem}
.stat span{color:var(--muted);font-size:.8rem}
.controls{display:flex;flex-wrap:wrap;gap:.6rem;margin-bottom:1rem;position:sticky;top:0;
background:var(--bg);padding:.75rem 0;border-bottom:1px solid var(--line);z-index:5}
input,select{background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:7px;
padding:.5rem .65rem;font:inherit}
input{flex:1 1 260px}
.count{color:var(--muted);align-self:center;font-size:.85rem;white-space:nowrap}
.tablewrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th{text-align:left;font-weight:600;color:var(--muted);border-bottom:1px solid var(--line);
padding:.5rem .6rem;white-space:nowrap;font-size:.8rem;text-transform:uppercase;letter-spacing:.04em}
td{border-bottom:1px solid var(--line);padding:.55rem .6rem;vertical-align:top}
tr:hover td{background:var(--card)}
.name{font-weight:600}
.key{color:var(--muted);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.8rem}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.82rem}
.chip{display:inline-block;background:var(--chip);border:1px solid var(--line);border-radius:20px;
padding:.1rem .5rem;font-size:.75rem;white-space:nowrap}
.chip.parametric{border-color:var(--accent);color:var(--accent)}
.num{text-align:right;font-variant-numeric:tabular-nums}
details summary{cursor:pointer;color:var(--muted);font-size:.8rem}
details ul{margin:.4rem 0 0;padding-left:1.1rem;color:var(--muted);font-size:.8rem}
a{color:var(--accent)}
.empty{padding:2rem;text-align:center;color:var(--muted)}
footer{margin-top:2.5rem;padding-top:1.25rem;border-top:1px solid var(--line);color:var(--muted);
font-size:.85rem}
"""

_JS = """
const rows=[...document.querySelectorAll('tbody tr')];
const q=document.getElementById('q'),d=document.getElementById('d'),
      t=document.getElementById('t'),g=document.getElementById('g'),
      c=document.getElementById('count'),empty=document.getElementById('empty');
function apply(){
  const s=q.value.toLowerCase().trim();
  let n=0;
  for(const r of rows){
    const ok=(!s||r.dataset.search.includes(s))
      &&(!d.value||r.dataset.discipline===d.value)
      &&(!t.value||r.dataset.tier===t.value)
      &&(!g.value||r.dataset.geometry===g.value);
    r.hidden=!ok; if(ok)n++;
  }
  c.textContent=n+' of '+rows.length+' families';
  empty.hidden=n>0;
}
[q,d,t,g].forEach(e=>e.addEventListener('input',apply));
apply();
"""


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def render(specs: list[FamilySpec], version: str) -> str:
    rows = []
    for spec in sorted(specs, key=lambda s: (s.discipline, s.category, s.label)):
        variants = expand(spec)
        names = [spec.type_name(v) for v in variants]
        status = geometry_status(spec)
        search = " ".join([spec.key, spec.label, spec.category, spec.discipline, spec.ifc_class,
                           spec.classification.get("uniclass", ""), *names[:40]]).lower()
        types_cell = (f'<details><summary>{len(names)} type'
                      f'{"s" if len(names) != 1 else ""}</summary><ul>'
                      + "".join(f"<li>{_esc(n)}</li>" for n in names[:40])
                      + (f"<li>… {len(names) - 40} more</li>" if len(names) > 40 else "")
                      + "</ul></details>")
        rows.append(
            f'<tr data-search="{_esc(search)}" data-discipline="{_esc(spec.discipline)}" '
            f'data-tier="{_esc(spec.tier)}" data-geometry="{_esc(status)}">'
            f'<td><div class="name">{_esc(spec.label)}</div>'
            f'<div class="key">{_esc(spec.key)}</div></td>'
            f'<td>{_esc(spec.discipline)}<br><span class="key">{_esc(spec.category)}</span></td>'
            f'<td><code>{_esc(spec.ifc_class)}</code></td>'
            f'<td><span class="chip">{_esc(spec.tier)}</span></td>'
            f'<td><span class="chip {status}">{_esc(status)}</span></td>'
            f'<td class="num">{types_cell}</td>'
            f'<td><code>{_esc(spec.classification.get("uniclass", "—"))}</code></td>'
            f'<td>{"✓" if spec.ports else ""}</td></tr>')

    total_types = sum(len(expand(s)) for s in specs)
    tiers = sorted({s.tier for s in specs})
    disciplines = sorted({s.discipline for s in specs})
    statuses = sorted({geometry_status(s) for s in specs})
    proxies = sum(1 for s in specs if s.builder == "box")

    def opts(values, label):
        return (f'<option value="">{label}</option>'
                + "".join(f'<option>{_esc(v)}</option>' for v in values))

    return f"""<title>massing-families — catalog</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Browsable catalog of the massing-families openBIM library — \
{len(specs)} IFC4 families, {total_types} types, CC0.">
<style>{_CSS}</style>
<div class="wrap">
<h1>massing-families</h1>
<p class="sub">An openBIM family library you can actually redistribute. Generated parametrically from
public standards — <strong>CC0</strong>. <a href="{REPO}">Source</a> ·
<a href="{REPO}/releases">Releases</a> · <a href="{REPO}/blob/main/docs/GUIDE.md">Guide</a> ·
<a href="{REPO}/blob/main/CONTRIBUTING.md">Contributing</a></p>

<div class="stats">
  <div class="stat"><b>{len(specs)}</b><span>families</span></div>
  <div class="stat"><b>{total_types:,}</b><span>types</span></div>
  <div class="stat"><b>{len({s.pack_name for s in specs})}</b><span>packs</span></div>
  <div class="stat"><b>{len({s.ifc_class for s in specs})} / {len(TYPE_CLASSES)}</b>
    <span>IFC4 type classes</span></div>
  <div class="stat"><b>{len(specs) - proxies}</b><span>real geometry</span></div>
  <div class="stat"><b>{sum(1 for s in specs if s.ports)}</b><span>with ports</span></div>
</div>

<div class="controls">
  <input id="q" type="search" placeholder="Search families, types, classes, Uniclass codes…"
         aria-label="Search">
  <select id="d" aria-label="Discipline">{opts(disciplines, "All disciplines")}</select>
  <select id="t" aria-label="Tier">{opts(tiers, "All tiers")}</select>
  <select id="g" aria-label="Geometry">{opts(statuses, "All geometry")}</select>
  <span class="count" id="count"></span>
</div>

<div class="tablewrap">
<table>
<thead><tr><th>Family</th><th>Discipline</th><th>IFC class</th><th>Tier</th><th>Geometry</th>
<th>Types</th><th>Uniclass</th><th>Ports</th></tr></thead>
<tbody>{"".join(rows)}</tbody>
</table>
</div>
<p class="empty" id="empty" hidden>Nothing matches those filters.</p>

<footer>
<p><strong>Geometry:</strong> <code>proxy</code> is a box with correct bounding dimensions and no
detail — right for a chiller cabinet, not for a wall section. <code>parametric</code> is a real swept
solid. The value is derived from the builder, never hand-set, so it cannot overstate.</p>
<p><strong>Licence:</strong> content CC0-1.0, generator MIT. The declaration travels with the
content — in every type's <code>MF_Library</code> pset, each pack's STEP header, and
<code>manifest.json</code>. Derived reference data has its own provenance in
<a href="{REPO}/blob/main/NOTICE.md">NOTICE.md</a>.</p>
<p>Generated from the catalog at v{_esc(version)} — this page is built by
<code>massing_families.cli site</code> and a test fails the build if it goes stale.</p>
</footer>
</div>
<script>{_JS}</script>
"""


def write(specs: list[FamilySpec], root: Path, version: str) -> Path:
    path = Path(root) / "site" / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(specs, version), encoding="utf-8")
    (path.parent / ".nojekyll").write_text("", encoding="utf-8")
    return path
