"""
Python version handling and compatibility utilities.
"""

import re
from typing import List, Dict, Optional, Tuple, Set
from packaging.version import Version, parse
from packaging.specifiers import SpecifierSet


class PythonVersionManager:
    """Manages Python version parsing, validation, and compatibility checking."""
    
    # Major Python versions with their latest patch versions
    PYTHON_VERSIONS = {
        # Python 3.7 (EOL: June 2023)
        "3.7": {
            "latest": "3.7.18",
            "supported": ["3.7.0", "3.7.1", "3.7.2", "3.7.3", "3.7.4", "3.7.5", "3.7.6", 
                         "3.7.7", "3.7.8", "3.7.9", "3.7.10", "3.7.11", "3.7.12", "3.7.13",
                         "3.7.14", "3.7.15", "3.7.16", "3.7.17", "3.7.18"],
            "status": "EOL"
        },
        # Python 3.8 (EOL: October 2024)
        "3.8": {
            "latest": "3.8.18",
            "supported": ["3.8.0", "3.8.1", "3.8.2", "3.8.3", "3.8.4", "3.8.5", "3.8.6",
                         "3.8.7", "3.8.8", "3.8.9", "3.8.10", "3.8.11", "3.8.12", "3.8.13",
                         "3.8.14", "3.8.15", "3.8.16", "3.8.17", "3.8.18"],
            "status": "EOL"
        },
        # Python 3.9 (EOL: October 2025)
        "3.9": {
            "latest": "3.9.18",
            "supported": ["3.9.0", "3.9.1", "3.9.2", "3.9.3", "3.9.4", "3.9.5", "3.9.6",
                         "3.9.7", "3.9.8", "3.9.9", "3.9.10", "3.9.11", "3.9.12", "3.9.13",
                         "3.9.14", "3.9.15", "3.9.16", "3.9.17", "3.9.18"],
            "status": "Active"
        },
        # Python 3.10 (EOL: October 2026)
        "3.10": {
            "latest": "3.10.13",
            "supported": ["3.10.0", "3.10.1", "3.10.2", "3.10.3", "3.10.4", "3.10.5", "3.10.6",
                         "3.10.7", "3.10.8", "3.10.9", "3.10.10", "3.10.11", "3.10.12", "3.10.13"],
            "status": "Active"
        },
        # Python 3.11 (EOL: October 2027)
        "3.11": {
            "latest": "3.11.9",
            "supported": ["3.11.0", "3.11.1", "3.11.2", "3.11.3", "3.11.4", "3.11.5", "3.11.6",
                         "3.11.7", "3.11.8", "3.11.9"],
            "status": "Active"
        },
        # Python 3.12 (EOL: October 2028)
        "3.12": {
            "latest": "3.12.10",
            "supported": ["3.12.0", "3.12.1", "3.12.2", "3.12.3", "3.12.4", "3.12.5", "3.12.6",
                         "3.12.7", "3.12.8", "3.12.9", "3.12.10"],
            "status": "Active"
        },
        # Python 3.13 (EOL: October 2029)
        "3.13": {
            "latest": "3.13.5",
            "supported": ["3.13.0", "3.13.1", "3.13.2", "3.13.3", "3.13.4", "3.13.5"],
            "status": "Active"
        }
    }
    
    def __init__(self):
        self._version_cache: Dict[str, Version] = {}
    
    def parse_version(self, version_str: str) -> Optional[Version]:
        """Parse a Python version string into a Version object."""
        if version_str in self._version_cache:
            return self._version_cache[version_str]
        
        try:
            # Handle common version formats
            version_str = version_str.strip()
            
            # Remove 'python' prefix if present
            if version_str.lower().startswith('python'):
                version_str = version_str[6:].strip()
            
            # Parse the version
            version = parse(version_str)
            self._version_cache[version_str] = version
            return version
        except Exception:
            return None
    
    def is_valid_version(self, version_str: str) -> bool:
        """Check if a version string is valid."""
        return self.parse_version(version_str) is not None
    
    def get_version_type(self, version_str: str) -> str:
        """Determine the type of version string (specific, major, or invalid)."""
        version = self.parse_version(version_str)
        if not version:
            return "invalid"
        
        # Check if it's a specific version (has patch number)
        if len(version.release) >= 3:
            return "specific"
        elif len(version.release) == 2:
            return "major"
        else:
            return "invalid"
    
    def expand_vague_version(self, version_str: str) -> List[str]:
        """Expand a vague version (e.g., '3.12') to all supported specific versions."""
        version = self.parse_version(version_str)
        if not version:
            return []
        
        # Get major.minor version
        major_minor = f"{version.release[0]}.{version.release[1]}"
        
        if major_minor in self.PYTHON_VERSIONS:
            return self.PYTHON_VERSIONS[major_minor]["supported"]
        
        return []
    
    def get_latest_version(self, major_minor: str) -> Optional[str]:
        """Get the latest patch version for a major.minor version."""
        if major_minor in self.PYTHON_VERSIONS:
            return self.PYTHON_VERSIONS[major_minor]["latest"]
        return None
    
    def get_supported_versions(self, major_minor: str) -> List[str]:
        """Get all supported specific versions for a major.minor version."""
        if major_minor in self.PYTHON_VERSIONS:
            return self.PYTHON_VERSIONS[major_minor]["supported"]
        return []
    
    def get_version_status(self, major_minor: str) -> str:
        """Get the status of a Python version (Active, EOL, etc.)."""
        if major_minor in self.PYTHON_VERSIONS:
            return self.PYTHON_VERSIONS[major_minor]["status"]
        return "Unknown"
    
    def get_all_supported_versions(self) -> List[str]:
        """Get all supported specific Python versions."""
        all_versions = []
        for major_minor, info in self.PYTHON_VERSIONS.items():
            all_versions.extend(info["supported"])
        return sorted(all_versions, key=parse)
    
    def get_active_versions(self) -> List[str]:
        """Get all active (non-EOL) Python versions."""
        active_versions = []
        for major_minor, info in self.PYTHON_VERSIONS.items():
            if info["status"] == "Active":
                active_versions.extend(info["supported"])
        return sorted(active_versions, key=parse)
    
    def get_latest_versions(self) -> Dict[str, str]:
        """Get the latest version for each major.minor version."""
        return {major_minor: info["latest"] for major_minor, info in self.PYTHON_VERSIONS.items()}
    
    def check_compatibility(self, package_requires_python: str, python_version: str) -> bool:
        """Check if a package's Python requirement is compatible with a Python version."""
        if not package_requires_python:
            return True
        
        try:
            # Parse the package's Python requirement
            spec = SpecifierSet(package_requires_python)
            
            # Parse the Python version
            version = self.parse_version(python_version)
            if not version:
                return False
            
            # Check compatibility
            return spec.contains(version)
        except Exception:
            return True
    
    def get_compatibility_info(self, package_requires_python: str, python_version: str) -> Dict[str, any]:
        """Get detailed compatibility information."""
        is_compatible = self.check_compatibility(package_requires_python, python_version)
        
        return {
            "package_requires_python": package_requires_python,
            "python_version": python_version,
            "is_compatible": is_compatible,
            "version_type": self.get_version_type(python_version),
            "parsed_version": str(self.parse_version(python_version)) if self.parse_version(python_version) else None
        }
    
    def suggest_versions(self, package_requires_python: str) -> List[str]:
        """Suggest Python versions that would be compatible with a package requirement."""
        if not package_requires_python:
            return self.get_all_supported_versions()
        
        try:
            spec = SpecifierSet(package_requires_python)
            compatible_versions = []
            
            for version in self.get_all_supported_versions():
                parsed_version = self.parse_version(version)
                if parsed_version and spec.contains(parsed_version):
                    compatible_versions.append(version)
            
            return compatible_versions
        except Exception:
            return self.get_all_supported_versions()
    
    def format_version_display(self, version_str: str) -> str:
        """Format a version string for display with status information."""
        version = self.parse_version(version_str)
        if not version:
            return f"{version_str} (invalid)"
        
        major_minor = f"{version.release[0]}.{version.release[1]}"
        status = self.get_version_status(major_minor)
        
        if len(version.release) >= 3:
            # Specific version
            return f"{version_str} ({status})"
        else:
            # Major version
            latest = self.get_latest_version(major_minor)
            return f"{version_str} (latest: {latest}, {status})"


# Global instance for easy access
python_version_manager = PythonVersionManager()
