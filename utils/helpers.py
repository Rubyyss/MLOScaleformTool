"""
Helper functions for GTA V Scaleform Minimap Calculator addon.

This module provides general utility functions used throughout the addon
that don't fit elsewhere.
"""

import bpy
from typing import Dict, List, Tuple, Any, Optional, Union

def deg_to_rad(degrees: float) -> float:
    """
    Convert degrees to radians.
    
    Args:
        degrees: Angle in degrees
        
    Returns:
        Angle in radians
    """
    import math
    return degrees * math.pi / 180.0

def hex_from_rgba(rgba: Tuple[float, float, float, float]) -> str:
    """
    Convert RGBA color values to hexadecimal string.
    
    Args:
        rgba: Tuple of (red, green, blue, alpha) values in [0.0-1.0] range
        
    Returns:
        Hexadecimal color string (e.g., "#FF0000" for red)
    """
    r, g, b = [int(c * 255) for c in rgba[:3]]
    return f"#{r:02x}{g:02x}{b:02x}"

def format_coordinate(value: float, precision: int, use_comma: bool) -> str:
    """
    Format coordinate value with specified precision and decimal separator.
    
    Args:
        value: Coordinate value to format
        precision: Number of decimal places
        use_comma: Whether to use comma as decimal separator
        
    Returns:
        Formatted string representation
    """
    formatted = f"{value:.{precision}f}"
    return formatted.replace(".", ",") if use_comma else formatted

def apply_fill_preset(obj: bpy.types.Object, preset: str) -> None:
    """
    Apply a fill preset to a curve object.
    
    Args:
        obj: Blender curve object to modify
        preset: Name of the preset to apply
    """
    from ..constants import FILL_PRESETS
    
    if preset in FILL_PRESETS:
        rgba = FILL_PRESETS[preset]
        obj["scaleform_fill_preset"] = preset
        obj["scaleform_fill_color_r"] = rgba[0]
        obj["scaleform_fill_color_g"] = rgba[1]
        obj["scaleform_fill_color_b"] = rgba[2]
        obj["scaleform_fill_color_a"] = rgba[3]

def apply_stroke_settings(obj: bpy.types.Object, 
                          color: Tuple[float, float, float, float], 
                          width: float, 
                          use_stroke: bool) -> None:
    """
    Apply stroke settings to a curve object.
    
    Args:
        obj: Blender curve object to modify
        color: RGBA color for stroke
        width: Stroke width
        use_stroke: Whether to use a stroke
    """
    obj["scaleform_use_stroke"] = use_stroke
    obj["scaleform_stroke_color_r"] = color[0]
    obj["scaleform_stroke_color_g"] = color[1]
    obj["scaleform_stroke_color_b"] = color[2]
    obj["scaleform_stroke_color_a"] = color[3]
    obj["scaleform_stroke_width"] = width

def get_addon_preferences() -> Any:
    """
    Get the addon preferences.
    
    Returns:
        Addon preferences object or None if not found
    """
    import bpy
    addon_name = __package__.split('.')[0]
    try:
        return bpy.context.preferences.addons[addon_name].preferences
    except (KeyError, AttributeError):
        return None

def get_enum_items(enum_property) -> List[Tuple[str, str, str]]:
    """
    Get all items from an EnumProperty.
    
    Args:
        enum_property: Blender EnumProperty
        
    Returns:
        List of enum items as (identifier, name, description) tuples
    """
    items = []
    for item in enum_property.enum_items:
        items.append((item.identifier, item.name, item.description))
    return items

def copy_to_clipboard(value: str) -> None:
    """
    Copy a value to the system clipboard.
    
    Args:
        value: String value to copy
    """
    bpy.context.window_manager.clipboard = value

def reset_scene_properties(scene: bpy.types.Scene) -> None:
    """
    Reset all scene properties related to the addon.
    
    Args:
        scene: Blender scene to reset properties in
    """
    scene.scaleform_has_valid_data = False
    scene.scaleform_width_orig = 0.0
    scene.scaleform_height_orig = 0.0
    scene.scaleform_width_svg = 0.0
    scene.scaleform_height_svg = 0.0
    scene.scaleform_center_x = 0.0
    scene.scaleform_center_y = 0.0
    scene.scaleform_scaleform_center_x = 0.0
    scene.scaleform_scaleform_center_y = 0.0
    scene.scaleform_position_svg_x = 0.0
    scene.scaleform_position_svg_y = 0.0
    scene.scaleform_position_scaleform_x = 0.0
    scene.scaleform_position_scaleform_y = 0.0
    scene.scaleform_selected_curve_count = 0
