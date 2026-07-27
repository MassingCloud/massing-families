"""Typology completeness — makes "can a user build a full building?" measurable rather than aspirational.

PLAN.md §10 Phase 6 commits each typology to a checklist test. This is that test: for each of the six
typologies, assert the catalog carries at least one family for every system that typology cannot be
built without.

A failure here is not a bug — it is an honest statement that the catalog cannot yet finish that
building type. `test_report_typology_gaps` prints the outstanding list so the gap is visible rather
than buried.
"""
from __future__ import annotations

import pytest

from massing_families.spec import load_catalog

# system -> predicate over the catalog. Kept as IFC classes and category names rather than family keys
# so the checklist stays true as families are renamed or split.
CORE = {
    "walls": lambda s: s.ifc_class == "IfcWallType",
    "floors": lambda s: s.ifc_class == "IfcSlabType",
    "roofs": lambda s: s.ifc_class == "IfcRoofType",
    "ceilings": lambda s: s.ifc_class == "IfcCoveringType" and s.predefined == "CEILING",
    "doors": lambda s: s.ifc_class == "IfcDoorType",
    "windows": lambda s: s.ifc_class == "IfcWindowType",
    "stairs": lambda s: s.ifc_class == "IfcStairType",
    "railings": lambda s: s.ifc_class == "IfcRailingType",
    "floor finishes": lambda s: s.ifc_class == "IfcCoveringType" and s.predefined == "FLOORING",
    "columns": lambda s: s.ifc_class == "IfcColumnType",
    "beams": lambda s: s.ifc_class == "IfcBeamType",
    # Split, not OR'd. These were one "foundations" check reading
    # `ifc_class in {IfcFootingType, IfcPileType}`, and a single HP pile satisfied it while the
    # catalog carried *zero* footings — 413 families and nothing to stand a building on. massing's
    # own coverage gate caught it (v0.3.670); this check could not, because an OR over two classes
    # only proves one of them exists. Any requirement naming two classes hides that hole.
    "footings": lambda s: s.ifc_class == "IfcFootingType",
    "piles": lambda s: s.ifc_class == "IfcPileType",
    "duct": lambda s: s.ifc_class == "IfcDuctSegmentType",
    "duct fittings": lambda s: s.ifc_class == "IfcDuctFittingType",
    "air terminals": lambda s: s.ifc_class == "IfcAirTerminalType",
    "hvac equipment": lambda s: s.ifc_class == "IfcUnitaryEquipmentType",
    "pipe": lambda s: s.ifc_class == "IfcPipeSegmentType",
    "pipe fittings": lambda s: s.ifc_class == "IfcPipeFittingType",
    "valves": lambda s: s.ifc_class == "IfcValveType",
    "plumbing fixtures": lambda s: s.ifc_class == "IfcSanitaryTerminalType",
    "drainage": lambda s: s.ifc_class == "IfcWasteTerminalType",
    "raceway": lambda s: s.ifc_class == "IfcCableCarrierSegmentType",
    "electrical distribution": lambda s: s.ifc_class == "IfcElectricDistributionBoardType",
    "lighting": lambda s: s.ifc_class == "IfcLightFixtureType",
    "outlets": lambda s: s.ifc_class == "IfcOutletType",
    "switches": lambda s: s.ifc_class == "IfcSwitchingDeviceType",
    "sprinklers": lambda s: s.ifc_class == "IfcFireSuppressionTerminalType",
    "fire alarm notification": lambda s: s.ifc_class == "IfcAlarmType",
    "fire detection": lambda s: s.ifc_class == "IfcSensorType",
    "fire dampers": lambda s: s.ifc_class == "IfcDamperType",
    "furniture": lambda s: s.ifc_class == "IfcFurnitureType",
    "heat source": lambda s: s.ifc_class == "IfcBoilerType",
    # Genuinely an OR: an air-cooled chiller needs no tower, so requiring both would be wrong.
    "cooling source": lambda s: s.ifc_class in {"IfcChillerType", "IfcCoolingTowerType"},
    "pumps": lambda s: s.ifc_class == "IfcPumpType",
    "terminal units": lambda s: s.ifc_class == "IfcAirTerminalBoxType",
    "roof drainage": lambda s: s.category == "Roof Drainage",
    "reinforcement": lambda s: s.ifc_class == "IfcReinforcingBarType",
}

TYPOLOGY_EXTRA = {
    "residential": {
        "appliances": lambda s: s.ifc_class == "IfcElectricApplianceType",
        "overhead doors": lambda s: "overhead" in s.label.lower(),
        "furnace / split system": lambda s: s.label.lower() in {"furnace", "split system"},
        "egress windows": lambda s: "egress" in s.label.lower(),
        "decks / balconies": lambda s: s.category == "Exterior" and s.discipline == "residential",
        "closet systems": lambda s: "closet" in s.label.lower(),
        "patio doors": lambda s: "patio" in s.label.lower(),
    },
    "commercial": {
        "curtain wall": lambda s: s.ifc_class == "IfcCurtainWallType",
        "elevators": lambda s: s.ifc_class == "IfcTransportElementType",
        "raised access floor": lambda s: "raised access" in s.label.lower(),
        "vav distribution": lambda s: s.ifc_class == "IfcAirTerminalBoxType",
        "central plant": lambda s: s.ifc_class in {"IfcChillerType", "IfcBoilerType"},
        "roof accessories": lambda s: s.category == "Roof Accessories",
    },
    "hotel": {
        "ptac / fan coil": lambda s: s.discipline == "hospitality" and "coil" in s.label.lower()
                                     or "ptac" in s.label.lower(),
        "commercial kitchen": lambda s: s.category == "Commercial Kitchen",
        "commercial laundry": lambda s: s.category == "Laundry",
        "guestroom ff&e": lambda s: s.category == "Guestroom FF&E",
    },
    "hospital": {
        "medical gas": lambda s: s.category == "Medical Gas",
        "headwalls": lambda s: "headwall" in s.label.lower(),
        "imaging": lambda s: s.category == "Imaging",
        "lead-lined construction": lambda s: "lead-lined" in s.label.lower(),
        "lab casework": lambda s: s.category == "Laboratory",
        "nurse call": lambda s: s.category == "Nurse Call",
    },
    "industrial": {
        "overhead cranes": lambda s: s.category == "Cranes",
        "dock equipment": lambda s: s.category == "Dock Equipment",
        "esfr sprinklers": lambda s: "esfr" in s.label.lower(),
        "high-bay lighting": lambda s: "high-bay" in s.label.lower(),
        "mezzanine": lambda s: "mezzanine" in s.label.lower(),
    },
    "airport": {
        "jet bridge": lambda s: "boarding bridge" in s.label.lower(),
        "baggage handling": lambda s: s.category == "Baggage Handling",
        "moving walks": lambda s: "moving walk" in s.label.lower(),
        "check-in / gate": lambda s: s.category == "Terminal",
        "security screening": lambda s: s.category == "Security",
    },
}


@pytest.fixture(scope="module")
def specs(catalog_root):
    return load_catalog(catalog_root)


def _missing(specs, checklist):
    return sorted(name for name, pred in checklist.items()
                  if not any(pred(s) for s in specs))


def test_core_building_systems_present(specs):
    """Every typology needs these; a gap here blocks all six."""
    assert _missing(specs, CORE) == []


@pytest.mark.parametrize("typology", sorted(TYPOLOGY_EXTRA))
def test_typology_specific_systems_present(specs, typology):
    assert _missing(specs, TYPOLOGY_EXTRA[typology]) == [], \
        f"{typology} cannot be completed — missing families for these systems"


def test_report_typology_gaps(specs, capsys):
    """Always-passing visibility check: prints per-typology status so gaps stay honest."""
    with capsys.disabled():
        print("\n  typology completeness:")
        core_gaps = _missing(specs, CORE)
        print(f"    {'core systems':16} {len(CORE) - len(core_gaps)}/{len(CORE)}"
              f"{'  MISSING: ' + ', '.join(core_gaps) if core_gaps else ''}")
        for typology, checks in sorted(TYPOLOGY_EXTRA.items()):
            gaps = _missing(specs, checks)
            print(f"    {typology:16} {len(checks) - len(gaps)}/{len(checks)}"
                  f"{'  MISSING: ' + ', '.join(gaps) if gaps else ''}")


def test_tier_agrees_with_builder(specs):
    """A declared tier must not contradict the geometry actually built.

    `tier` is author-declared; `GeometryStatus` is derived from the builder. Thirteen families were
    labelled L200 while using `revolve` or `swept_disk` — under-claiming rather than over-claiming, so
    harmless to a consumer, but it made "how many families are still proxies" answerable two ways
    (333 by tier, 320 by builder). Only the derived number is true.
    """
    wrong = [(s.key, s.tier, s.builder) for s in specs
             if (s.tier == "L200") != (s.builder == "box")]
    assert not wrong, f"tier contradicts builder: {wrong}"
