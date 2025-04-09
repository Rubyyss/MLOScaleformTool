"""
UI package for GTA V Scaleform Minimap Calculator addon.

This package provides the Blender user interface components including
panels, operators, and property settings.
"""

import bpy

# Import properties first, as other modules depend on them
from .properties import (
    ScaleformCalculatorSettings, 
    register_scene_properties,
    unregister_scene_properties
)

# Import operators
from .operators import (
    SCALEFORM_OT_calculate_dimensions,
    SCALEFORM_OT_calculate_position,
    SCALEFORM_OT_export_svg,
    SCALEFORM_OT_copy_to_clipboard,
    SCALEFORM_OT_reset_settings,
    SCALEFORM_OT_apply_fill_settings
)

# Import the panels
from .panels import (
    SCALEFORM_PT_main_panel,
    SCALEFORM_PT_export_settings,
    SCALEFORM_PT_minimap_settings
)

# List of all classes that need to be registered with Blender
classes = [
    # Properties
    ScaleformCalculatorSettings,
    
    # Operators
    SCALEFORM_OT_calculate_dimensions,
    SCALEFORM_OT_calculate_position,
    SCALEFORM_OT_export_svg,
    SCALEFORM_OT_copy_to_clipboard,
    SCALEFORM_OT_reset_settings,
    SCALEFORM_OT_apply_fill_settings,
    
    # Panels
    SCALEFORM_PT_main_panel,
    SCALEFORM_PT_export_settings,
    SCALEFORM_PT_minimap_settings
]

# Note: We don't include any register() or unregister() functions here 
# since registration will be handled by the main __init__.py file
# This prevents double registration issues

__all__ = [
    # Properties
    'ScaleformCalculatorSettings', 
    'register_scene_properties', 
    'unregister_scene_properties',
    
    # Operators
    'SCALEFORM_OT_calculate_dimensions',
    'SCALEFORM_OT_calculate_position',
    'SCALEFORM_OT_export_svg',
    'SCALEFORM_OT_copy_to_clipboard',
    'SCALEFORM_OT_reset_settings',
    'SCALEFORM_OT_apply_fill_settings',
    
    # Panels
    'SCALEFORM_PT_main_panel',
    'SCALEFORM_PT_export_settings',
    'SCALEFORM_PT_minimap_settings',
    
    # Class list
    'classes'
]