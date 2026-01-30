"""
SurfScreen Integrations Package

외부 데이터베이스 및 서비스 연동
"""

# Lazy imports to avoid errors when optional dependencies are not installed
def __getattr__(name):
    if name in ("MPIntegration", "mp_get_structure", "mp_create_surface", "mp_search_materials"):
        from .materials_project import (
            MPIntegration,
            mp_get_structure,
            mp_create_surface,
            mp_search_materials,
        )
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "MPIntegration",
    "mp_get_structure",
    "mp_create_surface",
    "mp_search_materials",
]

