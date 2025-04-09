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

def register():
    """Register the add-on with Blender."""
    # Register UI classes
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Register scene properties
    bpy.types.Scene.scaleform_settings = bpy.props.PointerProperty(type=ScaleformCalculatorSettings)
    register_scene_properties()
    
    # Print success message
    from .. import bl_info
    print(f"Registered {bl_info['name']} v{'.'.join(str(v) for v in bl_info['version'])}")

def unregister():
    """Unregister the add-on from Blender."""
    # Clear caches
    from .. import utils
    utils.clear_all_caches()
    
    # Unregister scene properties
    if hasattr(bpy.types.Scene, "scaleform_settings"):
        del bpy.types.Scene.scaleform_settings
    unregister_scene_properties()
    
    # Unregister UI classes in reverse order
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    # Print success message
    from .. import bl_info
    print(f"Unregistered {bl_info['name']}")

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