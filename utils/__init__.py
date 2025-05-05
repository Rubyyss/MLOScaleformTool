"""
Utilities package for GTA V Scaleform Minimap Calculator.

This package provides utility functions and helper classes
used throughout the addon.
"""

from .cache import (
    Cache, calculation_cache, geometry_cache, curve_cache,
    clear_all_caches, get_cache_stats
)

from .helpers import (
    deg_to_rad, hex_from_rgba, format_coordinate,
    apply_fill_preset, apply_stroke_settings, get_addon_preferences,
    get_enum_items, copy_to_clipboard, reset_scene_properties
)

__all__ = [
    # Cache system
    'Cache', 'calculation_cache', 'geometry_cache', 'curve_cache',
    'clear_all_caches', 'get_cache_stats',
    
    # Helper functions
    'deg_to_rad', 'hex_from_rgba', 'format_coordinate',
    'apply_fill_preset', 'apply_stroke_settings', 'get_addon_preferences',
    'get_enum_items', 'copy_to_clipboard', 'reset_scene_properties'
]