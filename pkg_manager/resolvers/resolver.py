"""
Optimized dependency resolver with smart search strategies and performance optimizations.
"""

import re
import time
from typing import List, Dict, Set, Optional, Tuple, Any
from packaging.specifiers import SpecifierSet
from packaging.version import Version, parse
from ..models import PackageSpec, ResolvedPackage, ResolutionResult, Environment, PackageConflict, ConflictResolutionStrategy
from ..clients.pypi_client import OptimizedPyPIClient
from ..clients.parallel_pypi_client import OptimizedParallelPyPIClient
from .conflict_resolver import ConflictResolver


class OptimizedDependencyResolver:
    """Optimized dependency resolver with smart search strategies."""
    
    def __init__(self, use_parallel: bool = False, max_workers: int = 10, cache_ttl: int = 3600):
        self.use_parallel = use_parallel
        
        if use_parallel:
            self.pypi_client = OptimizedParallelPyPIClient(
                max_workers=max_workers, 
                cache_ttl=cache_ttl,
                max_versions_per_package=30  # Reduced for faster processing
            )
        else:
            self.pypi_client = OptimizedPyPIClient(
                cache_ttl=cache_ttl,
                max_versions_per_package=30  # Reduced for faster processing
            )
        
        self.conflict_resolver = ConflictResolver(self.pypi_client)
        self.resolved_packages: Dict[str, ResolvedPackage] = {}
        self.package_constraints: Dict[str, List[SpecifierSet]] = {}
        self.conflicts: List[PackageConflict] = []
        
        # Performance tracking
        self.performance_stats = {
            'resolution_time': 0,
            'packages_resolved': 0,
            'cache_efficiency': 0
        }
    
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
        """Resolve dependencies with optimized performance."""
        start_time = time.time()
        
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
        
        # Use optimized resolution strategy
        if self.use_parallel and len(specs) > 3:
            # Use parallel resolution for larger package lists
            self._resolve_packages_parallel(specs, environment)
        else:
            # Use sequential resolution for smaller lists
            for spec in specs:
                self._resolve_package_optimized(spec, environment)
        
        # Detect conflicts using the conflict resolver
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
        
        # Update performance stats
        self.performance_stats['resolution_time'] = time.time() - start_time
        self.performance_stats['packages_resolved'] = len(self.resolved_packages)
        
        # Calculate cache efficiency
        client_stats = self.pypi_client.get_stats()
        total_requests = client_stats['cache_hits'] + client_stats['cache_misses']
        if total_requests > 0:
            self.performance_stats['cache_efficiency'] = client_stats['cache_hits'] / total_requests
        
        return ResolutionResult(
            packages=list(self.resolved_packages.values()),
            conflicts=[conflict.reason for conflict in self.conflicts],
            package_conflicts=self.conflicts,
            resolutions=resolutions,
            success=len(self.conflicts) == 0 or len(resolutions) > 0,
            dependency_tree=dependency_tree,
            conflict_resolution_strategy=conflict_strategy
        )
    
    def _resolve_packages_parallel(self, specs: List[PackageSpec], environment: Environment):
        """Resolve packages using parallel processing."""
        if hasattr(self.pypi_client, 'resolve_packages_parallel'):
            # Use the optimized parallel resolution
            resolved_versions = self.pypi_client.resolve_packages_parallel(specs, environment.python_version)
            
            # Create resolved packages
            for spec in specs:
                if spec.name in resolved_versions:
                    version = resolved_versions[spec.name]
                    
                    # Verify Python compatibility
                    is_compatible = self.pypi_client.check_python_compatibility(
                        spec.name, version, environment.python_version
                    )
                    
                    if is_compatible:
                        print(f"✅ {spec.name} {version} is compatible with Python {environment.python_version}")
                    else:
                        print(f"Warning: {spec.name} {version} may not be compatible with Python {environment.python_version}")
                    
                    # Create resolved package
                    resolved_package = ResolvedPackage(
                        name=spec.name,
                        version=version,
                        is_direct=True
                    )
                    
                    self.resolved_packages[spec.name] = resolved_package
                    
                    # Resolve dependencies (simplified for parallel processing)
                    dependencies = self.pypi_client.get_dependencies(spec.name, version)
                    for dep in dependencies[:5]:  # Limit dependencies for performance
                        dep_spec = self._parse_dependency_string(dep)
                        if dep_spec and dep_spec.name not in self.resolved_packages:
                            self._resolve_package_optimized(dep_spec, environment)
                            resolved_package.dependencies.append(dep_spec.name)
    
    def _resolve_package_optimized(self, spec: PackageSpec, environment: Environment) -> Optional[ResolvedPackage]:
        """Resolve a single package with optimizations."""
        if spec.name in self.resolved_packages:
            return self.resolved_packages[spec.name]
        
        # Use optimized version finding with early termination
        selected_version = self.pypi_client.find_optimal_version(
            spec.name, 
            environment.python_version, 
            spec,
            prefer_stable=True
        )
        
        if not selected_version:
            # Fallback to original method if no optimal version found
            compatible_versions = self.pypi_client.find_python_compatible_versions(
                spec.name, environment.python_version, spec, max_versions=5
            )
            if not compatible_versions:
                print(f"Warning: No compatible versions found for {spec.name}")
                return None
            else:
                selected_version = compatible_versions[-1]
                print(f"Warning: No optimal version found for {spec.name}, using {selected_version}")
        
        # Verify Python compatibility
        is_compatible = self.pypi_client.check_python_compatibility(
            spec.name, selected_version, environment.python_version
        )
        
        if is_compatible:
            print(f"✅ {spec.name} {selected_version} is compatible with Python {environment.python_version}")
        else:
            print(f"Warning: {spec.name} {selected_version} may not be compatible with Python {environment.python_version}")
        
        # Create resolved package
        resolved_package = ResolvedPackage(
            name=spec.name,
            version=selected_version,
            is_direct=True
        )
        
        self.resolved_packages[spec.name] = resolved_package
        
        # Resolve dependencies (limited for performance)
        dependencies = self.pypi_client.get_dependencies(spec.name, selected_version)
        for dep in dependencies[:5]:  # Limit to 5 dependencies for performance
            dep_spec = self._parse_dependency_string(dep)
            if dep_spec and dep_spec.name not in self.resolved_packages:
                self._resolve_package_optimized(dep_spec, environment)
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
                    package.name, environment.python_version, max_versions=3
                )
                
                if compatible_versions and compatible_versions[-1] != best_version:
                    # Check if the newer version is significantly better
                    newer_version = compatible_versions[-1]
                    if self._is_version_improvement(best_version, newer_version):
                        best_version = newer_version
            
            # Create optimized package
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
            package_conflicts=resolution_result.package_conflicts,
            resolutions=resolution_result.resolutions,
            warnings=resolution_result.warnings,
            success=resolution_result.success,
            dependency_tree=resolution_result.dependency_tree,
            conflict_resolution_strategy=resolution_result.conflict_resolution_strategy
        )
    
    def _is_version_improvement(self, current_version: str, new_version: str) -> bool:
        """Check if a new version is a significant improvement."""
        try:
            current = parse(current_version)
            new = parse(new_version)
            
            # Consider it an improvement if it's a newer major or minor version
            # or if it's a significantly newer patch version
            if new.major > current.major:
                return True
            elif new.major == current.major and new.minor > current.minor:
                return True
            elif new.major == current.major and new.minor == current.minor:
                # Only consider patch improvements if they're significant
                return new.micro > current.micro + 5  # At least 5 patch versions newer
            
            return False
        except Exception:
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        client_stats = self.pypi_client.get_stats()
        
        return {
            **self.performance_stats,
            **client_stats,
            'total_requests': client_stats['cache_hits'] + client_stats['cache_misses'],
            'cache_hit_rate': client_stats['cache_hits'] / (client_stats['cache_hits'] + client_stats['cache_misses']) if (client_stats['cache_hits'] + client_stats['cache_misses']) > 0 else 0,
            'versions_per_package': client_stats['versions_checked'] / max(self.performance_stats['packages_resolved'], 1),
            'parallel_processing': self.use_parallel
        }
    
    def clear_cache(self):
        """Clear all caches."""
        self.pypi_client.clear_cache()
    
    def reset_stats(self):
        """Reset all statistics."""
        self.pypi_client.reset_stats()
        self.performance_stats = {
            'resolution_time': 0,
            'packages_resolved': 0,
            'cache_efficiency': 0
        }
