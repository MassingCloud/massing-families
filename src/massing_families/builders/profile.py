"""L300 real geometry — parameterized profile sweeps.

This is the tier that ends "everything is a box". IFC4 ships 23 profile definitions and massing
currently uses exactly one (`IfcRectangleProfileDef`); this builder exposes the parametric family of
them, so a steel column is an actual W-shape with web and flange thicknesses rather than a 12" cube.

Which parameters get unit-scaled is decided by **the IFC schema itself**: an attribute whose underlying
measure type is a length is scaled into file units, everything else (LegSlope, FlangeSlope — plane
angles) passes through untouched. That way adding a new profile kind needs no scaling table.
"""
from __future__ import annotations

import ifcopenshell

from .. import ifc
from ..units import metres

_wrap = ifcopenshell.ifcopenshell_wrapper
_SCHEMA = _wrap.schema_by_name("IFC4")

# spec `kind:` -> IFC entity. Names kept short and drawing-familiar.
KINDS = {
    "Rectangle": "IfcRectangleProfileDef",
    "RectangleHollow": "IfcRectangleHollowProfileDef",
    "RoundedRectangle": "IfcRoundedRectangleProfileDef",
    "Circle": "IfcCircleProfileDef",
    "CircleHollow": "IfcCircleHollowProfileDef",
    "Ellipse": "IfcEllipseProfileDef",
    "IShape": "IfcIShapeProfileDef",
    "AsymmetricIShape": "IfcAsymmetricIShapeProfileDef",
    "LShape": "IfcLShapeProfileDef",
    "TShape": "IfcTShapeProfileDef",
    "UShape": "IfcUShapeProfileDef",
    "CShape": "IfcCShapeProfileDef",
    "ZShape": "IfcZShapeProfileDef",
    "Trapezium": "IfcTrapeziumProfileDef",
}


def _length_attrs(entity_name: str) -> set[str]:
    """Attribute names on a profile entity whose measure type is a length (so they need scaling).

    The type chain is walked and tested at *every* level — IfcPositiveLengthMeasure unwraps to
    IfcLengthMeasure and then to a bare `real`, so only checking the innermost type would find nothing
    and silently leave every parameter unscaled.
    """
    decl = _SCHEMA.declaration_by_name(entity_name)
    out = set()
    for attr in decl.all_attributes():
        t = attr.type_of_attribute()
        for _ in range(12):
            if "Length" in str(getattr(t, "name", lambda: "")()):
                out.add(attr.name())
                break
            if not hasattr(t, "declared_type"):
                break
            t = t.declared_type()
    return out


def _valid_attrs(entity_name: str) -> set[str]:
    return {a.name() for a in _SCHEMA.declaration_by_name(entity_name).all_attributes()}


def build_profile_entity(model, spec, variant, pdef: dict, name: str | None = None):
    """Create the IFC profile entity for a profile definition.

    Shared with the revolve, boolean and taper builders, which all need a profile but sweep it
    differently — so profile construction (and its validation) lives in one place.
    """
    kind = pdef.get("kind")
    entity = KINDS.get(kind)
    if entity is None:
        raise ValueError(f"family {spec.key!r}: unknown profile kind {kind!r}; "
                         f"have {sorted(KINDS)}")

    params = dict(pdef.get("params") or {})
    valid = _valid_attrs(entity)
    unknown = set(params) - valid
    if unknown:
        raise ValueError(f"family {spec.key!r}: {entity} has no attribute(s) {sorted(unknown)}; "
                         f"valid: {sorted(valid - {'ProfileType', 'ProfileName', 'Position'})}")

    lengths = _length_attrs(entity)
    attrs = {}
    for attr, raw in params.items():
        if raw is None:
            continue
        val = metres(raw) if attr in lengths else float(raw)
        attrs[attr] = ifc.scaled(model, val) if attr in lengths else val

    return model.create_entity(entity, ProfileType="AREA",
                               ProfileName=pdef.get("name") or name or variant.name,
                               Position=ifc.placement2d(model), **attrs)


def build(model, spec, variant):
    """Build a swept solid from the spec/variant profile definition."""
    pdef = {**(spec.profile or {}), **(variant.profile or {})}
    if not pdef:
        return None
    prof = build_profile_entity(model, spec, variant, pdef)

    # sweep length: explicit `depth:`, else the variant's height (dims[2])
    depth = pdef.get("depth")
    depth_m = metres(depth) if depth is not None else None
    if depth_m is None:
        dims = variant.dims_metres or spec.dims_metres
        depth_m = dims[2] if dims else None
    if not depth_m or depth_m <= 0:
        raise ValueError(f"family {spec.key!r} type {variant.name!r}: profile sweep needs a positive "
                         f"depth (set profile.depth or dims[2])")
    return ifc.extrude(model, prof, depth_m)
