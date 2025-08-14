"""
Dependency resolvers for finding optimal package combinations.
"""

from .resolver import DependencyResolver
from .parallel_resolver import ParallelDependencyResolver

__all__ = [
    "DependencyResolver",
    "ParallelDependencyResolver"
]
