"""
Parallel PyPI client for fetching package information efficiently.
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any, Tuple
from packaging.version import Version, parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..models import PackageInfo, PackageSpec


class ParallelPyPIClient:
    """Parallel client for interacting with the Python Package Index."""
    
    def __init__(self, max_workers: int = 10, timeout: int = 10):
        self.base_url = "https://pypi.org/pypi"
        self.max_workers = max_workers
        self.timeout = timeout
        self.session = None
        self._headers = {
            'User-Agent': 'Python-Package-Manager/1.0.0'
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers=self._headers,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def get_package_info_async(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Fetch package information from PyPI asynchronously."""
        try:
            url = f"{self.base_url}/{package_name}/json"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Warning: Could not fetch info for {package_name}: HTTP {response.status}")
                    return None
        except Exception as e:
            print(f"Warning: Could not fetch info for {package_name}: {e}")
            return None
    
    async def get_packages_info_async(self, package_names: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """Fetch information for multiple packages concurrently."""
        tasks = [self.get_package_info_async(name) for name in package_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        package_info = {}
        for package_name, result in zip(package_names, results):
            if isinstance(result, Exception):
                print(f"Warning: Error fetching {package_name}: {result}")
                package_info[package_name] = None
            else:
                package_info[package_name] = result
        
        return package_info
    
    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for fetching package information."""
        try:
            import requests
            session = requests.Session()
            session.headers.update(self._headers)
            url = f"{self.base_url}/{package_name}/json"
            response = session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Warning: Could not fetch info for {package_name}: {e}")
            return None
    
    def get_packages_info_parallel(self, package_names: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """Fetch information for multiple packages using thread pool."""
        package_info = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all requests
            future_to_package = {
                executor.submit(self.get_package_info, name): name 
                for name in package_names
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_package):
                package_name = future_to_package[future]
                try:
                    result = future.result()
                    package_info[package_name] = result
                except Exception as e:
                    print(f"Warning: Error fetching {package_name}: {e}")
                    package_info[package_name] = None
        
        return package_info
    
    def get_available_versions(self, package_name: str) -> List[str]:
        """Get all available versions for a package."""
        package_info = self.get_package_info(package_name)
        if not package_info:
            return []
        
        versions = list(package_info.get('releases', {}).keys())
        # Sort versions properly
        return sorted(versions, key=parse)
    
    def get_available_versions_batch(self, package_names: List[str]) -> Dict[str, List[str]]:
        """Get available versions for multiple packages in parallel."""
        package_info_batch = self.get_packages_info_parallel(package_names)
        versions_batch = {}
        
        for package_name, package_info in package_info_batch.items():
            if package_info:
                versions = list(package_info.get('releases', {}).keys())
                versions_batch[package_name] = sorted(versions, key=parse)
            else:
                versions_batch[package_name] = []
        
        return versions_batch
    
    def get_package_metadata(self, package_name: str, version: str) -> Optional[PackageInfo]:
        """Get detailed metadata for a specific package version."""
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
        
        return PackageInfo(
            name=package_name,
            version=version,
            dependencies=dependencies,
            requires_python=release_info.get('requires_python'),
            platform_specific=release_info.get('platform') != 'any',
            summary=release_info.get('summary'),
            description=release_info.get('description')
        )
    
    def find_compatible_versions(self, package_name: str, spec: PackageSpec) -> List[str]:
        """Find versions compatible with the given specification."""
        available_versions = self.get_available_versions(package_name)
        compatible_versions = []
        
        for version in available_versions:
            try:
                parsed_version = Version(version)
                if spec.specifier_set.contains(parsed_version):
                    compatible_versions.append(version)
            except Exception:
                continue
        
        return compatible_versions
    
    def find_compatible_versions_batch(self, package_specs: List[Tuple[str, PackageSpec]]) -> Dict[str, List[str]]:
        """Find compatible versions for multiple packages in parallel."""
        package_names = [spec[0] for spec in package_specs]
        versions_batch = self.get_available_versions_batch(package_names)
        
        compatible_versions_batch = {}
        for (package_name, spec), available_versions in zip(package_specs, versions_batch.values()):
            compatible_versions = []
            for version in available_versions:
                try:
                    parsed_version = Version(version)
                    if spec.specifier_set.contains(parsed_version):
                        compatible_versions.append(version)
                except Exception:
                    continue
            compatible_versions_batch[package_name] = compatible_versions
        
        return compatible_versions_batch
    
    def get_dependencies(self, package_name: str, version: str) -> List[str]:
        """Get dependencies for a specific package version."""
        metadata = self.get_package_metadata(package_name, version)
        if metadata:
            return metadata.dependencies
        return []
    
    def get_dependencies_batch(self, package_versions: List[Tuple[str, str]]) -> Dict[str, List[str]]:
        """Get dependencies for multiple package versions in parallel."""
        dependencies_batch = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all dependency requests
            future_to_package = {
                executor.submit(self.get_dependencies, name, version): (name, version)
                for name, version in package_versions
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_package):
                package_name, version = future_to_package[future]
                try:
                    dependencies = future.result()
                    dependencies_batch[package_name] = dependencies
                except Exception as e:
                    print(f"Warning: Error fetching dependencies for {package_name} {version}: {e}")
                    dependencies_batch[package_name] = []
        
        return dependencies_batch
    
    def check_python_compatibility(self, package_name: str, version: str, python_version: str) -> bool:
        """Check if a package version is compatible with the given Python version."""
        metadata = self.get_package_metadata(package_name, version)
        if not metadata or not metadata.requires_python:
            return True
        
        try:
            from packaging.specifiers import SpecifierSet
            spec = SpecifierSet(metadata.requires_python)
            return spec.contains(python_version)
        except Exception:
            return True
