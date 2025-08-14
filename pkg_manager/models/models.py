"""
Data models for the package manager.
"""

from typing import List, Dict, Optional, Set, Literal
from pydantic import BaseModel, Field, ConfigDict
from packaging.specifiers import SpecifierSet
from packaging.version import Version


class PackageSpec(BaseModel):
    """Represents a package specification with name and version constraints."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    name: str
    version_spec: str
    specifier_set: Optional[SpecifierSet] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.specifier_set is None:
            self.specifier_set = SpecifierSet(self.version_spec)


class PackageInfo(BaseModel):
    """Represents detailed information about a package."""
    name: str
    version: str
    dependencies: List[str] = Field(default_factory=list)
    requires_python: Optional[str] = None
    platform_specific: bool = False
    summary: Optional[str] = None
    description: Optional[str] = None


class ResolvedPackage(BaseModel):
    """Represents a resolved package with its dependencies."""
    name: str
    version: str
    dependencies: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    is_direct: bool = True


class Environment(BaseModel):
    """Represents the target environment."""
    python_version: str
    platform: str = "any"
    implementation: str = "cpython"
    architecture: Optional[str] = None


class ResolutionResult(BaseModel):
    """Represents the result of dependency resolution."""
    packages: List[ResolvedPackage]
    conflicts: List[str] = Field(default_factory=list)
    package_conflicts: List['PackageConflict'] = Field(default_factory=list)
    resolutions: List['ConflictResolution'] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    success: bool = True
    dependency_tree: Dict[str, List[str]] = Field(default_factory=dict)
    conflict_resolution_strategy: Optional['ConflictResolutionStrategy'] = None


class ConflictResolutionStrategy(BaseModel):
    """Represents a conflict resolution strategy."""
    strategy: Literal["auto", "manual", "ignore", "fail"] = "auto"
    prefer_latest: bool = True
    prefer_stable: bool = False
    allow_downgrade: bool = False
    max_attempts: int = 3


class ConflictResolution(BaseModel):
    """Represents a conflict resolution decision."""
    conflict_id: str
    package_name: str
    chosen_version: str
    reason: str
    strategy_used: str
    alternatives_considered: List[str] = Field(default_factory=list)


class PackageConflict(BaseModel):
    """Represents a package conflict."""
    package_name: str
    conflicting_versions: List[str]
    reason: str
    affected_packages: List[str] = Field(default_factory=list)
    resolution_suggestions: List[str] = Field(default_factory=list)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    auto_resolvable: bool = True 