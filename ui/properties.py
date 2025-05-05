"""
Property definitions for GTA V Scaleform Minimap Calculator.

This module defines the property groups and UI-related properties
used in the addon.
"""

import bpy
from bpy.props import (
    FloatProperty,
    StringProperty,
    BoolProperty,
    PointerProperty,
    FloatVectorProperty,
    IntProperty,
    EnumProperty,
)

from ..constants import FILL_PRESETS


def update_fill_preset(self, context):
    """
    Update handler for fill preset selection.

    When a preset is selected, this function updates the fill color
    to match the selected preset.

    Args:
        self: Property owner
        context: Blender context
    """
    
    # Clear the cache to force an upgrade
    from ..utils.cache import curve_cache
    curve_cache.clear()
    
    preset = self.fill_preset
    if preset in FILL_PRESETS:
        self.fill_color = FILL_PRESETS[preset]


class ScaleformCalculatorSettings(bpy.types.PropertyGroup):
    """
    Property group for Scaleform calculator settings.

    These properties control the behavior of the calculator and
    export operations.
    """

    # SVG export settings
    svg_scale: FloatProperty(
        name="SVG Scale",
        description="Scale factor for SVG output",
        default=20.0,
        min=0.01,
        max=60.0,
    )

    precision: IntProperty(
        name="Coordinate Precision",
        description="Number of decimal places for coordinates",
        default=2,
        min=0,
        max=6,
    )

    resolution: IntProperty(
        name="Curve Resolution",
        description="Resolution for curve approximation",
        default=12,
        min=1,
        max=64,
    )

    center_at_origin: BoolProperty(
        name="Center at Origin",
        description="Center the exported SVG at the origin instead of using top-left positioning",
        default=False,
    )

    # Fill and stroke settings
    fill_preset: EnumProperty(
        name="Fill Preset",
        description="Predefined color presets for different area types",
        items=[
            ("ACCESSIBLE", "Accessible Zone", "Color for accessible zones"),
            ("ENTITIES", "Entities Objects", "Color for entity objects"),
            ("NEXT_AREA", "Next Area", "Color for next area markers"),
            ("LIMITS", "Limits Of The Area", "Color for area limits"),
            ("CUSTOM", "Custom Color", "Use custom color settings"),
        ],
        default="ACCESSIBLE",
        update=update_fill_preset,
    )

    use_fill: BoolProperty(
        name="Use Fill", description="Fill shapes with color", default=True
    )

    fill_color: FloatVectorProperty(
        name="Fill Color",
        description="Color for filling shapes",
        subtype="COLOR",
        default=(0.6, 0.6, 0.6, 1.0),
        size=4,
        min=0.0,
        max=1.0,
    )

    use_stroke: BoolProperty(
        name="Use Stroke", description="Draw outlines around shapes", default=False
    )

    stroke_color: FloatVectorProperty(
        name="Stroke Color",
        description="Color for shape outlines",
        subtype="COLOR",
        default=(0.25, 0.25, 0.25, 1.0),
        size=4,
        min=0.0,
        max=1.0,
    )

    stroke_width: FloatProperty(
        name="Stroke Width",
        description="Width of shape outlines",
        default=0.5,
        min=0.0,
        max=10.0,
    )

    # Marker settings
    show_markers: BoolProperty(
        name="Show Markers",
        description="Show position markers in the exported SVG",
        default=False,
    )

    marker_color: StringProperty(
        name="Marker Color",
        description="Color for position markers in hex format",
        default="#FF0000",
    )

    marker_size: FloatProperty(
        name="Marker Size",
        description="Size of position markers",
        default=5.0,
        min=1.0,
        max=20.0,
    )

    # Format settings
    use_comma_separator: BoolProperty(
        name="Use Comma as Decimal",
        description="Use comma instead of period as decimal separator",
        default=False,
    )

    # Minimap settings
    minimap_preset: EnumProperty(
        name="Map Preset",
        description="Predefined map boundaries",
        items=[
            ("DEFAULT", "Default GTA V", "Use standard GTA V world boundaries"),
            ("CUSTOM", "Custom", "Define custom world boundaries"),
        ],
        default="DEFAULT",
    )

    custom_world_min_x: FloatProperty(
        name="World Min X",
        description="Minimum X coordinate of the world boundary",
        default=-4000.0,
    )

    custom_world_max_x: FloatProperty(
        name="World Max X",
        description="Maximum X coordinate of the world boundary",
        default=4000.0,
    )

    custom_world_min_y: FloatProperty(
        name="World Min Y",
        description="Minimum Y coordinate of the world boundary",
        default=-4000.0,
    )

    custom_world_max_y: FloatProperty(
        name="World Max Y",
        description="Maximum Y coordinate of the world boundary",
        default=4000.0,
    )

    minimap_width: FloatProperty(
        name="Minimap Width",
        description="Width of the minimap in Scaleform coordinates",
        default=300.0,
        min=1.0,
    )

    minimap_height: FloatProperty(
        name="Minimap Height",
        description="Height of the minimap in Scaleform coordinates",
        default=300.0,
        min=1.0,
    )


def register_scene_properties():
    """
    Register scene properties used by the addon.

    These properties store the state and results of calculations.
    """
    scene_props = {
        "scaleform_has_valid_data": BoolProperty(default=False),
        "scaleform_width_orig": FloatProperty(default=0.0),
        "scaleform_height_orig": FloatProperty(default=0.0),
        "scaleform_width_svg": FloatProperty(default=0.0),
        "scaleform_height_svg": FloatProperty(default=0.0),
        "scaleform_center_x": FloatProperty(default=0.0),
        "scaleform_center_y": FloatProperty(default=0.0),
        "scaleform_scaleform_center_x": FloatProperty(default=0.0),
        "scaleform_scaleform_center_y": FloatProperty(default=0.0),
        "scaleform_position_svg_x": FloatProperty(default=0.0),
        "scaleform_position_svg_y": FloatProperty(default=0.0),
        "scaleform_position_scaleform_x": FloatProperty(default=0.0),
        "scaleform_position_scaleform_y": FloatProperty(default=0.0),
        "scaleform_selected_curve_count": IntProperty(default=0),
    }

    for prop_name, prop in scene_props.items():
        setattr(bpy.types.Scene, prop_name, prop)


def unregister_scene_properties():
    """
    Unregister scene properties used by the addon.

    This should be called when unregistering the addon.
    """
    props_to_remove = [
        "scaleform_has_valid_data",
        "scaleform_width_orig",
        "scaleform_height_orig",
        "scaleform_width_svg",
        "scaleform_height_svg",
        "scaleform_center_x",
        "scaleform_center_y",
        "scaleform_scaleform_center_x",
        "scaleform_scaleform_center_y",
        "scaleform_position_svg_x",
        "scaleform_position_svg_y",
        "scaleform_position_scaleform_x",
        "scaleform_position_scaleform_y",
        "scaleform_selected_curve_count",
    ]

    for prop in props_to_remove:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)
