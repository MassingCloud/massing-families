"""Imperial parsing and exact metric storage (PLAN.md §7b)."""
from __future__ import annotations

import pytest

from massing_families.units import (UnitError, dims_m, format_ft_in, format_inches, inches,
                                    metres)


@pytest.mark.parametrize("value,expected_in", [
    ("3'-0\"", 36), ("3'-6 1/2\"", 42.5), ("7'", 84), ('36"', 36),
    ('1 1/2"', 1.5), ('5/8"', 0.625), (36, 36), ("0'-4 7/8\"", 4.875),
    ('8.00"', 8.0), ('0.285"', 0.285), ('3.3125"', 3.3125),      # decimal — steel sections
])
def test_parses_imperial(value, expected_in):
    assert inches(value) == pytest.approx(expected_in)


def test_exact_metric_storage():
    """3'-0" must store as exactly 0.9144 m — the value that yields clean numbers in every unit."""
    assert metres("3'-0\"") == 0.9144
    assert metres("7'-0\"") == 2.1336
    assert dims_m(["3'-0\"", '1 3/4"', "7'-0\""]) == [0.9144, 0.044450, 2.1336]


@pytest.mark.parametrize("value", ["3'-0\"", "3'-6 1/2\"", "7'", '36"', "0'-4 7/8\""])
def test_round_trips_through_metres(value):
    assert format_ft_in(metres(value)) == format_ft_in(metres(inches(value)))
    assert inches(format_ft_in(metres(value))) == pytest.approx(inches(value))


def test_formats_for_drawings():
    assert format_ft_in(0.9144) == "3'-0\""
    assert format_ft_in(2.1336) == "7'-0\""
    assert format_inches(metres('3 5/8"')) == '3 5/8"'
    assert format_inches(metres('4 7/8"')) == '4 7/8"'


@pytest.mark.parametrize("bad", ["", "banana", "3 foot", None])
def test_rejects_garbage(bad):
    with pytest.raises((UnitError, TypeError)):
        inches(bad)


def test_rejects_nonpositive_dims():
    with pytest.raises(UnitError):
        dims_m(["3'-0\"", '0"', "7'-0\""])
