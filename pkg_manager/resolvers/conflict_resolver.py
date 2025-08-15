"""
Conflict resolution module for the package manager.
"""

import uuid
from typing import List, Dict, Optional, Tuple
from packaging.version import Version, parse
from packaging.specifiers import SpecifierSet

from ..models import (
    PackageConflict, 
    ConflictResolution, 
    ConflictResolutionStrategy,
    PackageSpec,
    ResolvedPackage
)
from ..clients.pypi_client import OptimizedPyPIClient


class ConflictResolver:
    """Handles package conflict resolution with different strategies."""
    
    def __init__(self, pypi_client: OptimizedPyPIClient):
        self.pypi_client = pypi_client
    
    def resolve_conflicts(
        self, 
        conflicts: List[PackageConflict], 
        strategy: ConflictResolutionStrategy,
        environment: 'Environment'
    ) -> List[ConflictResolution]:
        """Resolve conflicts using the specified strategy."""
        resolutions = []
        
        for conflict in conflicts:
            if strategy.strategy == "ignore":
                continue
            elif strategy.strategy == "fail":
                raise ValueError(f"Conflict resolution failed: {conflict.reason}")
            elif strategy.strategy == "auto":
                resolution = self._auto_resolve_conflict(conflict, strategy, environment)
                if resolution:
                    resolutions.append(resolution)
            elif strategy.strategy == "manual":
                # For manual resolution, we'll return suggestions
                # The actual resolution will be handled by user input
                continue
        
        return resolutions
    
    def _auto_resolve_conflict(
        self, 
        conflict: PackageConflict, 
        strategy: ConflictResolutionStrategy,
        environment: 'Environment'
    ) -> Optional[ConflictResolution]:
        """Automatically resolve a conflict using the specified strategy."""
        if not conflict.auto_resolvable:
            return None
        
        # Get all available versions for the package
        available_versions = self.pypi_client.get_available_versions(conflict.package_name)
        if not available_versions:
            return None
        
        # Find compatible versions
        compatible_versions = []
        for version in available_versions:
            if self.pypi_client.check_python_compatibility(
                conflict.package_name, version, environment.python_version
            ):
                compatible_versions.append(version)
        
        if not compatible_versions:
            return None
        
        # Sort versions based on strategy
        if strategy.prefer_latest:
            compatible_versions.sort(key=parse, reverse=True)
        else:
            compatible_versions.sort(key=parse)
        
        # Find the best version that satisfies constraints
        chosen_version = None
        alternatives_considered = []
        
        for version in compatible_versions:
            alternatives_considered.append(version)
            
            # Check if this version satisfies all constraints
            if self._satisfies_constraints(version, conflict.conflicting_versions):
                chosen_version = version
                break
        
        if not chosen_version:
            # If no version satisfies all constraints, choose the best available
            chosen_version = compatible_versions[0]
        
        return ConflictResolution(
            conflict_id=str(uuid.uuid4()),
            package_name=conflict.package_name,
            chosen_version=chosen_version,
            reason=f"Auto-resolved using {strategy.strategy} strategy",
            strategy_used=strategy.strategy,
            alternatives_considered=alternatives_considered
        )
    
    def _satisfies_constraints(self, version: str, constraints: List[str]) -> bool:
        """Check if a version satisfies the given constraints."""
        try:
            parsed_version = Version(version)
            for constraint in constraints:
                spec = SpecifierSet(constraint)
                if not spec.contains(parsed_version):
                    return False
            return True
        except Exception:
            return False
    
    def suggest_resolutions(
        self, 
        conflict: PackageConflict, 
        environment: 'Environment'
    ) -> List[Dict[str, str]]:
        """Suggest possible resolutions for a conflict."""
        suggestions = []
        
        # Get available versions
        available_versions = self.pypi_client.get_available_versions(conflict.package_name)
        if not available_versions:
            return suggestions
        
        # Find compatible versions
        compatible_versions = []
        for version in available_versions:
            if self.pypi_client.check_python_compatibility(
                conflict.package_name, version, environment.python_version
            ):
                compatible_versions.append(version)
        
        # Sort by version (latest first)
        compatible_versions.sort(key=parse, reverse=True)
        
        # Create suggestions
        for i, version in enumerate(compatible_versions[:5]):  # Top 5 suggestions
            suggestion = {
                "version": version,
                "description": f"Use {version} (compatible with Python {environment.python_version})",
                "priority": "high" if i == 0 else "medium" if i < 3 else "low"
            }
            suggestions.append(suggestion)
        
        return suggestions
    
    def apply_resolution(
        self, 
        resolution: ConflictResolution, 
        resolved_packages: Dict[str, ResolvedPackage]
    ) -> None:
        """Apply a conflict resolution to the resolved packages."""
        if resolution.package_name in resolved_packages:
            resolved_packages[resolution.package_name].version = resolution.chosen_version
            resolved_packages[resolution.package_name].conflicts = []
    
    def detect_conflicts(
        self, 
        resolved_packages: Dict[str, ResolvedPackage],
        package_constraints: Dict[str, List[SpecifierSet]]
    ) -> List[PackageConflict]:
        """Detect conflicts in resolved packages."""
        conflicts = []
        
        for package_name, constraints in package_constraints.items():
            if len(constraints) > 1:
                # Check if constraints are compatible
                intersection = constraints[0]
                for constraint in constraints[1:]:
                    intersection = intersection & constraint
                
                if not intersection:
                    # Find affected packages
                    affected_packages = []
                    for pkg_name, pkg in resolved_packages.items():
                        if package_name in pkg.dependencies:
                            affected_packages.append(pkg_name)
                    
                    # Generate suggestions
                    suggestions = []
                    if package_name in resolved_packages:
                        current_version = resolved_packages[package_name].version
                        suggestions.append(f"Keep current version: {current_version}")
                    
                    # Add constraint-based suggestions
                    for constraint in constraints:
                        suggestions.append(f"Use constraint: {constraint}")
                    
                    conflict = PackageConflict(
                        package_name=package_name,
                        conflicting_versions=[str(c) for c in constraints],
                        reason=f"Conflicting version constraints for {package_name}",
                        affected_packages=affected_packages,
                        resolution_suggestions=suggestions,
                        severity="high" if len(affected_packages) > 2 else "medium",
                        auto_resolvable=True
                    )
                    conflicts.append(conflict)
        
        return conflicts
