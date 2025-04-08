"""
Caching system for GTA V Scaleform Minimap Calculator addon.

This module provides caching functionality to improve performance by
storing and reusing results of expensive calculations.
"""

import time
import gc
from typing import Dict, Any, Callable, TypeVar, Generic, Optional, Tuple

from ..constants import DEFAULT_CACHE_LIFETIME, MAX_CACHE_SIZE

# Generic types for cache
T = TypeVar('T')
K = TypeVar('K')

class CacheItem(Generic[T]):
    """
    Represents an item stored in the cache with expiration time.
    
    This class tracks when an item was added to the cache and determines
    when it should expire.
    """
    
    def __init__(self, value: T, lifetime: float = DEFAULT_CACHE_LIFETIME):
        """
        Initialize a new cache item.
        
        Args:
            value: Value to store in the cache
            lifetime: How long the item should live in the cache (seconds)
        """
        self.value = value
        self.timestamp = time.time()
        self.lifetime = lifetime
    
    def is_expired(self) -> bool:
        """
        Check if the cache item has expired.
        
        Returns:
            True if the item has expired, False otherwise
        """
        return time.time() > (self.timestamp + self.lifetime)
    
    def refresh(self) -> None:
        """Update the timestamp of the cache item to extend its lifetime."""
        self.timestamp = time.time()


class Cache(Generic[K, T]):
    """
    Generic cache implementation with support for expiration and size limits.
    
    This class provides a key-value store with automatic expiration of items
    and management of the cache size.
    """
    
    def __init__(self, max_size: int = MAX_CACHE_SIZE, default_lifetime: float = DEFAULT_CACHE_LIFETIME):
        """
        Initialize a new cache.
        
        Args:
            max_size: Maximum number of items before cleanup occurs
            default_lifetime: Default lifetime for items in seconds
        """
        self._cache: Dict[K, CacheItem[T]] = {}
        self.max_size = max_size
        self.default_lifetime = default_lifetime
        self.hit_count = 0
        self.miss_count = 0
    
    def get(self, key: K) -> Optional[T]:
        """
        Get a value from the cache.
        
        Args:
            key: Key to look up in the cache
            
        Returns:
            The cached value or None if not found or expired
        """
        if key in self._cache:
            item = self._cache[key]
            if item.is_expired():
                # Remove expired item
                del self._cache[key]
                self.miss_count += 1
                return None
            
            # Update statistics and return value
            self.hit_count += 1
            item.refresh()  # Update timestamp to extend lifetime
            return item.value
        
        self.miss_count += 1
        return None
    
    def set(self, key: K, value: T, lifetime: Optional[float] = None) -> None:
        """
        Store a value in the cache.
        
        Args:
            key: Key to store the value under
            value: Value to store
            lifetime: Custom lifetime in seconds (uses default if None)
        """
        # Check if we need to make space
        if len(self._cache) >= self.max_size:
            self._cleanup()
        
        actual_lifetime = lifetime if lifetime is not None else self.default_lifetime
        self._cache[key] = CacheItem(value, actual_lifetime)
    
    def _cleanup(self) -> None:
        """
        Remove old or expired items to make space in the cache.
        
        This is called automatically when the cache reaches its size limit.
        """
        # First remove all expired items
        expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
        for key in expired_keys:
            del self._cache[key]
        
        # If we still need space, remove oldest items
        if len(self._cache) >= self.max_size:
            # Sort by timestamp (oldest first)
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1].timestamp)
            # Remove 25% oldest or at least one item
            items_to_remove = max(1, len(sorted_items) // 4)
            for i in range(items_to_remove):
                if i < len(sorted_items):
                    del self._cache[sorted_items[i][0]]
    
    def clear(self) -> None:
        """
        Clear the cache completely.
        
        This removes all items from the cache and forces garbage collection.
        """
        self._cache.clear()
        # Force memory release
        gc.collect()
    
    def remove(self, key: K) -> bool:
        """
        Remove a specific item from the cache.
        
        Args:
            key: Key to remove
            
        Returns:
            True if the item existed and was removed, False otherwise
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Return statistics about cache usage.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.hit_count + self.miss_count
        hit_ratio = self.hit_count / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_ratio": hit_ratio,
            "hit_percentage": hit_ratio * 100
        }
    
    def get_or_compute(self, key: K, compute_func: Callable[[], T], 
                      lifetime: Optional[float] = None) -> T:
        """
        Get a value from the cache or compute it if not present.
        
        Args:
            key: Key to look for/store
            compute_func: Function to compute the value if not in cache
            lifetime: Optional lifetime for the new item
            
        Returns:
            The cached value or the computed value
        """
        # Check if already in cache
        cached_value = self.get(key)
        if cached_value is not None:
            return cached_value
        
        # Compute and store the value
        computed_value = compute_func()
        self.set(key, computed_value, lifetime)
        return computed_value


# Global cache instances for different types of data

# Cache for calculation results (general-purpose)
calculation_cache = Cache[str, Any](max_size=200, default_lifetime=600)  # 10 minutes

# Cache for processed geometry (longer lifetime)
geometry_cache = Cache[str, Any](max_size=100, default_lifetime=1800)  # 30 minutes

# Cache for selected curves (short lifetime)
curve_cache = Cache[str, Any](max_size=50, default_lifetime=60)  # 1 minute


def clear_all_caches() -> None:
    """
    Clear all caches in the system.
    
    This is useful when forcing recalculations or freeing memory.
    """
    calculation_cache.clear()
    geometry_cache.clear()
    curve_cache.clear()
    gc.collect()  # Force garbage collection


def get_cache_stats() -> Dict[str, Dict[str, Any]]:
    """
    Get statistics for all caches.
    
    Returns:
        Dictionary with statistics for each cache
    """
    return {
        "calculation": calculation_cache.get_stats(),
        "geometry": geometry_cache.get_stats(),
        "curve": curve_cache.get_stats()
    }


def compute_with_cache(cache: Cache, key: str, compute_func: Callable[[], Any]) -> Any:
    """
    Convenience function for computing a value with cache.
    
    Args:
        cache: Cache instance to use
        key: Key for the cache
        compute_func: Function to compute the value
        
    Returns:
        The cached or newly computed value
    """
    return cache.get_or_compute(key, compute_func)


def hash_object_data(obj: Any) -> str:
    """
    Generate a hash for a Blender object's data.
    
    This is useful for creating cache keys based on object state.
    
    Args:
        obj: Blender object to hash
        
    Returns:
        Hash string representing the object state
    """
    if hasattr(obj, "matrix_world"):
        # Hash for transformation matrix
        matrix_str = "_".join(str(obj.matrix_world[i][j]) for i in range(4) for j in range(4))
        return f"{obj.name}_{hash(matrix_str)}"
    
    # Fallback for objects without matrix
    return f"{obj.name}_{id(obj)}"


def hash_curve_data(curve_obj) -> str:
    """
    Generate a hash for a Blender curve's data.
    
    This creates a unique identifier for the curve based on its
    geometry data (points, handles, etc.) which can be used as a cache key.
    
    Args:
        curve_obj: Blender curve object
        
    Returns:
        Hash string for the curve data
    """
    # Base hash on object name and transformation
    base_hash = hash_object_data(curve_obj)
    
    # Add hash of spline data
    spline_hashes = []
    
    for spline in curve_obj.data.splines:
        # Include spline type and cyclic setting
        spline_hash = f"{spline.type}_{spline.use_cyclic_u}"
        
        # Add point data based on spline type
        if spline.type == "BEZIER":
            # For Bezier curves, include all points and handles
            points_hash = []
            for point in spline.bezier_points:
                pt_hash = (
                    f"{point.co[0]:.3f}_{point.co[1]:.3f}_{point.co[2]:.3f}_"
                    f"{point.handle_left[0]:.3f}_{point.handle_left[1]:.3f}_{point.handle_left[2]:.3f}_"
                    f"{point.handle_right[0]:.3f}_{point.handle_right[1]:.3f}_{point.handle_right[2]:.3f}"
                )
                points_hash.append(pt_hash)
            spline_hash += "_" + "_".join(points_hash)
        else:
            # For other spline types, include all points
            points_hash = []
            for point in spline.points:
                pt_hash = f"{point.co[0]:.3f}_{point.co[1]:.3f}_{point.co[2]:.3f}_{point.co[3]:.3f}"
                points_hash.append(pt_hash)
            spline_hash += "_" + "_".join(points_hash)
            
        spline_hashes.append(spline_hash)
    
    # Combine base hash with spline data
    return f"{base_hash}_{'_'.join(spline_hashes)}"