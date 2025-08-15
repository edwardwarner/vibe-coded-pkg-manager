"""
Dependency resolvers for finding optimal package combinations.
"""

from .resolver import OptimizedDependencyResolver
from .parallel_resolver import OptimizedParallelDependencyResolver

__all__ = [
    "OptimizedDependencyResolver",
    "OptimizedParallelDependencyResolver"
]
