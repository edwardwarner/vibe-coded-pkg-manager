"""
Optimized parallel dependency resolver with smart search strategies and performance optimizations.
"""

import re
import time
from typing import List, Dict, Set, Optional, Tuple, Any
from packaging.specifiers import SpecifierSet
from packaging.version import Version, parse
from ..models import PackageSpec, ResolvedPackage, ResolutionResult, Environment, PackageConflict, ConflictResolutionStrategy
from ..clients.parallel_pypi_client import OptimizedParallelPyPIClient
from .conflict_resolver import ConflictResolver


class OptimizedParallelDependencyResolver:
    """Optimized parallel dependency resolver with smart search strategies."""
    
    def __init__(self, max_workers: int = 10, cache_ttl: int = 3600):
        self.max_workers = max_workers
        self.pypi_client = OptimizedParallelPyPIClient(
            max_workers=max_workers, 
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
            'cache_efficiency': 0,
            'parallel_workers': max_workers
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
        """Resolve dependencies with optimized parallel performance."""
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
        
        # Resolve packages in parallel
        resolved_packages = self._resolve_packages_parallel(specs, environment)
        
        # Detect and resolve conflicts
        conflicts = self.conflict_resolver.detect_conflicts(resolved_packages, self.package_constraints)
        resolutions = []
        
        if conflicts:
            if conflict_strategy.strategy == "auto":
                resolutions = self.conflict_resolver.resolve_conflicts(conflicts, conflict_strategy, environment)
            elif conflict_strategy.strategy == "manual":
                # For manual strategy, just return the conflicts for user review
                pass
            elif conflict_strategy.strategy == "ignore":
                # Ignore conflicts and continue
                pass
            elif conflict_strategy.strategy == "fail":
                raise ValueError(f"Package conflicts detected: {len(conflicts)} conflicts found")
        
        # Optimize versions
        optimized_packages = self.optimize_versions(resolved_packages, environment)
        
        # Calculate performance stats
        resolution_time = time.time() - start_time
        self.performance_stats.update({
            'resolution_time': resolution_time,
            'packages_resolved': len(optimized_packages),
            'cache_efficiency': self.pypi_client.get_cache_efficiency()
        })
        
        return ResolutionResult(
            packages=optimized_packages,
            environment=environment,
            conflicts=conflicts,
            resolutions=resolutions,
            conflict_resolution_strategy=conflict_strategy,
            performance_stats=self.performance_stats
        )
    
    def _resolve_packages_parallel(self, specs: List[PackageSpec], environment: Environment) -> List[ResolvedPackage]:
        """Resolve packages using parallel processing."""
        # Use the parallel client's batch processing capabilities
        package_names = [spec.name for spec in specs]
        
        # Get package info in parallel using the synchronous method
        package_info_batch = self.pypi_client.get_multiple_package_info(package_names)
        
        resolved_packages = []
        
        for spec, package_info in zip(specs, package_info_batch):
            if package_info:
                # Find Python-compatible versions
                compatible_versions = self.pypi_client.find_python_compatible_versions(
                    spec.name, environment.python_version, spec
                )
                
                if compatible_versions:
                    # Find optimal version
                    optimal_version = self.pypi_client.find_optimal_version(
                        spec.name, environment.python_version, spec
                    )
                    
                    if optimal_version:
                        resolved_package = ResolvedPackage(
                            name=spec.name,
                            version=optimal_version,
                            dependencies=package_info.get('info', {}).get('requires_dist', []) or [],
                            python_compatibility=package_info.get('info', {}).get('requires_python', ''),
                            package_info=package_info
                        )
                        resolved_packages.append(resolved_package)
                        self.resolved_packages[spec.name] = resolved_package
        
        return resolved_packages
    
    def optimize_versions(self, packages: List[ResolvedPackage], environment: Environment) -> List[ResolvedPackage]:
        """Optimize package versions for the given environment."""
        optimized_packages = []
        
        for package in packages:
            # Find Python-compatible versions
            compatible_versions = self.pypi_client.find_python_compatible_versions(
                package.name, environment.python_version
            )
            
            if compatible_versions:
                # Find the best version that satisfies constraints
                constraints = self.package_constraints.get(package.name, [])
                best_version = None
                
                for version in compatible_versions:
                    version_obj = parse(version)
                    
                    # Check if version satisfies all constraints
                    satisfies_all = True
                    for constraint in constraints:
                        if not constraint.contains(version_obj):
                            satisfies_all = False
                            break
                    
                    if satisfies_all:
                        best_version = version
                        break
                
                if best_version:
                    # Update package with optimized version
                    optimized_package = ResolvedPackage(
                        name=package.name,
                        version=best_version,
                        dependencies=package.dependencies,
                        conflicts=package.conflicts,
                        is_direct=package.is_direct
                    )
                    optimized_packages.append(optimized_package)
                else:
                    optimized_packages.append(package)
            else:
                optimized_packages.append(package)
        
        return optimized_packages
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            **self.performance_stats,
            **self.pypi_client.get_performance_stats()
        }
