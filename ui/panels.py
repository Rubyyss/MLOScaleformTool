"""
Panel definitions for GTA V Scaleform Minimap Calculator addon.

This module defines the UI panels displayed in the Blender interface.
"""

import bpy
from bpy.types import Panel

class SCALEFORM_PT_main_panel(Panel):
    """
    Main panel for the GTA V Scaleform Minimap Calculator addon.
    
    This panel provides the main interface for the addon, displaying
    calculation results and access to the primary functions.
    """
    bl_label = "GTA V Scaleform Minimap"
    bl_idname = "SCALEFORM_PT_main_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Scaleform"

    def draw_header(self, context):
        """Draw the panel header."""
        self.layout.label(icon='MOD_CURVE')

    def draw(self, context):
        """Draw the panel contents."""
        layout = self.layout
        scene = context.scene
        settings = scene.scaleform_settings

        # Introduction text
        col = layout.column()
        col.label(text="Convert Blender curves to GTA V minimap")
        
        # Show selected curve count
        selected_curves = [obj for obj in context.selected_objects if obj.type == "CURVE"]
        selected_count = len(selected_curves)
        
        box = layout.box()
        row = box.row()
        row.label(text=f"Selected Curves: {selected_count}", icon='OUTLINER_OB_CURVE')
        
        # Workflow box
        box = layout.box()
        box.label(text="Workflow", icon='SEQUENCE')
        row = box.row(align=True)
        row.operator("scaleform.calculate_dimensions", icon='DRIVER_DISTANCE')
        
        # Only show these if we have valid data
        if scene.scaleform_has_valid_data:
            # Dimensions box
            dim_box = layout.box()
            dim_box.label(text="Dimensions:", icon='ORIENTATION_VIEW')
            row = dim_box.row()
            row.label(text=f"Units: {scene.scaleform_width_orig:.2f} x {scene.scaleform_height_orig:.2f}")
            row = dim_box.row()
            row.label(text=f"SVG: {scene.scaleform_width_svg * settings.svg_scale:.2f} x {scene.scaleform_height_svg * settings.svg_scale:.2f}")
            
            # Show number of curves in calculation
            if hasattr(scene, "scaleform_selected_curve_count"):
                row = dim_box.row()
                row.label(text=f"Curves in calculation: {scene.scaleform_selected_curve_count}")
            
            # Center box
            center_box = layout.box()
            center_box.label(text="Scaleform Center:", icon='PIVOT_CURSOR')
            
            # X coordinate with copy button
            row = center_box.row(align=True)
            row.label(text="X:")
            val_x = f"{scene.scaleform_scaleform_center_x:.2f}"
            row.label(text=val_x)
            copy_op = row.operator("scaleform.copy_to_clipboard", text="", icon='COPYDOWN')
            copy_op.value = val_x
            
            # Y coordinate with copy button
            row = center_box.row(align=True)
            row.label(text="Y:")
            val_y = f"{scene.scaleform_scaleform_center_y:.2f}"
            row.label(text=val_y)
            copy_op = row.operator("scaleform.copy_to_clipboard", text="", icon='COPYDOWN')
            copy_op.value = val_y
            
            # Position box
            pos_box = layout.box()
            row = pos_box.row()
            row.operator("scaleform.calculate_position", icon='SNAP_MIDPOINT')
            
            # Only show position if it has been calculated
            if hasattr(scene, "scaleform_position_scaleform_x") and scene.scaleform_position_scaleform_x != 0.0:
                pos_box.label(text="Scaleform Position:", icon='SNAP_VERTEX')
                
                # X coordinate with copy button
                row = pos_box.row(align=True)
                row.label(text="X:")
                val_pos_x = f"{scene.scaleform_position_scaleform_x:.2f}"
                row.label(text=val_pos_x)
                copy_op = row.operator("scaleform.copy_to_clipboard", text="", icon='COPYDOWN')
                copy_op.value = val_pos_x
                
                # Y coordinate with copy button
                row = pos_box.row(align=True)
                row.label(text="Y:")
                val_pos_y = f"{scene.scaleform_position_scaleform_y:.2f}"
                row.label(text=val_pos_y)
                copy_op = row.operator("scaleform.copy_to_clipboard", text="", icon='COPYDOWN')
                copy_op.value = val_pos_y
            
            # Export box
            export_box = layout.box()
            row = export_box.row()
            row.scale_y = 1.5
            row.operator("scaleform.export_svg", icon='EXPORT')
            
            # Tips box
            tips_box = layout.box()
            tips_box.label(text="Tips:", icon='INFO')
            tips_box.label(text="• Use the floor of the MLO as reference")
            tips_box.label(text="• Multiple curves can be selected for export")
            tips_box.label(text="• Each curve can have its own fill/stroke")
            tips_box.label(text="• Some MLOs require rotation by 180°")
            tips_box.label(text="• Use dissolving faces for smooth curves")
            tips_box.label(text="• Large MLOs may need scale adjustment")
        else:
            # Instruction for first step
            row = layout.row()
            row.label(text="Select curve(s) and calculate dimensions", icon='INFO')

class SCALEFORM_PT_export_settings(Panel):
    """
    Panel for export settings.
    
    This panel provides options for configuring the SVG export process,
    including scale, precision, and fill/stroke settings.
    """
    bl_label = "Export Settings"
    bl_idname = "SCALEFORM_PT_export_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Scaleform"
    bl_parent_id = "SCALEFORM_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        """Draw the panel header."""
        self.layout.label(icon='PREFERENCES')

    def draw(self, context):
        """Draw the panel contents."""
        layout = self.layout
        settings = context.scene.scaleform_settings
        selected_curves = [obj for obj in context.selected_objects if obj.type == "CURVE"]

        # Reset settings button
        row = layout.row()
        row.operator("scaleform.reset_settings", icon='LOOP_BACK')
        
        # SVG properties box
        box = layout.box()
        box.label(text="SVG Properties:", icon='OUTLINER_OB_FONT')
        col = box.column(align=True)
        col.prop(settings, "svg_scale", slider=True)
        col.prop(settings, "precision")
        col.prop(settings, "resolution")
        col.prop(settings, "center_at_origin")
        row = box.row()
        row.prop(settings, "use_comma_separator")
        
        # Fill preset box
        preset_box = layout.box()
        preset_box.label(text="Color Preset:", icon='COLOR')
        preset_box.prop(settings, "fill_preset", text="")
        
        # Fill settings box
        fill_box = layout.box()
        fill_box.label(text="Fill Settings:", icon='BRUSH_DATA')
        row = fill_box.row()
        row.prop(settings, "use_fill")
        sub = fill_box.row()
        sub.enabled = settings.use_fill
        sub.prop(settings, "fill_color", text="")
        
        # Stroke settings box
        stroke_box = layout.box()
        stroke_box.label(text="Stroke Settings:", icon='STROKE')
        row = stroke_box.row()
        row.prop(settings, "use_stroke")
        sub = stroke_box.column()
        sub.enabled = settings.use_stroke
        sub_row = sub.row()
        sub_row.prop(settings, "stroke_color", text="")
        sub_row.prop(settings, "stroke_width", text="Width")
        
        # Apply settings box
        apply_box = layout.box()
        row = apply_box.row()
        row.scale_y = 1.2
        apply_text = "Apply Fill Settings"
        if len(selected_curves) > 0:
            apply_text = f"Apply to {len(selected_curves)} curve(s)"
        row.operator("scaleform.apply_fill_settings", text=apply_text, icon='CHECKMARK')
        
        # Show saved settings for selected curves
        if selected_curves:
            info_box = layout.box()
            info_box.label(text="Saved Settings:", icon='INFO')
            
            # If multiple curves, show how many have settings
            if len(selected_curves) > 1:
                configured_curves = [obj for obj in selected_curves if "scaleform_fill_preset" in obj]
                row = info_box.row()
                row.label(text=f"{len(configured_curves)}/{len(selected_curves)} curves have settings")
            
            # If only one curve is selected, show its settings
            if len(selected_curves) == 1 and "scaleform_fill_preset" in selected_curves[0]:
                obj = selected_curves[0]
                row = info_box.row()
                row.label(text=f"Curve: {obj.name}")
                row = info_box.row()
                row.label(text=f"Preset: {obj.get('scaleform_fill_preset', 'None')}")
                row = info_box.row()
                r, g, b = obj.get('scaleform_fill_color_r', 0), obj.get('scaleform_fill_color_g', 0), obj.get('scaleform_fill_color_b', 0)
                row.label(text=f"Fill: #{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}")
                r, g, b = obj.get('scaleform_stroke_color_r', 0), obj.get('scaleform_stroke_color_g', 0), obj.get('scaleform_stroke_color_b', 0)
                row = info_box.row()
                row.label(text=f"Stroke: #{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}")
        
        # Marker settings box
        marker_box = layout.box()
        marker_box.label(text="Marker Settings: (DEBUG ONLY)", icon='KEYTYPE_KEYFRAME_VEC')
        row = marker_box.row()
        row.prop(settings, "show_markers")
        sub = marker_box.column()
        sub.enabled = settings.show_markers
        sub_row = sub.row()
        sub_row.prop(settings, "marker_color", text="Color")
        sub_row.prop(settings, "marker_size", text="Size")

class SCALEFORM_PT_minimap_settings(Panel):
    """
    Panel for minimap settings.
    
    This panel provides options for configuring the GTA V minimap
    coordinate system and boundaries.
    """
    bl_label = "Minimap Settings"
    bl_idname = "SCALEFORM_PT_minimap_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Scaleform"
    bl_parent_id = "SCALEFORM_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        """Draw the panel header."""
        self.layout.label(icon='WORDWRAP_ON')

    def draw(self, context):
        """Draw the panel contents."""
        layout = self.layout
        settings = context.scene.scaleform_settings
        
        # World boundaries box
        box = layout.box()
        box.label(text="World Boundaries:", icon='WORLD')
        box.prop(settings, "minimap_preset", text="Preset")
        
        # Show custom boundaries if custom preset is selected
        if settings.minimap_preset == 'CUSTOM':
            col = box.column(align=True)
            col.prop(settings, "custom_world_min_x")
            col.prop(settings, "custom_world_max_x")
            col.prop(settings, "custom_world_min_y")
            col.prop(settings, "custom_world_max_y")
        
        # Minimap dimensions box
        box = layout.box()
        box.label(text="Minimap Dimensions:", icon='GRID')
        col = box.column(align=True)
        col.prop(settings, "minimap_width")
        col.prop(settings, "minimap_height")
        
        # Information box
        info_box = layout.box()
        info_box.label(text="Coordinate System:", icon='INFO')
        info_box.label(text="1 pixel in V represents 300x300 mm")
        info_box.label(text="in SVG format.")