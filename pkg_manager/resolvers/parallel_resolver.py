"""
Parallel dependency resolver for finding optimal package combinations.
"""

import re
import time
from typing import List, Dict, Set, Optional, Tuple
from packaging.specifiers import SpecifierSet
from packaging.version import Version, parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..models import PackageSpec, ResolvedPackage, ResolutionResult, Environment, PackageConflict
from ..clients import ParallelPyPIClient


class ParallelDependencyResolver:
    """Parallel resolver for package dependencies and optimal version combinations."""
    
    def __init__(self, pypi_client: ParallelPyPIClient, max_workers: int = 10):
        self.pypi_client = pypi_client
        self.max_workers = max_workers
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
    
    def resolve_dependencies(self, package_specs: List[str], environment: Environment) -> ResolutionResult:
        """Resolve dependencies for the given package specifications using parallel processing."""
        start_time = time.time()
        
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
        
        # Resolve packages in parallel
        self._resolve_packages_parallel(specs, environment)
        
        # Check for conflicts
        self._detect_conflicts()
        
        # Build dependency tree
        dependency_tree = self._build_dependency_tree()
        
        resolution_time = time.time() - start_time
        print(f"Resolution completed in {resolution_time:.2f} seconds")
        
        return ResolutionResult(
            packages=list(self.resolved_packages.values()),
            conflicts=[conflict.reason for conflict in self.conflicts],
            success=len(self.conflicts) == 0,
            dependency_tree=dependency_tree
        )
    
    def _resolve_packages_parallel(self, specs: List[PackageSpec], environment: Environment):
        """Resolve multiple packages in parallel."""
        # First, resolve all direct packages in parallel
        direct_packages = [(spec.name, spec) for spec in specs]
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all package resolution tasks
            future_to_package = {
                executor.submit(self._resolve_package_worker, package_name, spec, environment): package_name
                for package_name, spec in direct_packages
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_package):
                package_name = future_to_package[future]
                try:
                    resolved_package = future.result()
                    if resolved_package:
                        self.resolved_packages[package_name] = resolved_package
                except Exception as e:
                    print(f"Warning: Error resolving {package_name}: {e}")
    
    def _resolve_package_worker(self, package_name: str, spec: PackageSpec, environment: Environment) -> Optional[ResolvedPackage]:
        """Worker function for resolving a single package."""
        if package_name in self.resolved_packages:
            return self.resolved_packages[package_name]
        
        # Find compatible versions
        compatible_versions = self.pypi_client.find_compatible_versions(package_name, spec)
        
        if not compatible_versions:
            print(f"Warning: No compatible versions found for {package_name}")
            return None
        
        # Select the latest compatible version
        selected_version = compatible_versions[-1]
        
        # Check Python compatibility
        if not self.pypi_client.check_python_compatibility(package_name, selected_version, environment.python_version):
            print(f"Warning: {package_name} {selected_version} may not be compatible with Python {environment.python_version}")
        
        # Create resolved package
        resolved_package = ResolvedPackage(
            name=package_name,
            version=selected_version,
            is_direct=True
        )
        
        # Resolve dependencies in parallel
        dependencies = self.pypi_client.get_dependencies(package_name, selected_version)
        if dependencies:
            self._resolve_dependencies_parallel(dependencies, environment, resolved_package)
        
        return resolved_package
    
    def _resolve_dependencies_parallel(self, dependencies: List[str], environment: Environment, parent_package: ResolvedPackage):
        """Resolve dependencies for a package in parallel."""
        # Parse dependency strings
        dep_specs = []
        for dep in dependencies:
            dep_spec = self._parse_dependency_string(dep)
            if dep_spec:
                dep_specs.append((dep_spec.name, dep_spec))
        
        if not dep_specs:
            return
        
        # Resolve dependencies in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all dependency resolution tasks
            future_to_dep = {
                executor.submit(self._resolve_dependency_worker, dep_name, dep_spec, environment): dep_name
                for dep_name, dep_spec in dep_specs
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_dep):
                dep_name = future_to_dep[future]
                try:
                    resolved_dep = future.result()
                    if resolved_dep:
                        self.resolved_packages[dep_name] = resolved_dep
                        parent_package.dependencies.append(dep_name)
                except Exception as e:
                    print(f"Warning: Error resolving dependency {dep_name}: {e}")
    
    def _resolve_dependency_worker(self, dep_name: str, dep_spec: PackageSpec, environment: Environment) -> Optional[ResolvedPackage]:
        """Worker function for resolving a dependency."""
        if dep_name in self.resolved_packages:
            return self.resolved_packages[dep_name]
        
        # Find compatible versions
        compatible_versions = self.pypi_client.find_compatible_versions(dep_name, dep_spec)
        
        if not compatible_versions:
            print(f"Warning: No compatible versions found for dependency {dep_name}")
            return None
        
        # Select the latest compatible version
        selected_version = compatible_versions[-1]
        
        # Create resolved package
        resolved_package = ResolvedPackage(
            name=dep_name,
            version=selected_version,
            is_direct=False
        )
        
        # Resolve nested dependencies (recursive but with parallel processing)
        dependencies = self.pypi_client.get_dependencies(dep_name, selected_version)
        if dependencies:
            self._resolve_dependencies_parallel(dependencies, environment, resolved_package)
        
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
        """Optimize package versions for better compatibility using parallel processing."""
        start_time = time.time()
        
        # Prepare package optimization tasks
        optimization_tasks = []
        for package in resolution_result.packages:
            optimization_tasks.append((package.name, package))
        
        optimized_packages = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all optimization tasks
            future_to_package = {
                executor.submit(self._optimize_package_worker, package_name, package): package_name
                for package_name, package in optimization_tasks
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_package):
                package_name = future_to_package[future]
                try:
                    optimized_package = future.result()
                    if optimized_package:
                        optimized_packages.append(optimized_package)
                except Exception as e:
                    print(f"Warning: Error optimizing {package_name}: {e}")
        
        optimization_time = time.time() - start_time
        print(f"Optimization completed in {optimization_time:.2f} seconds")
        
        return ResolutionResult(
            packages=optimized_packages,
            conflicts=resolution_result.conflicts,
            warnings=resolution_result.warnings,
            success=resolution_result.success,
            dependency_tree=resolution_result.dependency_tree
        )
    
    def _optimize_package_worker(self, package_name: str, package: ResolvedPackage) -> Optional[ResolvedPackage]:
        """Worker function for optimizing a single package version."""
        # Try to find a more recent version that's still compatible
        available_versions = self.pypi_client.get_available_versions(package_name)
        
        # Find the latest version that satisfies all constraints
        best_version = package.version
        for version in reversed(available_versions):
            if self._is_version_compatible(package_name, version):
                best_version = version
                break
        
        optimized_package = ResolvedPackage(
            name=package.name,
            version=best_version,
            dependencies=package.dependencies,
            conflicts=package.conflicts,
            is_direct=package.is_direct
        )
        
        return optimized_package
    
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
