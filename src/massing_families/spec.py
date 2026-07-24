"""Declarative family specs — the catalog's source of truth.

A spec is data, not code: adding a family is a YAML edit. Each spec declares an IFC type class, a
geometry `builder` + tier, and its named catalog types in **imperial nominals** (PLAN.md §7b).

Validation runs against the real IFC4 schema via IfcOpenShell rather than a hand-maintained list, so a
typo like `IfcDoorTyp` or a class that doesn't exist in IFC4 fails at build time instead of producing a
silently broken pack.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import ifcopenshell
import yaml

from .units import UnitError, dims_m

TIERS = {"L200", "L300", "L350"}
_wrap = ifcopenshell.ifcopenshell_wrapper
_SCHEMA = _wrap.schema_by_name("IFC4")


class SpecError(ValueError):
    """A malformed family spec."""


def _type_classes() -> set[str]:
    """Every concrete IfcTypeProduct subclass in IFC4 (125 of them)."""
    out = set()
    for decl in _SCHEMA.declarations():
        if not isinstance(decl, _wrap.entity):
            continue
        p = decl
        while p is not None:
            if p.name() == "IfcTypeProduct":
                out.add(decl.name())
                break
            p = p.supertype()
    return out


TYPE_CLASSES = _type_classes()


def predefined_values(ifc_class: str) -> set[str]:
    """Legal PredefinedType enum values for a type class, straight from the schema."""
    try:
        decl = _SCHEMA.declaration_by_name(ifc_class)
    except Exception:
        return set()
    for attr in decl.all_attributes():
        if attr.name() != "PredefinedType":
            continue
        t = attr.type_of_attribute()
        while hasattr(t, "declared_type"):
            t = t.declared_type()
        if isinstance(t, _wrap.enumeration_type):
            return set(t.enumeration_items())
    return set()


@dataclass
class TypeVariant:
    """One named, catalogued size — the Revit "one family, many types" model."""
    name: str                                  # imperial designation, e.g. '3\'-0" x 7\'-0"'
    dims: list[str | float] | None = None       # imperial [w, d, h]
    profile: dict[str, Any] | None = None       # per-variant profile params (steel shapes)
    swept_disk: dict[str, Any] | None = None    # per-variant swept-disk params (bar sizes)
    revolve: dict[str, Any] | None = None
    boolean: dict[str, Any] | None = None
    taper: dict[str, Any] | None = None
    assembly: dict[str, Any] | None = None
    mesh: dict[str, Any] | None = None
    psets: dict[str, dict] = field(default_factory=dict)

    @property
    def dims_metres(self) -> list[float] | None:
        return dims_m(self.dims) if self.dims else None


@dataclass
class FamilySpec:
    key: str
    label: str
    ifc_class: str
    category: str
    discipline: str
    builder: str = "box"
    tier: str = "L200"
    predefined: str | None = None
    dims: list[str | float] | None = None       # default/base size, imperial
    profile: dict[str, Any] | None = None
    swept_disk: dict[str, Any] | None = None    # circular section swept along a path (rebar, rails)
    revolve: dict[str, Any] | None = None       # profile revolved about an axis (tanks, domes)
    boolean: dict[str, Any] | None = None       # base solid minus voids (vision panels, basins)
    taper: dict[str, Any] | None = None         # tapered extrusion (duct transitions, reducers)
    assembly: dict[str, Any] | None = None      # multi-part solid (stairs, trusses, headwalls)
    mesh: dict[str, Any] | None = None          # tessellated faces — the import landing format
    types: list[TypeVariant] = field(default_factory=list)
    psets: dict[str, dict] = field(default_factory=dict)
    material: dict[str, Any] | None = None
    classification: dict[str, str] = field(default_factory=dict)
    ports: dict[str, Any] | None = None         # IfcDistributionPort config for routing content
    license: str = "CC0-1.0"
    source: str = "massing-families"
    generator: str | None = None                # e.g. 'aisc' — expands types from a data table
    generator_args: dict[str, Any] = field(default_factory=dict)
    massing_key: str | None = None              # the equivalent key in massing's built-in CATALOG,
                                                # so a pack can eventually replace it upstream
    pack: str | None = None                     # sub-discipline pack override. A generated family can
                                                # produce hundreds of types, and import pulls in *every*
                                                # type in a file (§3) — so 'structural' splits into
                                                # 'structural-steel-w', 'structural-steel-hss', etc.

    @property
    def pack_name(self) -> str:
        return self.pack or self.discipline

    # ---- naming -------------------------------------------------------------
    def type_name(self, variant: TypeVariant) -> str:
        """The schedule-facing type name. Imperial, because names are what appear on drawings and in
        the picker. Also the dedup identity massing uses — see PLAN.md §5."""
        return f"{self.label} - {variant.name}"

    @property
    def dims_metres(self) -> list[float] | None:
        return dims_m(self.dims) if self.dims else None

    # ---- construction / validation ------------------------------------------
    @classmethod
    def from_dict(cls, raw: dict, origin: str = "<dict>") -> "FamilySpec":
        unknown = set(raw) - set(cls.__dataclass_fields__)
        if unknown:
            raise SpecError(f"{origin}: unknown spec field(s) {sorted(unknown)}")
        for req in ("key", "label", "ifc_class", "category", "discipline"):
            if not raw.get(req):
                raise SpecError(f"{origin}: missing required field {req!r}")
        variants = [TypeVariant(**v) if isinstance(v, dict) else TypeVariant(name=str(v))
                    for v in raw.get("types", [])]
        data = {k: v for k, v in raw.items() if k != "types"}
        spec = cls(**data, types=variants)
        spec.validate(origin)
        return spec

    def validate(self, origin: str = "<spec>") -> None:
        if self.ifc_class not in TYPE_CLASSES:
            raise SpecError(f"{origin}: {self.ifc_class!r} is not an IFC4 IfcTypeProduct subclass")
        if self.tier not in TIERS:
            raise SpecError(f"{origin}: tier must be one of {sorted(TIERS)}, got {self.tier!r}")
        if self.predefined:
            legal = predefined_values(self.ifc_class)
            if legal and self.predefined not in legal:
                raise SpecError(f"{origin}: PredefinedType {self.predefined!r} invalid for "
                                f"{self.ifc_class}; legal values include "
                                f"{sorted(legal)[:8]}{'...' if len(legal) > 8 else ''}")
        if not self.types and not self.dims and not self.generator:
            raise SpecError(f"{origin}: family {self.key!r} needs dims, types, or a generator")
        try:
            if self.dims:
                dims_m(self.dims)
            for v in self.types:
                if v.dims:
                    dims_m(v.dims)
        except UnitError as e:
            raise SpecError(f"{origin}: family {self.key!r}: {e}") from None
        names = [v.name for v in self.types]
        dupes = {n for n in names if names.count(n) > 1}
        if dupes:
            raise SpecError(f"{origin}: family {self.key!r} has duplicate type names {sorted(dupes)}")

    def resolved_types(self) -> list[TypeVariant]:
        """The variants to actually build — falling back to a single 'Standard' from base dims."""
        if self.types:
            return self.types
        return [TypeVariant(name="Standard", dims=self.dims)]


def load_file(path: Path) -> list[FamilySpec]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    if not isinstance(raw, list):
        raise SpecError(f"{path}: expected a top-level list of family specs")
    return [FamilySpec.from_dict(r, origin=f"{Path(path).name}[{i}]") for i, r in enumerate(raw)]


def load_catalog(root: Path, discipline: str | None = None) -> list[FamilySpec]:
    """Load every family spec under catalog/, optionally filtered to one discipline directory."""
    root = Path(root)
    globs = sorted((root / discipline).rglob("*.yaml")) if discipline else sorted(root.rglob("*.yaml"))
    specs: list[FamilySpec] = []
    for f in globs:
        specs.extend(load_file(f))
    keys = [s.key for s in specs]
    dupes = {k for k in keys if keys.count(k) > 1}
    if dupes:
        raise SpecError(f"duplicate family keys across catalog: {sorted(dupes)}")
    return specs
