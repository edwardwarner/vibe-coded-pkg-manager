"""
Python Package Manager

A smart package manager that finds optimal package combinations and generates installation scripts.
"""

__version__ = "1.0.0"
__author__ = "Package Manager Team"

from .core import PackageManager, ParallelPackageManager
from .resolvers import DependencyResolver, ParallelDependencyResolver
from .generators import ScriptGenerator
from .clients import PyPIClient, ParallelPyPIClient
from .models import (
    PackageSpec,
    PackageInfo,
    ResolvedPackage,
    Environment,
    ResolutionResult,
    PackageConflict
)

__all__ = [
    "PackageManager",
    "ParallelPackageManager", 
    "DependencyResolver",
    "ParallelDependencyResolver",
    "ScriptGenerator",
    "PyPIClient",
    "ParallelPyPIClient",
    "PackageSpec",
    "PackageInfo",
    "ResolvedPackage", 
    "Environment",
    "ResolutionResult",
    "PackageConflict"
] 