"""Pack emitter — turns specs into shippable, versioned IFC4 library files.

Packs are **discipline-scoped, never monolithic**. This is a hard constraint, not a preference:
massing's `import_types_from_ifc` imports *every* IfcTypeProduct in the file it is given, so a single
5,000-type library would flood a user's project with content they never asked for (PLAN.md §3).

Each pack ships with a manifest entry carrying counts, categories, licences and a sha256, so the
platform can present a real browsable catalog instead of `GET /families/library`'s current
filename-plus-size listing.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import ifcopenshell
import ifcopenshell.api

from . import enrich, ifc
from .builders import build_geometry
from .generators import expand
from .spec import FamilySpec

LIBRARY_NAME = "massing-families"


def build_type(model: ifcopenshell.file, spec: FamilySpec, variant, version: str):
    """Create one fully-enriched IfcTypeProduct: geometry + psets + provenance + material +
    classification + quantities."""
    name = spec.type_name(variant)
    typ = ifcopenshell.api.run("root.create_entity", model, ifc_class=spec.ifc_class, name=name)
    if spec.predefined and hasattr(typ, "PredefinedType"):
        typ.PredefinedType = spec.predefined

    rep = build_geometry(model, spec, variant)
    if rep is not None:
        ifc.clear_representations(model, typ)   # never append a second map — see PLAN.md §5
        ifc.assign(model, typ, rep)

    enrich.apply_psets(model, typ, {**spec.psets, **variant.psets})
    enrich.apply_provenance(model, typ, spec, variant, version)
    enrich.apply_material(model, typ, spec.material)
    enrich.apply_classification(model, typ, spec.classification)
    enrich.apply_quantities(model, typ, variant.dims_metres or spec.dims_metres)
    enrich.apply_ports(model, typ, spec.ports)
    return typ


def build_model(specs: list[FamilySpec], version: str, name: str = "Massing Family Library"):
    """Build every spec's catalogued types into one IFC model. Returns (model, stats)."""
    model = ifc.new_library(name)
    families = 0
    types = 0
    for spec in specs:
        variants = expand(spec)
        if not variants:
            continue
        families += 1
        for variant in variants:
            build_type(model, spec, variant, version)
            types += 1
    stats = {
        "families": families,
        "types": types,
        "categories": sorted({s.category for s in specs}),
        "disciplines": sorted({s.discipline for s in specs}),
        "licenses": sorted({s.license for s in specs}),
        "tiers": sorted({s.tier for s in specs}),
    }
    return model, stats


def write_pack(specs: list[FamilySpec], out_dir: Path, discipline: str, version: str) -> dict:
    """Write one discipline-scoped pack and return its manifest entry."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{LIBRARY_NAME}-{discipline}-v{version}.ifc"
    path = out_dir / filename

    model, stats = build_model(specs, version, name=f"Massing Family Library — {discipline}")
    model.write(str(path))

    data = path.read_bytes()
    return {
        "file": filename,
        "discipline": discipline,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "ifc_schema": ifc.SCHEMA,
        **stats,
        "families": stats["families"],
        "index": _family_index(specs),
    }


def _family_index(specs: list[FamilySpec]) -> list[dict]:
    """Per-family metadata for the picker.

    `GET /families/library` currently returns filename and size only (PLAN.md §10 Phase 7); this is the
    data a browsable, searchable, classification-filtered catalog needs, published alongside the packs
    so the UI work needs no new build step.
    """
    out = []
    for spec in sorted(specs, key=lambda s: (s.category, s.label)):
        variants = expand(spec)
        out.append({
            "key": spec.key,
            "label": spec.label,
            "category": spec.category,
            "discipline": spec.discipline,
            "ifc_class": spec.ifc_class,
            "predefined": spec.predefined,
            "tier": spec.tier,
            "geometry": enrich.geometry_status(spec),
            "classification": spec.classification,
            "license": spec.license,
            "massing_key": spec.massing_key,
            "has_ports": bool(spec.ports),
            "type_count": len(variants),
            "types": [spec.type_name(v) for v in variants[:50]],
        })
    return out


def write_manifest(entries: list[dict], out_dir: Path, version: str) -> Path:
    """The sidecar that makes the catalog browsable — counts, categories, licences, checksums."""
    out_dir = Path(out_dir)
    manifest = {
        "library": LIBRARY_NAME,
        "version": version,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ifc_schema": ifc.SCHEMA,
        "units": {"authored": "US imperial nominal", "stored": "metres (exact)"},
        "totals": {
            "packs": len(entries),
            "families": sum(e["families"] for e in entries),
            "types": sum(e["types"] for e in entries),
            "size_bytes": sum(e["size_bytes"] for e in entries),
        },
        "packs": entries,
    }
    path = out_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path
