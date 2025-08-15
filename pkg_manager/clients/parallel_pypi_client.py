"""
Optimized parallel PyPI client with caching, smart filtering, and concurrent processing.
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any, Set
from packaging.version import Version, parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..models import PackageInfo, PackageSpec, python_version_manager


class OptimizedParallelPyPIClient:
    """Optimized parallel client for interacting with the Python Package Index."""
    
    def __init__(self, max_workers: int = 10, timeout: int = 30, cache_ttl: int = 3600, max_versions_per_package: int = 50):
        self.base_url = "https://pypi.org/pypi"
        self.max_workers = max_workers
        self.timeout = timeout
        
        # Performance settings
        self.cache_ttl = cache_ttl
        self.max_versions_per_package = max_versions_per_package
        
        # Caches
        self._package_info_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._compatibility_cache: Dict[str, bool] = {}
        
        # Statistics for monitoring
        self.stats = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'versions_checked': 0,
            'versions_pruned': 0,
            'parallel_requests': 0
        }
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid."""
        if key not in self._cache_timestamps:
            return False
        return time.time() - self._cache_timestamps[key] < self.cache_ttl
    
    def _cache_key(self, package_name: str, version: str = None) -> str:
        """Generate cache key for package data."""
        if version:
            return f"{package_name}:{version}"
        return package_name
    
    async def _fetch_package_info_async(self, session: aiohttp.ClientSession, package_name: str) -> Optional[Dict[str, Any]]:
        """Fetch package information asynchronously."""
        cache_key = self._cache_key(package_name)
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            self.stats['cache_hits'] += 1
            return self._package_info_cache[cache_key]
        
        # Fetch from API
        self.stats['cache_misses'] += 1
        self.stats['api_calls'] += 1
        self.stats['parallel_requests'] += 1
        
        try:
            url = f"{self.base_url}/{package_name}/json"
            async with session.get(url, timeout=self.timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Cache the result
                    self._package_info_cache[cache_key] = data
                    self._cache_timestamps[cache_key] = time.time()
                    
                    return data
                else:
                    print(f"Warning: Could not fetch info for {package_name}: HTTP {response.status}")
                    return None
        except Exception as e:
            print(f"Warning: Could not fetch info for {package_name}: {e}")
            return None
    
    async def get_package_info_async(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Get package information asynchronously."""
        async with aiohttp.ClientSession() as session:
            return await self._fetch_package_info_async(session, package_name)
    
    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Get package information synchronously."""
        cache_key = self._cache_key(package_name)
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            self.stats['cache_hits'] += 1
            return self._package_info_cache[cache_key]
        
        # Use asyncio to run the async version
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.get_package_info_async(package_name))
    
    def get_multiple_package_info(self, package_names: List[str]) -> List[Optional[Dict[str, Any]]]:
        """Get package information for multiple packages synchronously."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Get package info for all packages concurrently
        package_info_results = loop.run_until_complete(
            self.get_multiple_package_info_async(package_names)
        )
        
        # Return as a list in the same order as package_names
        return [package_info_results.get(name) for name in package_names]
    
    async def get_multiple_package_info_async(self, package_names: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """Fetch multiple package information concurrently."""
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_package_info_async(session, name) for name in package_names]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            return {
                package_name: result if not isinstance(result, Exception) else None
                for package_name, result in zip(package_names, results)
            }
    
    def get_available_versions(self, package_name: str) -> List[str]:
        """Get available versions with smart filtering."""
        package_info = self.get_package_info(package_name)
        if not package_info:
            return []
        
        versions = list(package_info.get('releases', {}).keys())
        
        # Sort versions properly
        sorted_versions = sorted(versions, key=parse)
        
        # Apply smart filtering to limit the number of versions to check
        if len(sorted_versions) > self.max_versions_per_package:
            # Keep the latest versions (most likely to be compatible)
            sorted_versions = sorted_versions[-self.max_versions_per_package:]
            self.stats['versions_pruned'] += len(versions) - len(sorted_versions)
        
        return sorted_versions
    
    def get_package_metadata(self, package_name: str, version: str) -> Optional[PackageInfo]:
        """Get detailed metadata for a specific package version with caching."""
        cache_key = self._cache_key(package_name, version)
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            self.stats['cache_hits'] += 1
            return self._package_info_cache[cache_key]
        
        # Fetch from API
        self.stats['cache_misses'] += 1
        self.stats['api_calls'] += 1
        
        package_info = self.get_package_info(package_name)
        if not package_info:
            return None
        
        releases = package_info.get('releases', {})
        if version not in releases:
            return None
        
        release_info = releases[version][0] if releases[version] else {}
        
        # Extract dependencies
        dependencies = []
        if 'requires_dist' in release_info:
            dependencies = release_info['requires_dist']
        
        metadata = PackageInfo(
            name=package_name,
            version=version,
            dependencies=dependencies,
            requires_python=release_info.get('requires_python'),
            platform_specific=release_info.get('platform') != 'any',
            summary=release_info.get('summary'),
            description=release_info.get('description')
        )
        
        # Cache the result
        self._package_info_cache[cache_key] = metadata
        self._cache_timestamps[cache_key] = time.time()
        
        return metadata
    
    def check_python_compatibility(self, package_name: str, version: str, python_version: str) -> bool:
        """Check if a package version is compatible with the given Python version."""
        # Create cache key for compatibility check
        cache_key = f"compat:{package_name}:{version}:{python_version}"
        
        if cache_key in self._compatibility_cache:
            self.stats['cache_hits'] += 1
            return self._compatibility_cache[cache_key]
        
        self.stats['cache_misses'] += 1
        self.stats['versions_checked'] += 1
        
        metadata = self.get_package_metadata(package_name, version)
        if not metadata or not metadata.requires_python:
            result = True
        else:
            result = python_version_manager.check_compatibility(metadata.requires_python, python_version)
        
        # Cache the result
        self._compatibility_cache[cache_key] = result
        return result
    
    def find_python_compatible_versions(
        self, 
        package_name: str, 
        python_version: str, 
        spec: PackageSpec = None,
        max_versions: int = 10
    ) -> List[str]:
        """Find versions compatible with the given Python version with early termination."""
        available_versions = self.get_available_versions(package_name)
        compatible_versions = []
        
        # Process versions in reverse order (latest first) for early termination
        for version in reversed(available_versions):
            try:
                # Check if version satisfies the spec (if provided)
                if spec:
                    parsed_version = Version(version)
                    if not spec.specifier_set.contains(parsed_version):
                        continue
                
                # Check Python compatibility
                if self.check_python_compatibility(package_name, version, python_version):
                    compatible_versions.append(version)
                    
                    # Early termination: if we have enough compatible versions, stop
                    if len(compatible_versions) >= max_versions:
                        break
                        
            except Exception:
                continue
        
        # Return in ascending order (oldest to newest)
        return list(reversed(compatible_versions))
    
    def find_optimal_version(
        self, 
        package_name: str, 
        python_version: str, 
        spec: PackageSpec = None,
        prefer_stable: bool = True
    ) -> Optional[str]:
        """Find the optimal version with smart selection."""
        compatible_versions = self.find_python_compatible_versions(package_name, python_version, spec, max_versions=5)
        
        if not compatible_versions:
            return None
        
        if prefer_stable:
            # Prefer stable versions (no alpha, beta, rc, dev suffixes)
            stable_versions = [
                v for v in compatible_versions 
                if not any(suffix in v.lower() for suffix in ['alpha', 'beta', 'rc', 'dev', 'pre'])
            ]
            if stable_versions:
                return stable_versions[-1]  # Latest stable version
        
        # Return the latest compatible version
        return compatible_versions[-1]
    
    def get_dependencies(self, package_name: str, version: str) -> List[str]:
        """Get dependencies for a specific package version."""
        metadata = self.get_package_metadata(package_name, version)
        if metadata:
            return metadata.dependencies
        return []
    
    def get_python_compatibility_info(self, package_name: str, version: str, python_version: str) -> Dict[str, Any]:
        """Get detailed compatibility information for a package version."""
        metadata = self.get_package_metadata(package_name, version)
        is_compatible = self.check_python_compatibility(package_name, version, python_version)
        
        # Get enhanced compatibility info
        compatibility_info = python_version_manager.get_compatibility_info(
            metadata.requires_python if metadata else None, 
            python_version
        )
        
        return {
            'package_name': package_name,
            'version': version,
            'python_version': python_version,
            'is_compatible': is_compatible,
            'requires_python': metadata.requires_python if metadata else None,
            'dependencies': metadata.dependencies if metadata else [],
            'summary': metadata.summary if metadata else None,
            'version_type': compatibility_info['version_type'],
            'parsed_version': compatibility_info['parsed_version']
        }
    
    def resolve_packages_parallel(self, package_specs: List[PackageSpec], python_version: str) -> Dict[str, str]:
        """Resolve multiple packages in parallel for optimal performance."""
        # Pre-fetch package information for all packages
        package_names = [spec.name for spec in package_specs]
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Fetch package info for all packages concurrently
        package_info_results = loop.run_until_complete(
            self.get_multiple_package_info_async(package_names)
        )
        
        # Resolve versions using ThreadPoolExecutor for CPU-bound operations
        resolved_versions = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Create tasks for version resolution
            future_to_spec = {
                executor.submit(self._resolve_single_package, spec, python_version): spec
                for spec in package_specs
            }
            
            # Collect results
            for future in as_completed(future_to_spec):
                spec = future_to_spec[future]
                try:
                    version = future.result()
                    if version:
                        resolved_versions[spec.name] = version
                except Exception as e:
                    print(f"Error resolving {spec.name}: {e}")
        
        return resolved_versions
    
    def _resolve_single_package(self, spec: PackageSpec, python_version: str) -> Optional[str]:
        """Resolve a single package (for use with ThreadPoolExecutor)."""
        return self.find_optimal_version(spec.name, python_version, spec)
    
    def clear_cache(self):
        """Clear all caches."""
        self._package_info_cache.clear()
        self._cache_timestamps.clear()
        self._compatibility_cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            **self.stats,
            'cache_size': len(self._package_info_cache),
            'compatibility_cache_size': len(self._compatibility_cache)
        }
    
    def get_cache_efficiency(self) -> float:
        """Get cache efficiency as a percentage."""
        total_requests = self.stats['cache_hits'] + self.stats['cache_misses']
        if total_requests == 0:
            return 0.0
        return (self.stats['cache_hits'] / total_requests) * 100
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        return {
            **self.get_stats(),
            'cache_efficiency': self.get_cache_efficiency()
        }
    
    def reset_stats(self):
        """Reset performance statistics."""
        self.stats = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'versions_checked': 0,
            'versions_pruned': 0,
            'parallel_requests': 0
        }
