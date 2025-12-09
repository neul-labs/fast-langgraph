"""
Python wrapper for the Rust cached decorator to provide Pythonic interface.
"""

from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from .fast_langgraph import RustFunctionCache

F = TypeVar("F", bound=Callable[..., Any])


def cached(func: Optional[Callable] = None, *, max_size: int = 1000) -> Callable:
    """
    Decorator to cache function results using Rust-based caching.

    Usage:
        @cached
        def expensive_function(x, y):
            return x + y

        @cached(max_size=100)
        def another_function(x):
            return x * 2

    Args:
        func: The function to cache (when used without parameters)
        max_size: Maximum cache size (default: 1000)

    Returns:
        Decorated function with caching enabled
    """

    def decorator(f: Callable) -> Callable:
        cache = RustFunctionCache(max_size=max_size)

        @wraps(f)
        def wrapper(*args, **kwargs):
            # Check cache first
            result = cache.get(args, kwargs if kwargs else None)
            if result is not None:
                return result

            # Cache miss - call original function
            result = f(*args, **kwargs)

            # Store in cache
            cache.put(args, result, kwargs if kwargs else None)

            return result

        # Add cache management methods
        wrapper.cache_stats = lambda: cache.stats()
        wrapper.cache_clear = lambda: cache.clear()
        wrapper.cache_contains = lambda *args, **kwargs: cache.contains(
            args, kwargs if kwargs else None
        )
        wrapper.cache_invalidate = lambda *args, **kwargs: cache.invalidate(
            args, kwargs if kwargs else None
        )
        wrapper.__wrapped__ = f
        wrapper._cache = cache

        return wrapper

    # Support both @cached and @cached(max_size=100)
    if func is None:
        # Called with parameters: @cached(max_size=100)
        return decorator
    else:
        # Called without parameters: @cached
        return decorator(func)


__all__ = ["cached"]
