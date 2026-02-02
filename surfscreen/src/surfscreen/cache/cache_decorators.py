"""
Cache Decorators

Decorators for automatic result caching and cache invalidation.
"""

import functools
import hashlib
import json
import logging
from typing import Any, Callable, Optional, List, Union, TypeVar

# Python 3.8 compatibility: ParamSpec is only available in Python 3.10+
try:
    from typing import ParamSpec
except ImportError:
    from typing_extensions import ParamSpec

from .cache_manager import get_cache_manager, CacheManager

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')




def cache_result(
    key_prefix: str = "result",
    ttl: Optional[int] = None,
    key_params: Optional[List[str]] = None,
    include_args: bool = True,
    include_kwargs: bool = True,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to cache function results.
    
    Args:
        key_prefix: Prefix for cache key
        ttl: Time-to-live in seconds
        key_params: List of parameter names to include in cache key.
                   If None, includes all parameters.
        include_args: Whether to include positional args in key
        include_kwargs: Whether to include keyword args in key
        
    Returns:
        Decorated function
        
    Example:
        @cache_result(key_prefix="screening", ttl=3600)
        def calculate_energy(structure, engine="mace"):
            # ... expensive calculation ...
            return energy
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            cache = get_cache_manager()
            
            # Generate cache key
            key = _generate_function_key(
                func,
                args if include_args else (),
                kwargs if include_kwargs else {},
                key_prefix,
                key_params,
            )
            
            # Try to get from cache
            cached = cache.get(key)
            if cached is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(
                key,
                result,
                ttl=ttl,
                metadata={
                    "function": func.__name__,
                    "module": func.__module__,
                },
            )
            
            return result
        
        # Add cache control methods
        wrapper.cache_key = lambda *args, **kwargs: _generate_function_key(
            func, args, kwargs, key_prefix, key_params
        )
        wrapper.invalidate = lambda *args, **kwargs: get_cache_manager().delete(
            _generate_function_key(func, args, kwargs, key_prefix, key_params)
        )
        wrapper.uncached = func
        
        return wrapper
    
    return decorator


def cache_result_async(
    key_prefix: str = "result",
    ttl: Optional[int] = None,
    key_params: Optional[List[str]] = None,
) -> Callable:
    """
    Async version of cache_result decorator.
    
    Example:
        @cache_result_async(key_prefix="api")
        async def fetch_data(url: str):
            # ... async operation ...
            return data
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            key = _generate_function_key(
                func, args, kwargs, key_prefix, key_params
            )
            
            cached = cache.get(key)
            if cached is not None:
                logger.debug(f"Cache hit for async {func.__name__}")
                return cached
            
            result = await func(*args, **kwargs)
            
            cache.set(
                key,
                result,
                ttl=ttl,
                metadata={
                    "function": func.__name__,
                    "module": func.__module__,
                    "async": True,
                },
            )
            
            return result
        
        wrapper.uncached = func
        
        return wrapper
    
    return decorator


def invalidate_cache(
    key_pattern: str,
    on_success: bool = True,
    on_error: bool = False,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to invalidate cache entries after function execution.
    
    Args:
        key_pattern: Cache key pattern to invalidate (supports wildcards)
        on_success: Invalidate on successful execution
        on_error: Invalidate even if function raises exception
        
    Returns:
        Decorated function
        
    Example:
        @invalidate_cache(key_pattern="screening:*")
        def clear_all_screening_cache():
            pass
            
        @invalidate_cache(key_pattern="user:{user_id}:*")
        def update_user(user_id: str, data: dict):
            pass
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            cache = get_cache_manager()
            
            # Format pattern with function arguments
            pattern = _format_pattern(key_pattern, args, kwargs, func)
            
            try:
                result = func(*args, **kwargs)
                
                if on_success:
                    deleted = cache.clear(pattern)
                    logger.debug(f"Invalidated {deleted} cache entries: {pattern}")
                
                return result
                
            except Exception as e:
                if on_error:
                    deleted = cache.clear(pattern)
                    logger.debug(f"Invalidated {deleted} cache entries on error: {pattern}")
                raise
        
        return wrapper
    
    return decorator


class CacheAside:
    """
    Cache-aside pattern helper for manual cache management.
    
    Example:
        cache_aside = CacheAside(prefix="calculation")
        
        # Check cache
        result = cache_aside.get(structure_hash, engine)
        if result is None:
            result = expensive_calculation()
            cache_aside.set(structure_hash, engine, result)
    """
    
    def __init__(
        self,
        prefix: str = "calc",
        ttl: Optional[int] = None,
        cache_manager: Optional[CacheManager] = None,
    ):
        """
        Initialize cache-aside helper.
        
        Args:
            prefix: Key prefix
            ttl: Default TTL
            cache_manager: Optional cache manager instance
        """
        self.prefix = prefix
        self.ttl = ttl
        self._cache = cache_manager
    
    @property
    def cache(self) -> CacheManager:
        """Get cache manager."""
        if self._cache is None:
            self._cache = get_cache_manager()
        return self._cache
    
    def make_key(self, *parts: Any) -> str:
        """Create cache key from parts."""
        key_parts = [str(p) for p in parts]
        combined = ":".join(key_parts)
        return f"{self.prefix}:{hashlib.md5(combined.encode()).hexdigest()[:12]}"
    
    def get(self, *key_parts: Any) -> Optional[Any]:
        """Get value from cache."""
        key = self.make_key(*key_parts)
        return self.cache.get(key)
    
    def set(self, *args: Any, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Last positional arg before 'value' is the value to cache.
        All other args form the key.
        
        Example:
            cache.set(structure, engine, value=result)
        """
        key = self.make_key(*args)
        return self.cache.set(key, value, ttl=ttl or self.ttl)
    
    def delete(self, *key_parts: Any) -> bool:
        """Delete value from cache."""
        key = self.make_key(*key_parts)
        return self.cache.delete(key)
    
    def get_or_compute(
        self,
        *key_parts: Any,
        compute_fn: Callable[[], T],
        ttl: Optional[int] = None,
    ) -> T:
        """
        Get from cache or compute and store.
        
        Args:
            *key_parts: Parts to form cache key
            compute_fn: Function to compute value if not cached
            ttl: Optional TTL override
            
        Returns:
            Cached or computed value
        """
        cached = self.get(*key_parts)
        if cached is not None:
            return cached
        
        result = compute_fn()
        self.set(*key_parts, value=result, ttl=ttl)
        return result


def _generate_function_key(
    func: Callable,
    args: tuple,
    kwargs: dict,
    prefix: str,
    key_params: Optional[List[str]] = None,
) -> str:
    """Generate cache key for function call."""
    # Start with function identifier
    func_id = f"{func.__module__}.{func.__name__}"
    
    # Build parameters dict
    params = {}
    
    # Add positional args
    for i, arg in enumerate(args):
        param_name = f"arg{i}"
        if key_params is None or param_name in key_params:
            params[param_name] = _serialize_arg(arg)
    
    # Add keyword args
    for key, value in kwargs.items():
        if key_params is None or key in key_params:
            params[key] = _serialize_arg(value)
    
    # Sort for consistent hashing
    params_str = json.dumps(params, sort_keys=True)
    
    # Generate hash
    combined = f"{func_id}:{params_str}"
    hash_val = hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    return f"{prefix}:{hash_val}"


def _serialize_arg(arg: Any) -> Any:
    """Serialize argument for cache key generation."""
    try:
        # Handle numpy arrays
        if hasattr(arg, 'tobytes'):
            import numpy as np
            if isinstance(arg, np.ndarray):
                return hashlib.md5(arg.tobytes()).hexdigest()[:8]
        
        # Handle ASE Atoms
        if hasattr(arg, 'get_positions') and hasattr(arg, 'get_chemical_symbols'):
            positions = arg.get_positions()
            symbols = arg.get_chemical_symbols()
            combined = f"{positions.tobytes()}{symbols}"
            return hashlib.md5(combined.encode()).hexdigest()[:8]
        
        # Handle dicts and lists
        if isinstance(arg, (dict, list)):
            return json.dumps(arg, sort_keys=True, default=str)
        
        # Handle basic types
        return str(arg)
        
    except Exception:
        return str(type(arg).__name__)


def _format_pattern(
    pattern: str,
    args: tuple,
    kwargs: dict,
    func: Callable,
) -> str:
    """Format pattern with function arguments."""
    import inspect
    
    # Get function signature
    sig = inspect.signature(func)
    params = list(sig.parameters.keys())
    
    # Build format dict
    format_dict = {}
    
    # Add positional args
    for i, (param, arg) in enumerate(zip(params, args)):
        format_dict[param] = str(arg)
    
    # Add keyword args
    for key, value in kwargs.items():
        format_dict[key] = str(value)
    
    # Format pattern
    try:
        return pattern.format(**format_dict)
    except KeyError:
        return pattern
