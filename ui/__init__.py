"""
UI package for GTA V Scaleform Minimap Calculator.

This package provides the Blender user interface components including
panels, operators, and property settings.
"""

import bpy

# Import properties first, as other modules depend on them
from .properties import (
    ScaleformCalculatorSettings,
    register_scene_properties,
    unregister_scene_properties,
)

# Import visualization module
from .visualization import (
    register_visualization_properties,
    unregister_visualization_properties,
    visualization_classes,
    SCALEFORM_OT_toggle_visualization,
    SCALEFORM_OT_update_visualization,
    SCALEFORM_PT_visualization_panel,
    SCALEFORM_PersistentPreferences,
)

# Import operators
from .operators import (
    SCALEFORM_OT_calculate_dimensions,
    SCALEFORM_OT_calculate_position,
    SCALEFORM_OT_export_svg,
    SCALEFORM_OT_copy_to_clipboard,
    SCALEFORM_OT_reset_settings,
    SCALEFORM_OT_apply_fill_settings,
)

# Import the panels
from .panels import (
    SCALEFORM_PT_main_panel,
    SCALEFORM_PT_export_settings,
    SCALEFORM_PT_minimap_settings,
)

# List of all classes that need to be registered with Blender
classes = [
    # Properties
    ScaleformCalculatorSettings,
    # Preferences
    SCALEFORM_PersistentPreferences,
    # Main panels first
    SCALEFORM_PT_main_panel,
    # Child panels
    SCALEFORM_PT_export_settings,
    SCALEFORM_PT_minimap_settings,
    SCALEFORM_PT_visualization_panel,
    # Operators
    SCALEFORM_OT_calculate_dimensions,
    SCALEFORM_OT_calculate_position,
    SCALEFORM_OT_export_svg,
    SCALEFORM_OT_copy_to_clipboard,
    SCALEFORM_OT_reset_settings,
    SCALEFORM_OT_apply_fill_settings,
    # Visualization operators
    SCALEFORM_OT_toggle_visualization,
    SCALEFORM_OT_update_visualization,
]


def register():
    """Register scene properties and UI components"""
    register_scene_properties()
    register_visualization_properties()


def unregister():
    """Unregister scene properties and UI components"""
    unregister_visualization_properties()
    unregister_scene_properties()
