"""massing-families — IFC4 family/type content library for the Massing platform.

Authored in US imperial nominals, stored in exact metres. See PLAN.md.
"""
# The single source of truth for the library version. `cli build` stamps it into every pack
# filename, the manifest, each pack's STEP header and every type's MF_Library.Version, so leaving it
# stale silently mislabels content: a whole current catalog once shipped to a deployment's shelf
# labelled v0.1.0 because this string had not moved since the first release.
# pyproject.toml reads it dynamically; tests/test_version.py checks it against the CHANGELOG.
__version__ = "0.1.6"
