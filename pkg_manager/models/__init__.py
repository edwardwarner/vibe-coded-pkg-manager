"""
Data models for the package manager.
"""

from .models import (
    PackageSpec,
    PackageInfo,
    ResolvedPackage,
    Environment,
    ResolutionResult,
    PackageConflict,
    ConflictResolutionStrategy,
    ConflictResolution
)

from .python_versions import PythonVersionManager, python_version_manager

__all__ = [
    "PackageSpec",
    "PackageInfo", 
    "ResolvedPackage",
    "Environment",
    "ResolutionResult",
    "PackageConflict",
    "ConflictResolutionStrategy",
    "ConflictResolution",
    "PythonVersionManager",
    "python_version_manager"
]
