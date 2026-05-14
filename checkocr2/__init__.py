"""CheckOCR2 package foundation.

The legacy public launchers remain at the repository root. New implementation
modules live here so behavior can be migrated incrementally behind the same GUI.
"""

__all__ = ["__version__", "__display_version__"]

__version__ = "7.0.0"
__display_version__ = f"V{'.'.join(__version__.split('.')[:2])}"
