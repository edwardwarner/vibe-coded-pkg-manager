"""
Dependency resolver for finding optimal package combinations.
"""

import re
from typing import List, Dict, Set, Optional, Tuple
from packaging.specifiers import SpecifierSet
from packaging.version import Version, parse
from ..models import PackageSpec, ResolvedPackage, ResolutionResult, Environment, PackageConflict, ConflictResolutionStrategy
from ..clients import PyPIClient
from .conflict_resolver import ConflictResolver


class DependencyResolver:
    """Resolves package dependencies and finds optimal versions."""
    
    def __init__(self):
        self.pypi_client = PyPIClient()
        self.conflict_resolver = ConflictResolver(self.pypi_client)
        self.resolved_packages: Dict[str, ResolvedPackage] = {}
        self.package_constraints: Dict[str, List[SpecifierSet]] = {}
        self.conflicts: List[PackageConflict] = []
    
    def parse_package_spec(self, spec_string: str) -> PackageSpec:
        """Parse a package specification string."""
        # Handle various formats: package, package==version, package>=version, etc.
        if '==' in spec_string:
            name, version = spec_string.split('==', 1)
        elif '>=' in spec_string:
            name, version = spec_string.split('>=', 1)
        elif '<=' in spec_string:
            name, version = spec_string.split('<=', 1)
        elif '>' in spec_string:
            name, version = spec_string.split('>', 1)
        elif '<' in spec_string:
            name, version = spec_string.split('<', 1)
        elif '~=' in spec_string:
            name, version = spec_string.split('~=', 1)
        elif '!=' in spec_string:
            name, version = spec_string.split('!=', 1)
        else:
            # If no operator is specified, assume it's just a package name
            name = spec_string.strip()
            version = ">=0"
        
        # Ensure version spec has a valid format
        if version != ">=0" and not any(op in version for op in ['==', '>=', '<=', '>', '<', '~=', '!=']):
            # If version is just a number, make it a minimum version
            version = f">={version}"
        
        return PackageSpec(name=name.strip().lower(), version_spec=version.strip())
    
    def resolve_dependencies(
        self, 
        package_specs: List[str], 
        environment: Environment,
        conflict_strategy: Optional[ConflictResolutionStrategy] = None
    ) -> ResolutionResult:
        """Resolve dependencies for the given package specifications."""
        self.resolved_packages.clear()
        self.package_constraints.clear()
        self.conflicts.clear()
        
        # Use default strategy if none provided
        if conflict_strategy is None:
            conflict_strategy = ConflictResolutionStrategy()
        
        # Parse package specifications
        specs = [self.parse_package_spec(spec) for spec in package_specs]
        
        # Build initial constraints
        for spec in specs:
            if spec.name not in self.package_constraints:
                self.package_constraints[spec.name] = []
            self.package_constraints[spec.name].append(spec.specifier_set)
        
        # Resolve each package
        for spec in specs:
            self._resolve_package(spec, environment)
        
        # Detect conflicts using the new conflict resolver
        self.conflicts = self.conflict_resolver.detect_conflicts(
            self.resolved_packages, self.package_constraints
        )
        
        # Resolve conflicts if any
        resolutions = []
        if self.conflicts and conflict_strategy.strategy != "ignore":
            try:
                resolutions = self.conflict_resolver.resolve_conflicts(
                    self.conflicts, conflict_strategy, environment
                )
                
                # Apply resolutions
                for resolution in resolutions:
                    self.conflict_resolver.apply_resolution(resolution, self.resolved_packages)
                    
            except ValueError as e:
                # If conflict resolution fails, return with conflicts
                pass
        
        # Build dependency tree
        dependency_tree = self._build_dependency_tree()
        
        return ResolutionResult(
            packages=list(self.resolved_packages.values()),
            conflicts=[conflict.reason for conflict in self.conflicts],
            package_conflicts=self.conflicts,
            resolutions=resolutions,
            success=len(self.conflicts) == 0 or len(resolutions) > 0,
            dependency_tree=dependency_tree,
            conflict_resolution_strategy=conflict_strategy
        )
    
    def _resolve_package(self, spec: PackageSpec, environment: Environment) -> Optional[ResolvedPackage]:
        """Resolve a single package and its dependencies."""
        if spec.name in self.resolved_packages:
            return self.resolved_packages[spec.name]
        
        # Find Python-compatible versions first
        compatible_versions = self.pypi_client.find_python_compatible_versions(
            spec.name, environment.python_version, spec
        )
        
        if not compatible_versions:
            # Fallback to original method if no Python-compatible versions found
            compatible_versions = self.pypi_client.find_compatible_versions(spec.name, spec)
            if not compatible_versions:
                print(f"Warning: No compatible versions found for {spec.name}")
                return None
            else:
                print(f"Warning: No Python {environment.python_version} compatible versions found for {spec.name}, using latest available")
        
        # Select the latest compatible version
        selected_version = compatible_versions[-1]
        
        # Verify Python compatibility (should be True if we used find_python_compatible_versions)
        is_compatible = self.pypi_client.check_python_compatibility(spec.name, selected_version, environment.python_version)
        if not is_compatible:
            print(f"Warning: {spec.name} {selected_version} may not be compatible with Python {environment.python_version}")
        else:
            print(f"✅ {spec.name} {selected_version} is compatible with Python {environment.python_version}")
        
        # Create resolved package
        resolved_package = ResolvedPackage(
            name=spec.name,
            version=selected_version,
            is_direct=True
        )
        
        self.resolved_packages[spec.name] = resolved_package
        
        # Resolve dependencies
        dependencies = self.pypi_client.get_dependencies(spec.name, selected_version)
        for dep in dependencies:
            dep_spec = self._parse_dependency_string(dep)
            if dep_spec:
                self._resolve_package(dep_spec, environment)
                resolved_package.dependencies.append(dep_spec.name)
        
        return resolved_package
    
    def _parse_dependency_string(self, dep_string: str) -> Optional[PackageSpec]:
        """Parse a dependency string from package metadata."""
        # Remove extra markers like [extra], (>=3.7), etc.
        dep_string = re.sub(r'\[.*?\]', '', dep_string)
        dep_string = re.sub(r'\(.*?\)', '', dep_string)
        dep_string = dep_string.strip()
        
        if not dep_string:
            return None
        
        return self.parse_package_spec(dep_string)
    

    
    def _build_dependency_tree(self) -> Dict[str, List[str]]:
        """Build a dependency tree from resolved packages."""
        tree = {}
        for package in self.resolved_packages.values():
            tree[package.name] = package.dependencies
        return tree
    
    def optimize_versions(self, resolution_result: ResolutionResult, environment: Environment = None) -> ResolutionResult:
        """Optimize package versions for better compatibility."""
        # This is a simplified optimization - in a real implementation,
        # you might want to use more sophisticated algorithms
        
        optimized_packages = []
        
        for package in resolution_result.packages:
            # Keep the current version if it's already Python-compatible
            best_version = package.version
            
            # Only try to optimize if we have environment info and the current version isn't optimal
            if environment:
                # Try to find a more recent version that's still Python-compatible
                compatible_versions = self.pypi_client.find_python_compatible_versions(
                    package.name, environment.python_version
                )
                
                # Find the latest compatible version that satisfies all constraints
                for version in reversed(compatible_versions):
                    if self._is_version_compatible(package.name, version):
                        best_version = version
                        break
            
            optimized_package = ResolvedPackage(
                name=package.name,
                version=best_version,
                dependencies=package.dependencies,
                conflicts=package.conflicts,
                is_direct=package.is_direct
            )
            optimized_packages.append(optimized_package)
        
        return ResolutionResult(
            packages=optimized_packages,
            conflicts=resolution_result.conflicts,
            warnings=resolution_result.warnings,
            success=resolution_result.success,
            dependency_tree=resolution_result.dependency_tree
        )
    
    def _is_version_compatible(self, package_name: str, version: str) -> bool:
        """Check if a version is compatible with all constraints."""
        if package_name not in self.package_constraints:
            return True
        
        try:
            parsed_version = Version(version)
            for constraint in self.package_constraints[package_name]:
                if not constraint.contains(parsed_version):
                    return False
            return True
        except Exception:
            return False 