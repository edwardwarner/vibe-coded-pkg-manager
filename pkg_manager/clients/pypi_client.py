"""
PyPI client for fetching package information.
"""

import requests
import json
from typing import Dict, List, Optional, Any
from packaging.version import Version, parse
from ..models import PackageInfo, PackageSpec


class PyPIClient:
    """Client for interacting with the Python Package Index."""
    
    def __init__(self):
        self.base_url = "https://pypi.org/pypi"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Python-Package-Manager/1.0.0'
        })
    
    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Fetch package information from PyPI."""
        try:
            url = f"{self.base_url}/{package_name}/json"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Warning: Could not fetch info for {package_name}: {e}")
            return None
    
    def get_available_versions(self, package_name: str) -> List[str]:
        """Get all available versions for a package."""
        package_info = self.get_package_info(package_name)
        if not package_info:
            return []
        
        versions = list(package_info.get('releases', {}).keys())
        # Sort versions properly
        return sorted(versions, key=parse)
    
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
    
    def get_dependencies(self, package_name: str, version: str) -> List[str]:
        """Get dependencies for a specific package version."""
        metadata = self.get_package_metadata(package_name, version)
        if metadata:
            return metadata.dependencies
        return []
    
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