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

__all__ = [
    "PackageSpec",
    "PackageInfo", 
    "ResolvedPackage",
    "Environment",
    "ResolutionResult",
    "PackageConflict",
    "ConflictResolutionStrategy",
    "ConflictResolution"
]
