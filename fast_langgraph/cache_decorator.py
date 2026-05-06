"""
Python wrapper for the Rust cached decorator to provide Pythonic interface.
"""

from typing import Any, Callable, Optional, TypeVar

from .fast_langgraph import RustFunctionCache

F = TypeVar("F", bound=Callable[..., Any])


class _CachedWrapper:
    """Internal type for the cached decorator wrapper to satisfy mypy."""

    def __init__(self, func: Callable[..., Any], cache: RustFunctionCache) -> None:
        self.__wrapped__ = func
        self._cache = cache
        self.__name__ = getattr(func, "__name__", "cached_function")
        self.__doc__ = getattr(func, "__doc__", None)

    def __repr__(self) -> str:
        return f"<cached wrapper for {self.__name__}>"

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        result = self._cache.get(args, kwargs if kwargs else None)
        if result is not None:
            return result
        result = self.__wrapped__(*args, **kwargs)
        self._cache.put(args, result, kwargs if kwargs else None)
        return result

    def cache_stats(self) -> Any:
        return self._cache.stats()

    def cache_clear(self) -> None:
        self._cache.clear()

    def cache_contains(self, *args: Any, **kwargs: Any) -> bool:
        return self._cache.contains(args, kwargs if kwargs else None)  # type: ignore[no-any-return]

    def cache_invalidate(self, *args: Any, **kwargs: Any) -> bool:
        return self._cache.invalidate(args, kwargs if kwargs else None)  # type: ignore[no-any-return]


def cached(func: Optional[Callable[..., Any]] = None, *, max_size: int = 1000) -> Any:
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

    def decorator(f: Callable[..., Any]) -> _CachedWrapper:
        cache = RustFunctionCache(max_size=max_size)
        wrapper = _CachedWrapper(f, cache)
        return wrapper

    # Support both @cached and @cached(max_size=100)
    if func is None:
        # Called with parameters: @cached(max_size=100)
        return decorator
    else:
        # Called without parameters: @cached
        return decorator(func)


__all__ = ["cached"]
