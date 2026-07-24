"""Spec validation — schema-driven, so a typo fails the build rather than shipping broken content."""
from __future__ import annotations

import pytest

from massing_families.spec import (TYPE_CLASSES, FamilySpec, SpecError, load_catalog,
                                   predefined_values)

BASE = {"key": "x", "label": "X", "ifc_class": "IfcDoorType", "category": "Doors",
        "discipline": "architectural", "dims": ["3'-0\"", '2"', "7'-0\""]}


def test_knows_every_ifc4_type_class():
    assert len(TYPE_CLASSES) == 125
    assert {"IfcDoorType", "IfcColumnType", "IfcSanitaryTerminalType"} <= TYPE_CLASSES
    assert "IfcWall" not in TYPE_CLASSES          # occurrence class, not a type


def test_reads_predefined_enums_from_schema():
    assert predefined_values("IfcDoorType") == {"DOOR", "GATE", "TRAPDOOR", "USERDEFINED",
                                                "NOTDEFINED"}
    assert "COLUMN" in predefined_values("IfcColumnType")


def test_accepts_valid_spec():
    spec = FamilySpec.from_dict({**BASE, "predefined": "DOOR"})
    assert spec.dims_metres == [0.9144, 0.0508, 2.1336]
    assert spec.type_name(spec.resolved_types()[0]) == "X - Standard"


@pytest.mark.parametrize("patch,fragment", [
    ({"ifc_class": "IfcDoorTyp"}, "not an IFC4"),
    ({"ifc_class": "IfcWall"}, "not an IFC4"),
    ({"predefined": "NOPE"}, "invalid for IfcDoorType"),
    ({"tier": "L999"}, "tier must be one of"),
    ({"dims": ["3'-0\"", "banana", "7'-0\""]}, "cannot parse"),
    ({"nonsense": 1}, "unknown spec field"),
])
def test_rejects_bad_spec(patch, fragment):
    with pytest.raises(SpecError) as e:
        FamilySpec.from_dict({**BASE, **patch})
    assert fragment in str(e.value)


def test_rejects_family_with_nothing_to_build():
    raw = {k: v for k, v in BASE.items() if k != "dims"}
    with pytest.raises(SpecError, match="needs dims, types, or a generator"):
        FamilySpec.from_dict(raw)


def test_rejects_duplicate_type_names():
    with pytest.raises(SpecError, match="duplicate type names"):
        FamilySpec.from_dict({**BASE, "types": [{"name": "A", "dims": [1, 1, 1]},
                                                {"name": "A", "dims": [2, 2, 2]}]})


def test_real_catalog_loads_and_is_unique(catalog_root):
    specs = load_catalog(catalog_root)
    assert specs, "catalog must not be empty"
    keys = [s.key for s in specs]
    assert len(keys) == len(set(keys))
    for s in specs:
        assert s.license, f"{s.key} must declare a licence"
        assert s.classification, f"{s.key} must be classified"
