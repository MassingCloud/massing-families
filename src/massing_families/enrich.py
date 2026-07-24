"""Data richness — psets, provenance, materials, classification, quantities.

This is the layer that differentiates the library from a pretty box in SketchUp. Verified in PLAN.md §4:
all of it survives massing's `import_types_from_ifc` (which routes through `project.append_asset`), so
content authored here arrives in a user's project fully intact.

Kept as one module because these are four small facets of a single concern — "make the type carry real
data" — and splitting them into four ~30-line files would cost more in indirection than it buys.
"""
from __future__ import annotations

from typing import Any

import ifcopenshell
import ifcopenshell.api

from .units import metres

PROVENANCE_PSET = "MF_Library"

# classification system -> (IfcClassification Name, Edition, Source)
SYSTEMS = {
    "uniclass": ("Uniclass", "2015", "NBS"),
    "omniclass": ("OmniClass", "2012", "CSI"),
    "masterformat": ("MasterFormat", "2020", "CSI"),
}


def apply_psets(model: ifcopenshell.file, product, psets: dict[str, dict]) -> None:
    """Attach type-level property sets. `pset.add_pset` is find-or-create, so re-applying edits
    rather than duplicating — same semantics as massing's `_apply_psets`."""
    for name, props in (psets or {}).items():
        if not props:
            continue
        pset = ifcopenshell.api.run("pset.add_pset", model, product=product, name=str(name))
        ifcopenshell.api.run("pset.edit_pset", model, pset=pset,
                             properties={str(k): v for k, v in props.items()})


# What the geometry actually is, derived from the builder rather than hand-set per family.
# PLAN.md §8g: a dimensionally-correct box is a legitimate deliverable, but it must be *labelled* as a
# proxy and never passed off as detailed content. Deriving this means it can never drift out of date.
GEOMETRY_STATUS = {
    "box": "proxy",              # correct bounding dimensions, no detail
    "profile": "parametric",     # real swept section
    "swept_disk": "parametric",
    "revolve": "parametric",
    "boolean": "parametric",
    "taper": "parametric",
    "assembly": "assembly",      # multi-part positioned solids
    "mesh": "tessellated",       # faceted; typically imported rather than fabricated
}


def geometry_status(spec) -> str:
    return GEOMETRY_STATUS.get(spec.builder, "unknown")


def apply_provenance(model: ifcopenshell.file, product, spec, variant, version: str) -> None:
    """Stamp every type with where it came from and what may be done with it.

    This is also the collision-safe identity massing's `(ifc_class, Name)` dedup lacks (PLAN.md §5):
    `MF_Library.Key` uniquely identifies a family across vendors even if two libraries pick the same
    display name.
    """
    props = {
        "Key": spec.key,
        "Family": spec.label,
        "TypeName": variant.name,
        "Version": version,
        "License": spec.license,
        "Source": spec.source,
        "Tier": spec.tier,
        "Builder": spec.builder,
        "Discipline": spec.discipline,
        "GeometryStatus": geometry_status(spec),
    }
    if spec.massing_key:
        props["MassingKey"] = spec.massing_key
    apply_psets(model, product, {PROVENANCE_PSET: props})


def apply_material(model: ifcopenshell.file, product, material: dict[str, Any] | None) -> None:
    """Assign either a single IfcMaterial (`name:`) or an ordered IfcMaterialLayerSet (`layers:`).

    Layer thicknesses are imperial like everything else — `5/8"` gypsum, `3 5/8"` stud.
    """
    if not material:
        return
    if material.get("layers"):
        mset = ifcopenshell.api.run("material.add_material_set", model,
                                    name=material.get("name") or "Assembly",
                                    set_type="IfcMaterialLayerSet")
        for layer in material["layers"]:
            mname = str(layer.get("material") or "Material")
            mat = _find_or_add_material(model, mname, layer.get("category"))
            lyr = ifcopenshell.api.run("material.add_layer", model, layer_set=mset, material=mat)
            ifcopenshell.api.run("material.edit_layer", model, layer=lyr, attributes={
                "LayerThickness": metres(layer.get("thickness", "1\"")), "Name": mname})
        ifcopenshell.api.run("material.assign_material", model, products=[product],
                             type="IfcMaterialLayerSet", material=mset)
        return
    mat = _find_or_add_material(model, str(material.get("name") or "Material"),
                               material.get("category"))
    ifcopenshell.api.run("material.assign_material", model, products=[product],
                         type="IfcMaterial", material=mat)


def _find_or_add_material(model: ifcopenshell.file, name: str, category: str | None = None):
    existing = next((m for m in model.by_type("IfcMaterial") if m.Name == name), None)
    if existing is not None:
        return existing
    mat = ifcopenshell.api.run("material.add_material", model, name=name)
    if category and hasattr(mat, "Category"):
        mat.Category = str(category)
    return mat


def _find_or_add_classification(model: ifcopenshell.file, system: str):
    name, edition, source = SYSTEMS[system]
    existing = next((c for c in model.by_type("IfcClassification") if c.Name == name), None)
    if existing is not None:
        return existing
    cls = ifcopenshell.api.run("classification.add_classification", model, classification=name)
    for attr, val in (("Edition", edition), ("Source", source)):
        if hasattr(cls, attr):
            setattr(cls, attr, val)
    return cls


def apply_classification(model: ifcopenshell.file, product, classification: dict[str, str]) -> None:
    """Attach IfcClassificationReference codes (Uniclass / OmniClass / MasterFormat).

    MasterFormat is licensed by CSI — we support the field so a deployment can supply its own mapping,
    but ship no MasterFormat codes ourselves (PLAN.md §6.3).
    """
    for system, code in (classification or {}).items():
        if not code:
            continue
        if system not in SYSTEMS:
            raise ValueError(f"unknown classification system {system!r}; have {sorted(SYSTEMS)}")
        cls = _find_or_add_classification(model, system)
        ifcopenshell.api.run("classification.add_reference", model, products=[product],
                             identification=str(code), name=SYSTEMS[system][0],
                             classification=cls)


PORT_SYSTEMS = {"CABLE", "CABLECARRIER", "DUCT", "PIPE", "OTHER", "NOTDEFINED", "USERDEFINED"}


def apply_ports(model: ifcopenshell.file, product, ports: dict | None) -> None:
    """Attach IfcDistributionPorts so massing's port-to-port MEP connectivity works.

    Verified by the Phase 3 spike: `nest.assign_object` attaches ports to a *type* via IfcRelNests, and
    both the ports and their FlowDirection survive `project.append_asset` — i.e. they arrive intact
    through massing's import. This was the unverified assumption gating all routing content
    (PLAN.md §8f); it holds.
    """
    if not ports:
        return
    system = str(ports.get("system", "NOTDEFINED")).upper()
    if system not in PORT_SYSTEMS:
        raise ValueError(f"unknown port system {system!r}; have {sorted(PORT_SYSTEMS)}")
    names = ports.get("names") or ["In", "Out"]
    flows = ports.get("flows") or ["SOURCE", "SINK"]
    if len(names) != len(flows):
        raise ValueError("port names and flows must be the same length")

    created = []
    for name, flow in zip(names, flows):
        p = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcDistributionPort",
                                 name=str(name))
        if hasattr(p, "PredefinedType"):
            p.PredefinedType = system
        if hasattr(p, "FlowDirection"):
            p.FlowDirection = str(flow).upper()
        created.append(p)
    ifcopenshell.api.run("nest.assign_object", model, related_objects=created,
                         relating_object=product)


def apply_quantities(model: ifcopenshell.file, product, dims_m: list[float] | None) -> None:
    """Nominal bounding quantities for takeoff/scheduling.

    Deliberately labelled `Nominal*` on a `Qto_` -style set: these are the type's bounding box, not a
    tessellated volume, and calling them anything else would overstate their accuracy.
    """
    if not dims_m:
        return
    w, d, h = dims_m
    apply_psets(model, product, {"MF_Quantities": {
        "NominalWidth": round(w, 6),
        "NominalDepth": round(d, 6),
        "NominalHeight": round(h, 6),
        "NominalFootprintArea": round(w * d, 6),
        "NominalVolume": round(w * d * h, 6),
    }})
