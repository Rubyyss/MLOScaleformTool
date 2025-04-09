"""
Operator definitions for GTA V Scaleform Minimap Calculator addon.

This module defines the Blender operators that implement the addon functionality.
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ExportHelper
from typing import Set, Dict, Any, List, Tuple, Optional

from ..constants import WORLD_BOUNDS
from ..core import MinimapCalculator, CurveProcessor, SVGExporter
from ..geometry import Vector3, GPointF, GRectF
from ..utils import copy_to_clipboard, apply_fill_preset, apply_stroke_settings

class SCALEFORM_OT_calculate_dimensions(Operator):
    """
    Calculate dimensions of selected curves.
    
    This operator analyzes the selected curves and calculates their
    dimensions and center point, which are needed for SVG export.
    """
    bl_idname = "scaleform.calculate_dimensions"
    bl_label = "Calculate Dimensions"
    bl_description = "Calculate dimensions of selected curves for minimap export"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # Process the selected curves
        curve_data = CurveProcessor.get_selected_curves(context)
        if not curve_data["valid"]:
            self.report({"ERROR"}, curve_data["message"])
            return {"CANCELLED"}

        # Store the results in scene properties
        scene = context.scene
        settings = scene.scaleform_settings
        dimensions = CurveProcessor.calculate_dimensions(curve_data)
        
        scene.scaleform_width_orig = dimensions["width_orig"]
        scene.scaleform_height_orig = dimensions["height_orig"]
        scene.scaleform_width_svg = dimensions["width_svg"]
        scene.scaleform_height_svg = dimensions["height_svg"]
        scene.scaleform_center_x = dimensions["center"].x
        scene.scaleform_center_y = dimensions["center"].y

        # Get world bounds based on settings
        world_bounds = WORLD_BOUNDS if settings.minimap_preset == 'DEFAULT' else (
            settings.custom_world_min_x, settings.custom_world_max_x,
            settings.custom_world_min_y, settings.custom_world_max_y
        )
        minimap_size = (settings.minimap_width, settings.minimap_height)

        # Calculate Scaleform center point
        calculator = MinimapCalculator(world_bounds, minimap_size)
        center_blender = Vector3(0.0, dimensions["center"].x, dimensions["center"].y)
        scaleform_center = calculator.blender_to_scaleform(
            center_blender, settings.svg_scale, dimensions["width_svg"], dimensions["height_svg"]
        )
        
        # Store the Scaleform center in scene properties
        scene.scaleform_scaleform_center_x = scaleform_center.x
        scene.scaleform_scaleform_center_y = scaleform_center.y
        scene.scaleform_has_valid_data = True
        
        # Store the number of selected curves
        scene.scaleform_selected_curve_count = len(curve_data.get("curves", []))

        # Report success to the user
        self.report({"INFO"}, 
                    f"Selected curves: {scene.scaleform_selected_curve_count}, "
                    f"Units: {dimensions['width_orig']:.2f} x {dimensions['height_orig']:.2f}, "
                    f"SVG: {dimensions['width_svg'] * settings.svg_scale:.2f} x {dimensions['height_svg'] * settings.svg_scale:.2f}, "
                    f"Scaleform Center: ({scaleform_center.x:.2f}, {scaleform_center.y:.2f})")
        return {"FINISHED"}

class SCALEFORM_OT_calculate_position(Operator):
    """
    Calculate position of selected curves.
    
    This operator calculates the Scaleform position of the currently
    selected curves, which is useful for positioning them in GTA V.
    """
    bl_idname = "scaleform.calculate_position"
    bl_label = "Calculate Position"
    bl_description = "Calculate Scaleform position of selected curves"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        # Only enable if we have valid data
        return context.scene.scaleform_has_valid_data

    def execute(self, context):
        # Process the selected curves
        curve_data = CurveProcessor.get_selected_curves(context)
        if not curve_data["valid"]:
            self.report({"ERROR"}, curve_data["message"])
            return {"CANCELLED"}

        # Get scene and settings
        scene = context.scene
        settings = scene.scaleform_settings
        
        # Use center of selected curves
        center = curve_data["center"]
        position_blender = Vector3(0.0, center.x, center.y)
        
        # Get existing dimensions from scene
        dimensions = {
            "width_svg": scene.scaleform_width_svg, 
            "height_svg": scene.scaleform_height_svg
        }
        
        # Calculate SVG position
        svg_x = center.x * settings.svg_scale
        svg_y = center.y * settings.svg_scale

        # Get world bounds based on settings
        world_bounds = WORLD_BOUNDS if settings.minimap_preset == 'DEFAULT' else (
            settings.custom_world_min_x, settings.custom_world_max_x,
            settings.custom_world_min_y, settings.custom_world_max_y
        )
        minimap_size = (settings.minimap_width, settings.minimap_height)

        # Calculate Scaleform position
        calculator = MinimapCalculator(world_bounds, minimap_size)
        scaleform_pos = calculator.blender_to_scaleform(
            position_blender, settings.svg_scale, dimensions["width_svg"], dimensions["height_svg"]
        )

        # Store the results in scene properties
        scene.scaleform_position_svg_x = svg_x
        scene.scaleform_position_svg_y = svg_y
        scene.scaleform_position_scaleform_x = scaleform_pos.x
        scene.scaleform_position_scaleform_y = scaleform_pos.y

        # Report success to the user
        self.report({"INFO"},
                    f"SVG Position: ({svg_x:.2f}, {svg_y:.2f}), "
                    f"Scaleform Position: ({scaleform_pos.x:.2f}, {scaleform_pos.y:.2f})")
        return {"FINISHED"}

class SCALEFORM_OT_export_svg(Operator, ExportHelper):
    """
    Export curves to SVG for GTA V minimap.
    
    This operator exports the selected curves to an SVG file that can be
    used for GTA V Scaleform minimap creation.
    """
    bl_idname = "scaleform.export_svg"
    bl_label = "Export SVG with Minimap"
    bl_description = "Export selected curves to SVG for GTA V minimap"
    filename_ext = ".svg"
    filter_glob: StringProperty(default="*.svg", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        # Only enable if we have valid data
        return context.scene.scaleform_has_valid_data

    def execute(self, context):
        # Get scene and settings
        scene, settings = context.scene, context.scene.scaleform_settings
        
        # Process the selected curves
        curve_data = CurveProcessor.get_selected_curves(context)
        if not curve_data["valid"]:
            self.report({"ERROR"}, curve_data["message"])
            return {"CANCELLED"}

        # Normalize curves (center at origin if specified)
        normalized_curves = CurveProcessor.normalize_curves(curve_data, settings.center_at_origin)
        
        # Get dimensions from scene
        dimensions = {key: getattr(scene, f"scaleform_{key}") for key in 
                     ["width_orig", "height_orig", "width_svg", "height_svg"]}

        # Get world bounds based on settings
        world_bounds = WORLD_BOUNDS if settings.minimap_preset == 'DEFAULT' else (
            settings.custom_world_min_x, settings.custom_world_max_x,
            settings.custom_world_min_y, settings.custom_world_max_y
        )
        minimap_size = (settings.minimap_width, settings.minimap_height)

        # Generate minimap data (example positions)
        calculator = MinimapCalculator(world_bounds, minimap_size)
        
        # Using sample positions for demonstration (these would normally come from elsewhere)
        positions = [Vector3(1000.0, 2000.0, 50.0), Vector3(-500.0, 1500.0, 30.0)]
        minimap_data = calculator.generate_scaleform_data(positions)
        minimap_coords = minimap_data["minimap_points"]

        # Generate SVG content
        svg_content = SVGExporter.generate_svg_content(dimensions, normalized_curves, settings, minimap_coords)
        
        # Export SVG file
        SVGExporter.export_svg_file(self.filepath, svg_content)
        
        # Export JSON data file
        json_filepath = SVGExporter.export_minimap_data(self.filepath, minimap_data)

        # Report success to the user
        curve_count = len(curve_data.get("curves_info", [])) if "curves_info" in curve_data else 0
        self.report({"INFO"}, f"Exported {curve_count} curves to SVG at {self.filepath}\nScaleform data saved to {json_filepath}")
        return {"FINISHED"}

class SCALEFORM_OT_copy_to_clipboard(Operator):
    """
    Copy a value to the clipboard.
    
    This operator copies a value to the system clipboard, which is useful
    for transferring coordinates to other applications.
    """
    bl_idname = "scaleform.copy_to_clipboard"
    bl_label = "Copy to Clipboard"
    bl_description = "Copy value to system clipboard"
    value: StringProperty(name="Value")

    def execute(self, context):
        # Apply the decimal separator setting
        settings = context.scene.scaleform_settings
        value_to_copy = self.value.replace(".", ",") if settings.use_comma_separator else self.value
        
        # Copy to clipboard
        copy_to_clipboard(value_to_copy)
        
        # Report success to the user
        self.report({"INFO"}, f"Copied {value_to_copy} to clipboard")
        return {"FINISHED"}

class SCALEFORM_OT_reset_settings(Operator):
    """
    Reset all settings to default values.
    
    This operator resets all addon settings to their default values.
    """
    bl_idname = "scaleform.reset_settings"
    bl_label = "Reset Settings"
    bl_description = "Reset all settings to their default values"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # Get settings
        settings = context.scene.scaleform_settings
        
        # Reset to defaults
        settings.svg_scale = 10.0
        settings.precision = 2
        settings.resolution = 12
        settings.center_at_origin = False
        settings.fill_preset = 'ACCESSIBLE'
        settings.use_fill = True
        settings.fill_color = (0.6, 0.6, 0.6, 1.0)
        settings.use_stroke = False
        settings.stroke_color = (0.25, 0.25, 0.25, 1.0)
        settings.stroke_width = 0.5
        settings.show_markers = True
        settings.marker_color = "#FF0000"
        settings.marker_size = 5.0
        settings.use_comma_separator = False
        settings.minimap_preset = 'DEFAULT'
        settings.minimap_width = 300.0
        settings.minimap_height = 300.0
        
        # Report success to the user
        self.report({"INFO"}, "Settings have been reset to defaults")
        return {"FINISHED"}

class SCALEFORM_OT_apply_fill_settings(Operator):
    """
    Apply fill and stroke settings to selected curves.
    
    This operator applies the current fill and stroke settings to all
    selected curve objects.
    """
    bl_idname = "scaleform.apply_fill_settings"
    bl_label = "Apply Fill Settings to Selected"
    bl_description = "Apply current fill and stroke settings to selected curves"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        # Only enable if curves are selected
        return any(obj.type == "CURVE" for obj in context.selected_objects)

    def execute(self, context):
        # Get settings
        settings = context.scene.scaleform_settings
        
        # Get selected curves
        selected_curves = [obj for obj in context.selected_objects if obj.type == "CURVE"]
        
        if not selected_curves:
            self.report({"ERROR"}, "No curve objects selected.")
            return {"CANCELLED"}
        
        # Apply settings to each curve
        for obj in selected_curves:
            # Apply fill preset
            obj["scaleform_fill_preset"] = settings.fill_preset
            obj["scaleform_use_fill"] = settings.use_fill
            obj["scaleform_fill_color_r"] = settings.fill_color[0]
            obj["scaleform_fill_color_g"] = settings.fill_color[1]
            obj["scaleform_fill_color_b"] = settings.fill_color[2]
            obj["scaleform_fill_color_a"] = settings.fill_color[3]
            
            # Apply stroke settings
            obj["scaleform_use_stroke"] = settings.use_stroke
            obj["scaleform_stroke_color_r"] = settings.stroke_color[0]
            obj["scaleform_stroke_color_g"] = settings.stroke_color[1]
            obj["scaleform_stroke_color_b"] = settings.stroke_color[2]
            obj["scaleform_stroke_color_a"] = settings.stroke_color[3]
            obj["scaleform_stroke_width"] = settings.stroke_width
        
        # Report success to the user
        self.report({"INFO"}, f"Fill and stroke settings applied to {len(selected_curves)} curve objects")
        return {"FINISHED"}