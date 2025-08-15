"""
Python Package Manager

A smart package manager that finds optimal package combinations and generates installation scripts.
"""

__version__ = "1.0.0"
__author__ = "Package Manager Team"

from .core import PackageManager, ParallelPackageManager
from .resolvers import OptimizedDependencyResolver, OptimizedParallelDependencyResolver
from .generators import ScriptGenerator
from .clients import OptimizedPyPIClient, OptimizedParallelPyPIClient
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
    "OptimizedDependencyResolver",
    "OptimizedParallelDependencyResolver",
    "ScriptGenerator",
    "OptimizedPyPIClient",
    "OptimizedParallelPyPIClient",
    "PackageSpec",
    "PackageInfo",
    "ResolvedPackage", 
    "Environment",
    "ResolutionResult",
    "PackageConflict"
] 