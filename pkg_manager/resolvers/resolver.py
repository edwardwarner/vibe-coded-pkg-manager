"""
Dependency resolver for finding optimal package combinations.
"""

import re
from typing import List, Dict, Set, Optional, Tuple
from packaging.specifiers import SpecifierSet
from packaging.version import Version, parse
from ..models import PackageSpec, ResolvedPackage, ResolutionResult, Environment, PackageConflict
from ..clients import PyPIClient


class DependencyResolver:
    """Resolves package dependencies and finds optimal version combinations."""
    
    def __init__(self, pypi_client: PyPIClient):
        self.pypi_client = pypi_client
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
            version = "*"
        
        # Ensure version spec has a valid format
        if version != "*" and not any(op in version for op in ['==', '>=', '<=', '>', '<', '~=', '!=']):
            # If version is just a number, make it a minimum version
            version = f">={version}"
        
        return PackageSpec(name=name.strip().lower(), version_spec=version.strip())
    
    def resolve_dependencies(self, package_specs: List[str], environment: Environment) -> ResolutionResult:
        """Resolve dependencies for the given package specifications."""
        self.resolved_packages.clear()
        self.package_constraints.clear()
        self.conflicts.clear()
        
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
        
        # Check for conflicts
        self._detect_conflicts()
        
        # Build dependency tree
        dependency_tree = self._build_dependency_tree()
        
        return ResolutionResult(
            packages=list(self.resolved_packages.values()),
            conflicts=[conflict.reason for conflict in self.conflicts],
            success=len(self.conflicts) == 0,
            dependency_tree=dependency_tree
        )
    
    def _resolve_package(self, spec: PackageSpec, environment: Environment) -> Optional[ResolvedPackage]:
        """Resolve a single package and its dependencies."""
        if spec.name in self.resolved_packages:
            return self.resolved_packages[spec.name]
        
        # Find compatible versions
        compatible_versions = self.pypi_client.find_compatible_versions(spec.name, spec)
        
        if not compatible_versions:
            print(f"Warning: No compatible versions found for {spec.name}")
            return None
        
        # Select the latest compatible version
        selected_version = compatible_versions[-1]
        
        # Check Python compatibility
        if not self.pypi_client.check_python_compatibility(spec.name, selected_version, environment.python_version):
            print(f"Warning: {spec.name} {selected_version} may not be compatible with Python {environment.python_version}")
        
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
    
    def _detect_conflicts(self):
        """Detect version conflicts between packages."""
        for package_name, constraints in self.package_constraints.items():
            if len(constraints) > 1:
                # Check if constraints are compatible
                intersection = constraints[0]
                for constraint in constraints[1:]:
                    intersection = intersection & constraint
                
                if not intersection:
                    self.conflicts.append(PackageConflict(
                        package_name=package_name,
                        conflicting_versions=[str(c) for c in constraints],
                        reason=f"Conflicting version constraints for {package_name}: {[str(c) for c in constraints]}"
                    ))
    
    def _build_dependency_tree(self) -> Dict[str, List[str]]:
        """Build a dependency tree from resolved packages."""
        tree = {}
        for package in self.resolved_packages.values():
            tree[package.name] = package.dependencies
        return tree
    
    def optimize_versions(self, resolution_result: ResolutionResult) -> ResolutionResult:
        """Optimize package versions for better compatibility."""
        # This is a simplified optimization - in a real implementation,
        # you might want to use more sophisticated algorithms
        
        optimized_packages = []
        
        for package in resolution_result.packages:
            # Try to find a more recent version that's still compatible
            available_versions = self.pypi_client.get_available_versions(package.name)
            
            # Find the latest version that satisfies all constraints
            best_version = package.version
            for version in reversed(available_versions):
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