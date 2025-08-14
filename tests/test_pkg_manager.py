#!/usr/bin/env python3
"""
Test script for the Python Package Manager.
"""

import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pkg_manager.core import PackageManager


def test_basic_resolution():
    """Test basic package resolution."""
    print("Testing basic package resolution...")
    
    manager = PackageManager()
    
    # Test with simple packages
    packages = "requests>=2.31.0,pandas>=1.5.0"
    
    result = manager.run(
        packages=packages,
        python_version="3.9",
        output_dir="./test_output",
        display_result=True
    )
    
    print(f"Resolution successful: {result['resolution_result'].success}")
    print(f"Number of packages resolved: {len(result['resolution_result'].packages)}")
    
    return result


def test_file_input():
    """Test package resolution from file."""
    print("\nTesting package resolution from file...")
    
    manager = PackageManager()
    
    result = manager.run(
        input_file="tests/example_packages.txt",
        python_version="3.9",
        output_dir="./test_output_file",
        display_result=True
    )
    
    print(f"Resolution successful: {result['resolution_result'].success}")
    print(f"Number of packages resolved: {len(result['resolution_result'].packages)}")
    
    return result


def test_conflict_detection():
    """Test conflict detection."""
    print("\nTesting conflict detection...")
    
    manager = PackageManager()
    
    # These packages might have conflicting dependencies
    packages = "django>=4.0.0,djangorestframework>=3.14.0,django-cors-headers>=4.0.0"
    
    result = manager.run(
        packages=packages,
        python_version="3.9",
        output_dir="./test_output_conflicts",
        display_result=True
    )
    
    print(f"Resolution successful: {result['resolution_result'].success}")
    if result['resolution_result'].conflicts:
        print("Conflicts detected:")
        for conflict in result['resolution_result'].conflicts:
            print(f"  - {conflict}")
    
    return result


if __name__ == "__main__":
    print("Python Package Manager - Test Suite")
    print("=" * 50)
    
    try:
        # Run tests
        test_basic_resolution()
        test_file_input()
        test_conflict_detection()
        
        print("\n" + "=" * 50)
        print("All tests completed!")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1) 