"""
UI package for GTA V Scaleform Minimap Calculator addon.

This package provides the Blender user interface components including
panels, operators, and visualization tools.
"""

from .properties import (
    ScaleformCalculatorSettings, 
    register_scene_properties,
    unregister_scene_properties
)

from .operators import (
    SCALEFORM_OT_calculate_dimensions,
    SCALEFORM_OT_calculate_position,
    SCALEFORM_OT_export_svg,
    SCALEFORM_OT_copy_to_clipboard,
    SCALEFORM_OT_reset_settings,
    SCALEFORM_OT_apply_fill_settings,
    SCALEFORM_OT_toggle_bounds_display
)

from .panels import (
    SCALEFORM_PT_main_panel,
    SCALEFORM_PT_export_settings,
    SCALEFORM_PT_minimap_settings,
    SCALEFORM_PT_visualization_panel
)

# List all classes that need to be registered with Blender
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
    SCALEFORM_OT_toggle_bounds_display,
    
    # Panels
    SCALEFORM_PT_main_panel,
    SCALEFORM_PT_export_settings,
    SCALEFORM_PT_minimap_settings,
    SCALEFORM_PT_visualization_panel
]

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
    'SCALEFORM_OT_toggle_bounds_display',
    
    # Panels
    'SCALEFORM_PT_main_panel',
    'SCALEFORM_PT_export_settings',
    'SCALEFORM_PT_minimap_settings',
    'SCALEFORM_PT_visualization_panel',
    
    # Class list
    'classes'
]