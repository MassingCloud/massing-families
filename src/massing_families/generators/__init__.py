"""Type generators — expand one family spec into many catalogued types from a data table.

A `generator:` lets a single spec produce the whole run of real shapes (every AISC W-section, every
nominal duct size) instead of hand-listing them, which is how the catalog reaches thousands of types
off a few hundred families without becoming unmaintainable YAML.
"""
from __future__ import annotations

from . import aisc, rebar, sizes

GENERATORS = {
    "aisc": aisc.generate,
    "sizes": sizes.generate,
    "rebar": rebar.generate,
}


def expand(spec):
    """The variants to build for a spec — generator output if declared, else its explicit types."""
    if not spec.generator:
        return spec.resolved_types()
    fn = GENERATORS.get(spec.generator)
    if fn is None:
        raise ValueError(f"family {spec.key!r}: unknown generator {spec.generator!r}; "
                         f"have {sorted(GENERATORS)}")
    variants = fn(spec)
    if not variants:
        raise ValueError(f"family {spec.key!r}: generator {spec.generator!r} produced no types")
    return variants


__all__ = ["GENERATORS", "expand", "aisc", "rebar", "sizes"]
