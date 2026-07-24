"""Classification codes must be real — never invented.

`data/uniclass_codes.csv` is a de-minimis extract of *only* the codes this catalog references, with
their published titles, taken from the Uniclass Pr and Ss tables. We don't redistribute the full
7,892-row tables (PLAN.md §8g); this is a validation fixture.

**Adding a family with a new code means looking that code up in the published table first**
(https://uniclass.thenbs.com) and adding the row here. That is the whole point of this test: it turns
"never guess a classification code" from a good intention into a build failure.

This discipline has already caught three rounds of mistakes:
  - `Pr_20_93_71` assumed for steel columns — actually *Retaining wall units*
  - `Pr_20_93_52` assumed for steel beams — actually *Masonry walling units*
  - four invented MEP codes (`Pr_65_52_15`, `Pr_65_52_97`, `Pr_65_70_31`, `Pr_75_75_31`) that do not
    exist in the Pr table at all
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from massing_families.spec import load_catalog

CODES = Path(__file__).resolve().parents[1] / "data" / "uniclass_codes.csv"


@pytest.fixture(scope="module")
def published() -> dict[str, str]:
    if not CODES.exists():
        pytest.skip(f"{CODES} missing")
    return {r["code"]: r["title"] for r in csv.DictReader(CODES.open(encoding="utf-8"))}


def test_every_uniclass_code_is_published(catalog_root, published):
    bad = []
    for spec in load_catalog(catalog_root):
        code = spec.classification.get("uniclass")
        if code and code not in published:
            bad.append((spec.key, code))
    assert not bad, ("classification codes not found in the published Uniclass tables — look them up "
                     f"at uniclass.thenbs.com and add them to {CODES.name}: {bad}")


def test_codes_use_a_known_table_prefix(published):
    for code in published:
        assert code.split("_")[0] in {"Pr", "Ss"}, f"{code} is not a Pr or Ss code"


def test_every_family_is_classified(catalog_root):
    unclassified = [s.key for s in load_catalog(catalog_root) if not s.classification]
    assert not unclassified, f"families with no classification: {unclassified}"


# Discrete manufactured articles. A chair or a valve is a *product* (Pr); it is never a system (Ss).
# Assemblies — walls, slabs, roofs, ceilings, stairs, ramps, fences, temporary works — legitimately
# take Ss codes, so the meaningful check is the inverse: no Ss code on a discrete product class.
PRODUCT_CLASSES = {
    "IfcFurnitureType", "IfcSanitaryTerminalType", "IfcElectricApplianceType",
    "IfcLightFixtureType", "IfcValveType", "IfcPumpType", "IfcTransformerType",
    "IfcOutletType", "IfcSwitchingDeviceType", "IfcJunctionBoxType", "IfcSensorType",
    "IfcAlarmType", "IfcDamperType", "IfcFilterType", "IfcCompressorType",
    "IfcElectricGeneratorType", "IfcElectricDistributionBoardType",
    "IfcPipeSegmentType", "IfcPipeFittingType", "IfcDuctSegmentType", "IfcDuctFittingType",
    "IfcCableCarrierSegmentType", "IfcWasteTerminalType", "IfcUnitaryEquipmentType",
    "IfcAirTerminalType", "IfcFireSuppressionTerminalType",
}


def test_systems_codes_not_used_on_discrete_products(catalog_root):
    """Ss is the *systems* table. A wall assembly is a system; a valve is a product."""
    bad = []
    for spec in load_catalog(catalog_root):
        code = spec.classification.get("uniclass", "")
        if code.startswith("Ss_") and spec.ifc_class in PRODUCT_CLASSES:
            bad.append((spec.key, spec.ifc_class, code))
    assert not bad, f"systems (Ss) codes used on discrete product classes: {bad}"
