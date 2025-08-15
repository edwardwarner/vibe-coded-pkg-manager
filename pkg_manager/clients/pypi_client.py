"""
Optimized PyPI client with caching and smart version filtering for improved performance.
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any, Set
from packaging.version import Version, parse
from functools import lru_cache
from ..models import PackageInfo, PackageSpec, python_version_manager


class OptimizedPyPIClient:
    """Optimized client for interacting with the Python Package Index."""
    
    def __init__(self, cache_ttl: int = 3600, max_versions_per_package: int = 50):
        self.base_url = "https://pypi.org/pypi"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Python-Package-Manager/1.0.0'
        })
        
        # Performance settings
        self.cache_ttl = cache_ttl  # Cache time-to-live in seconds
        self.max_versions_per_package = max_versions_per_package  # Limit versions to check
        
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
            'versions_pruned': 0
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
    
    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Fetch package information from PyPI with caching."""
        cache_key = self._cache_key(package_name)
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            self.stats['cache_hits'] += 1
            return self._package_info_cache[cache_key]
        
        # Fetch from API
        self.stats['cache_misses'] += 1
        self.stats['api_calls'] += 1
        
        try:
            url = f"{self.base_url}/{package_name}/json"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Cache the result
            self._package_info_cache[cache_key] = data
            self._cache_timestamps[cache_key] = time.time()
            
            return data
        except requests.RequestException as e:
            print(f"Warning: Could not fetch info for {package_name}: {e}")
            return None
    
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
    
    def reset_stats(self):
        """Reset performance statistics."""
        self.stats = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'versions_checked': 0,
            'versions_pruned': 0
        }
