"""Imperial-first dimensions with exact metric storage.

Per PLAN.md §7b: the catalog is *authored* in US imperial nominals (3'-0", W14X90, 2x4, #5) because
nominal size is a content decision that cannot be unit-converted — 0.9 m converts to 2'-11 7/16", which
is not a door anyone builds. Geometry is *stored* in exact metres, because IFC carries an
IfcUnitAssignment and massing scales every length on write; storing the exact equivalent yields clean
round numbers in every unit system (3'-0" -> 0.9144 m -> 3.0 ft / 36 in / 914.4 mm).

The inch has been defined as exactly 25.4 mm since 1959, so the conversion is lossless both ways. We
round to 9 decimal places purely to keep binary-float dust out of the IFC text.
"""
from __future__ import annotations

import re
from fractions import Fraction

M_PER_INCH = Fraction(254, 10000)          # exactly 0.0254 m
INCHES_PER_FOOT = 12
_ROUND = 9

# 3'-0"  |  3'-6 1/2"  |  7'  |  36"  |  1 1/2"  |  5/8"  |  0'-4 7/8"  |  8.00"  |  0.285"
# The inches whole-part accepts decimals because that is how steel sections are dimensioned
# (W14X90 web = 0.440"), while architectural dimensions use the fraction form (3'-6 1/2").
_FT_IN = re.compile(
    r"""^\s*
    (?:(?P<feet>\d+(?:\.\d+)?)\s*(?:'|ft|feet)\s*)?              # feet part
    (?:[-\s]*)                                                    # separator
    (?:(?P<whole>\d+(?:\.\d+)?)?\s*(?:(?P<num>\d+)\s*/\s*(?P<den>\d+))?   # inches: whole + fraction
       \s*(?:"|in|inch|inches)\s*)?
    $""",
    re.VERBOSE,
)


class UnitError(ValueError):
    """Raised when a dimension string cannot be parsed."""


def inches(value) -> float:
    """Parse an imperial dimension to inches.

    Accepts: "3'-0\"", "3'-6 1/2\"", "7'", "36\"", "1 1/2\"", "5/8\"".
    Bare int/float is treated as inches, so `dims: [36, 2, 84]` is valid shorthand.
    """
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        raise UnitError("empty dimension")
    # bare numeric string -> inches
    try:
        return float(s)
    except ValueError:
        pass
    m = _FT_IN.match(s)
    if not m or not any(m.group(g) for g in ("feet", "whole", "num")):
        raise UnitError(f"cannot parse imperial dimension {value!r} "
                        f"(expected forms: 3'-0\", 3'-6 1/2\", 7', 36\", 1 1/2\", 5/8\")")
    total = Fraction(0)
    if m.group("feet"):
        total += Fraction(str(m.group("feet"))) * INCHES_PER_FOOT
    if m.group("whole"):
        total += Fraction(str(m.group("whole")))
    if m.group("num"):
        den = int(m.group("den"))
        if den == 0:
            raise UnitError(f"zero denominator in {value!r}")
        total += Fraction(int(m.group("num")), den)
    return float(total)


def metres(value) -> float:
    """Parse an imperial dimension straight to exact metres — the storage unit."""
    exact = Fraction(inches(value)).limit_denominator(10**6) * M_PER_INCH
    return round(float(exact), _ROUND)


def dims_m(values) -> list[float]:
    """Convert a [w, d, h] imperial spec to exact metres."""
    out = [metres(v) for v in values]
    if len(out) != 3 or any(v <= 0 for v in out):
        raise UnitError(f"dims must be three positive [w, d, h] values, got {values!r}")
    return out


def format_ft_in(m: float, precision: int = 16) -> str:
    """Format metres back to a US-drawing dimension string: 0.9144 -> 3'-0\".

    `precision` is the fractional-inch denominator to snap to (16 = 1/16", the drawing convention).
    """
    total_in = Fraction(round(float(m) / float(M_PER_INCH) * precision), precision)
    feet, rem = divmod(total_in, INCHES_PER_FOOT)
    whole = int(rem)
    frac = rem - whole
    out = f"{int(feet)}'-{whole}"
    if frac:
        out += f" {frac.numerator}/{frac.denominator}"
    return out + '"'


def format_inches(m: float, precision: int = 16) -> str:
    """Format metres as plain inches: 0.0508 -> 2\". Used for thin members (wall/plate thickness)."""
    total_in = Fraction(round(float(m) / float(M_PER_INCH) * precision), precision)
    whole = int(total_in)
    frac = total_in - whole
    out = str(whole) if whole or not frac else ""
    if frac:
        out = (out + " " if out else "") + f"{frac.numerator}/{frac.denominator}"
    return out + '"'
