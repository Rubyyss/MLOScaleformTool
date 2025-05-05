"""
Visualization module for GTA V Scaleform Minimap Calculator.

This module provides visualization capabilities for curves in the 3D viewport,
displaying dimensions, bounds, orientation, and coordinate systems.
"""

import bpy
import gpu
import blf
from gpu_extras.batch import batch_for_shader
from bpy.types import Operator, Panel
from bpy.props import BoolProperty, FloatProperty, IntProperty
from mathutils import Vector, Matrix
import math

from ..constants import (
    BOUNDS_COLOR,
    REAL_BOUNDS_COLOR,
    DIRECTION_COLOR,
    CENTER_COLOR,
    LINE_WIDTH,
    EXPORT_DIRECTION_COLOR,
)
from ..geometry import GPointF, GRectF
from ..geometry.utils import GeometryUtils
from ..core import CurveProcessor
from ..utils.cache import curve_cache

# Global variables for visualization
_handle_3d = None
_visualization_enabled = False
_visualization_data = {}


def clear_visualization_data():
    """
    Clear all visualization data.
    
    This function resets the global visualization state variables, ensuring
    that no data persists between scene changes or file loads.
    """
    global _visualization_data, _visualization_enabled, _handle_3d
    
    # Reset the data dictionary
    _visualization_data = {}
    
    # Set enabled flag to False
    _visualization_enabled = False
    
    # Clear the handle (if not already cleared by disable_visualization)
    # We don't remove the draw handler here as that should be done by disable_visualization
    # This is just a safety measure
    _handle_3d = None


def draw_3d_callback():
    """
    Callback function for 3D drawing.
    This function is called by Blender to draw 3D elements in the viewport.
    """
    global _visualization_enabled, _visualization_data

    if not _visualization_enabled or _visualization_data is None:
        return

    # Configure OpenGL for drawing
    gpu.state.line_width_set(LINE_WIDTH)

    # Draw 3D elements
    if "bounds" in _visualization_data:
        draw_bounds(_visualization_data["bounds"])

    if "center" in _visualization_data:
        draw_center(_visualization_data["center"])

    # Only draw direction arrow if axes are enabled
    if (
        _visualization_data.get("show_axes", True)
        and "direction" in _visualization_data
        and "center" in _visualization_data
    ):
        draw_direction(_visualization_data["center"], _visualization_data["direction"])

    # Only draw axes and export direction if show_axes is enabled
    if _visualization_data.get("show_axes", True) and "center" in _visualization_data:
        draw_axes(
            _visualization_data["center"],
            _visualization_data.get("dimensions", (1, 1, 1)),
        )
        # Draw export direction indicator (orange arrow pointing in -Y direction)
        draw_export_direction(
            _visualization_data["center"],
            _visualization_data.get("dimensions", (1, 1, 1)),
        )

    if _visualization_data.get("show_grid", False) and "center" in _visualization_data:
        draw_grid(
            _visualization_data["center"],
            _visualization_data.get("grid_size", 10),
            _visualization_data.get("grid_divisions", 10),
        )

    # Restore OpenGL state
    gpu.state.line_width_set(1.0)


def draw_2d_callback():
    """Draw 2D elements in the viewport (text overlays)."""
    global _visualization_enabled, _visualization_data

    if not _visualization_enabled or not _visualization_data:
        return

    # Empty function - we no longer display dimension text in the viewport


def draw_bounds(bounds):
    """Draw a bounding box."""
    min_point, max_point = bounds

    # Generate coordinates for the bounds cube
    vertices = []

    # Bottom face
    vertices.extend(
        [
            (min_point[0], min_point[1], min_point[2]),
            (max_point[0], min_point[1], min_point[2]),
            (max_point[0], min_point[1], min_point[2]),
            (max_point[0], max_point[1], min_point[2]),
            (max_point[0], max_point[1], min_point[2]),
            (min_point[0], max_point[1], min_point[2]),
            (min_point[0], max_point[1], min_point[2]),
            (min_point[0], min_point[1], min_point[2]),
        ]
    )

    # Top face
    vertices.extend(
        [
            (min_point[0], min_point[1], max_point[2]),
            (max_point[0], min_point[1], max_point[2]),
            (max_point[0], min_point[1], max_point[2]),
            (max_point[0], max_point[1], max_point[2]),
            (max_point[0], max_point[1], max_point[2]),
            (min_point[0], max_point[1], max_point[2]),
            (min_point[0], max_point[1], max_point[2]),
            (min_point[0], min_point[1], max_point[2]),
        ]
    )

    # Connecting lines
    vertices.extend(
        [
            (min_point[0], min_point[1], min_point[2]),
            (min_point[0], min_point[1], max_point[2]),
            (max_point[0], min_point[1], min_point[2]),
            (max_point[0], min_point[1], max_point[2]),
            (max_point[0], max_point[1], min_point[2]),
            (max_point[0], max_point[1], max_point[2]),
            (min_point[0], max_point[1], min_point[2]),
            (min_point[0], max_point[1], max_point[2]),
        ]
    )

    # Draw the cube lines
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, "LINES", {"pos": vertices})

    shader.bind()
    shader.uniform_float("color", BOUNDS_COLOR)
    batch.draw(shader)


def draw_center(center):
    """Draw a marker at the center point."""
    size = 0.1
    vertices = [
        (center[0] - size, center[1], center[2]),
        (center[0] + size, center[1], center[2]),
        (center[0], center[1] - size, center[2]),
        (center[0], center[1] + size, center[2]),
        (center[0], center[1], center[2] - size),
        (center[0], center[1], center[2] + size),
    ]

    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, "LINES", {"pos": vertices})

    shader.bind()
    shader.uniform_float("color", CENTER_COLOR)
    batch.draw(shader)


def draw_direction(center, direction):
    """Draw an arrow showing the direction."""
    # Calculate end point of the arrow
    end_point = (
        center[0] + direction[0],
        center[1] + direction[1],
        center[2] + direction[2],
    )

    # Draw main line
    vertices = [center, end_point]
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, "LINES", {"pos": vertices})

    shader.bind()
    shader.uniform_float("color", DIRECTION_COLOR)
    batch.draw(shader)

    # Draw arrow head
    draw_arrow_head(center, end_point, DIRECTION_COLOR)


def draw_export_direction(center, dimensions):
    """
    Draw an orange arrow indicating the export direction (-Y axis).
    This helps users understand the orientation for SVG export.
    """
    # Get length based on dimensions for consistency with other axes
    axis_length = max(dimensions) * 0.5

    # Calculate end point (pointing in -Y direction)
    end_point = (center[0], center[1] - axis_length, center[2])  # Negative Y direction

    # Draw main line
    vertices = [center, end_point]
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, "LINES", {"pos": vertices})

    shader.bind()
    shader.uniform_float("color", EXPORT_DIRECTION_COLOR)
    batch.draw(shader)

    # Draw arrow head
    draw_arrow_head(center, end_point, EXPORT_DIRECTION_COLOR)

    # Draw "Export Direction" label
    draw_text_3d("Export Direction", end_point, EXPORT_DIRECTION_COLOR, size=14)


def draw_arrow_head(start, end, color, size=0.1):
    """
    Draw an arrow head.

    Args:
        start: Start point
        end: End point
        color: Arrow color
        size: Size of the head
    """
    # Calculate direction vector and normalize it
    direction = Vector((end[0] - start[0], end[1] - start[1], end[2] - start[2]))
    length = direction.length

    if length < 0.0001:
        return

    direction.normalize()

    # Find a perpendicular vector to construct the head
    if abs(direction.z) < 0.9:
        perpendicular = direction.cross(Vector((0, 0, 1)))
    else:
        perpendicular = direction.cross(Vector((1, 0, 0)))

    perpendicular.normalize()
    perpendicular2 = direction.cross(perpendicular)

    # Calculate arrow head points
    arrow_size = size * length
    arrow_tip = Vector(end)
    arrow_base = arrow_tip - direction * arrow_size

    # Create points for the head shape
    p1 = arrow_base + perpendicular * arrow_size * 0.5
    p2 = arrow_base - perpendicular * arrow_size * 0.5
    p3 = arrow_base + perpendicular2 * arrow_size * 0.5
    p4 = arrow_base - perpendicular2 * arrow_size * 0.5

    # Create vertices for the head (cone shape)
    vertices = [
        (arrow_tip[0], arrow_tip[1], arrow_tip[2]),
        (p1[0], p1[1], p1[2]),
        (arrow_tip[0], arrow_tip[1], arrow_tip[2]),
        (p2[0], p2[1], p2[2]),
        (arrow_tip[0], arrow_tip[1], arrow_tip[2]),
        (p3[0], p3[1], p3[2]),
        (arrow_tip[0], arrow_tip[1], arrow_tip[2]),
        (p4[0], p4[1], p4[2]),
    ]

    # Draw the head
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, "LINES", {"pos": vertices})

    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def draw_grid(center, grid_size, grid_divisions):
    """Draw a reference grid."""
    # Calculate cell size
    cell_size = grid_size / grid_divisions

    # Start coordinates for the grid
    start_x = center[0] - grid_size / 2
    start_y = center[1] - grid_size / 2
    z_pos = center[2]  # Grid height

    # Create grid lines
    vertices = []

    # Create vertical lines (parallel to Y axis)
    for i in range(grid_divisions + 1):
        x = start_x + i * cell_size
        vertices.append((x, start_y, z_pos))
        vertices.append((x, start_y + grid_size, z_pos))

    # Create horizontal lines (parallel to X axis)
    for i in range(grid_divisions + 1):
        y = start_y + i * cell_size
        vertices.append((start_x, y, z_pos))
        vertices.append((start_x + grid_size, y, z_pos))

    # Draw the grid
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, "LINES", {"pos": vertices})

    shader.bind()
    shader.uniform_float("color", (0.5, 0.5, 0.5, 0.3))  # Light gray grid
    batch.draw(shader)


def draw_axes(center, dimensions):
    """Draw coordinate axes."""
    # Get length for axes based on dimensions
    axis_length = max(dimensions) * 0.5

    # End points of the axes
    x_end = (center[0] + axis_length, center[1], center[2])
    y_end = (center[0], center[1] + axis_length, center[2])
    z_end = (center[0], center[1], center[2] + axis_length)

    # Draw X axis (red)
    vertices = [center, x_end]
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, "LINES", {"pos": vertices})
    shader.bind()
    shader.uniform_float("color", (1.0, 0.0, 0.0, 1.0))  # Red
    batch.draw(shader)
    draw_arrow_head(center, x_end, (1.0, 0.0, 0.0, 1.0))

    # Draw Y axis (green)
    vertices = [center, y_end]
    batch = batch_for_shader(shader, "LINES", {"pos": vertices})
    shader.bind()
    shader.uniform_float("color", (0.0, 1.0, 0.0, 1.0))  # Green
    batch.draw(shader)
    draw_arrow_head(center, y_end, (0.0, 1.0, 0.0, 1.0))

    # Draw Z axis (blue)
    vertices = [center, z_end]
    batch = batch_for_shader(shader, "LINES", {"pos": vertices})
    shader.bind()
    shader.uniform_float("color", (0.0, 0.0, 1.0, 1.0))  # Blue
    batch.draw(shader)
    draw_arrow_head(center, z_end, (0.0, 0.0, 1.0, 1.0))

    # Add text labels
    draw_text_3d("X", x_end, (1.0, 0.0, 0.0, 1.0))
    draw_text_3d("Y", y_end, (0.0, 1.0, 0.0, 1.0))
    draw_text_3d("Z", z_end, (0.0, 0.0, 1.0, 1.0))


def draw_text_3d(text, position, color=(1, 1, 1, 1), size=12, align="CENTER"):
    """Draw text at a 3D position in the viewport."""
    import blf
    from bpy_extras.view3d_utils import location_3d_to_region_2d

    region = bpy.context.region
    rv3d = bpy.context.region_data

    # Convert 3D position to 2D screen coordinates
    coord_2d = location_3d_to_region_2d(region, rv3d, position)

    if coord_2d is None:
        return

    # Set font properties
    font_id = 0  # default font
    blf.position(font_id, coord_2d[0], coord_2d[1], 0)

    # Updated for Blender 4.4 - the syntax has changed
    blf.size(font_id, size)  # Remove the DPI parameter (72)

    blf.color(font_id, *color)

    # Handle alignment
    if align != "LEFT":
        text_width, text_height = blf.dimensions(font_id, text)
        if align == "CENTER":
            blf.position(font_id, coord_2d[0] - text_width / 2, coord_2d[1], 0)
        elif align == "RIGHT":
            blf.position(font_id, coord_2d[0] - text_width, coord_2d[1], 0)

    # Draw the text
    blf.draw(font_id, text)


def draw_dimension_text(dimensions):
    """Draw text with dimension information on the screen."""
    # Configure blf
    import blf

    font_id = 0  # Default font
    blf.size(font_id, 16)  # Updated for Blender 4.0+ API
    blf.color(font_id, 1.0, 1.0, 1.0, 1.0)  # White

    # Calculate position on screen
    region = bpy.context.region
    width, height = region.width, region.height

    # Text to display
    width_text = f"Width: {dimensions[0]:.2f}"
    height_text = f"Height: {dimensions[1]:.2f}"
    depth_text = f"Depth: {dimensions[2]:.2f}"

    # Draw text in the upper right corner
    x_pos = width - 180
    y_pos = height - 30

    blf.position(font_id, x_pos, y_pos, 0)
    blf.draw(font_id, width_text)

    blf.position(font_id, x_pos, y_pos - 24, 0)
    blf.draw(font_id, height_text)

    blf.position(font_id, x_pos, y_pos - 48, 0)
    blf.draw(font_id, depth_text)


def enable_visualization(context):
    """Enable visualization in the 3D viewport."""
    global _handle_3d, _visualization_enabled

    if _handle_3d is None:
        # Register 3D drawing callback
        _handle_3d = bpy.types.SpaceView3D.draw_handler_add(
            draw_3d_callback, (), "WINDOW", "POST_VIEW"
        )

        _visualization_enabled = True

        # Force viewport update
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()

        return True
    return False


def disable_visualization(context):
    """Disable visualization in the 3D viewport."""
    global _handle_3d, _visualization_enabled
    
    # Check if the handle exists
    if _handle_3d is not None:
        try:
            # Try to remove the draw handler
            bpy.types.SpaceView3D.draw_handler_remove(_handle_3d, "WINDOW")
        except Exception as e:
            # If there's an error (e.g., if the handler is already removed),
            # just log and continue
            print(f"Warning: Failed to remove 3D visualization handler: {e}")
        finally:
            # Always set handle to None to ensure we don't try to remove it again
            _handle_3d = None
    
    # Set enabled flag to False
    _visualization_enabled = False
    
    # Make sure the scene property reflects this state
    if context and hasattr(context, "scene") and context.scene and hasattr(context.scene, "scaleform_vis_enabled"):
        context.scene.scaleform_vis_enabled = False
    
    # Force viewport update if possible
    try:
        if context and hasattr(context, "screen") and context.screen:
            for area in context.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()
    except Exception as e:
        print(f"Warning: Failed to update viewport: {e}")
    
    return True


def update_visualization_data(context):
    """Update visualization data based on selected curves."""
    global _visualization_data

    # First, clear the visualization data
    _visualization_data = {}

    # Clear the cache to force recalculation
    from ..utils.cache import curve_cache
    curve_cache.clear()

    # Force viewport update to clear old visualization
    try:
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
    except:
        pass  # Ignore errors if context or screen is invalid

    # Process the selected curves - use force refresh to skip cache
    try:
        curve_data = CurveProcessor.force_refresh_curve_data(context)
    except Exception as e:
        print(f"Error refreshing curve data: {e}")
        # Fallback if the force_refresh_curve_data method is not available or fails
        try:
            curve_data = CurveProcessor.get_selected_curves(context, use_cache=False)
        except Exception as e2:
            print(f"Error getting selected curves: {e2}")
            return False

    if not curve_data["valid"]:
        return False

    # Extract bounds
    bounds = curve_data["bounds"]
    min_x, min_y = bounds.left, bounds.top
    max_x, max_y = bounds.right, bounds.bottom

    # Get all points to find Z bounds
    all_points = []

    for curve_obj in context.selected_objects:
        if curve_obj.type != "CURVE":
            continue

        matrix_world = curve_obj.matrix_world

        for spline in curve_obj.data.splines:
            if spline.type == "BEZIER":
                for point in spline.bezier_points:
                    # Transform point to global space
                    global_co = matrix_world @ point.co
                    all_points.append(global_co)
            else:
                for point in spline.points:
                    # Transform point to global space
                    global_co = matrix_world @ Vector(
                        (point.co[0], point.co[1], point.co[2])
                    )
                    all_points.append(global_co)

    # Calculate Z bounds
    min_z = min(p.z for p in all_points) if all_points else 0
    max_z = max(p.z for p in all_points) if all_points else 0

    # Store data for visualization
    _visualization_data = {
        "bounds": ((min_x, min_y, min_z), (max_x, max_y, max_z)),
        "center": ((min_x + max_x) / 2, (min_y + max_y) / 2, (min_z + max_z) / 2),
        "dimensions": (max_x - min_x, max_y - min_y, max_z - min_z),
        "show_grid": context.scene.scaleform_vis_show_grid,
        "show_axes": context.scene.scaleform_vis_show_axes,
        "grid_size": context.scene.scaleform_vis_grid_size,
        "grid_divisions": context.scene.scaleform_vis_grid_divisions,
    }

    # Calculate direction (use the orientation of the first curve object)
    if context.selected_objects:
        selected_curves = [
            obj for obj in context.selected_objects if obj.type == "CURVE"
        ]
        if selected_curves:
            direction = selected_curves[0].matrix_world.to_3x3() @ Vector((1, 0, 0))
            direction.normalize()
            _visualization_data["direction"] = (direction.x, direction.y, direction.z)

    # Force viewport update
    try:
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
    except:
        pass  # Ignore errors if context or screen is invalid

    return True


class SCALEFORM_OT_toggle_visualization(Operator):
    """
    Toggle visualization for dimensions and orientation.
    """

    bl_idname = "scaleform.toggle_visualization"
    bl_label = "Toggle Visualization"
    bl_description = (
        "Toggle visualization of dimensions and orientation in the 3D viewport"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        global _visualization_enabled

        if _visualization_enabled:
            # Disable visualization
            if disable_visualization(context):
                # Clear all visualization data
                clear_visualization_data()
                context.scene.scaleform_vis_enabled = False
                self.report({"INFO"}, "Visualization disabled")
            else:
                self.report({"ERROR"}, "Failed to disable visualization")
        else:
            # Update visualization data
            if update_visualization_data(context):
                # Enable visualization
                if enable_visualization(context):
                    context.scene.scaleform_vis_enabled = True
                    self.report({"INFO"}, "Visualization enabled")
                else:
                    self.report({"ERROR"}, "Failed to enable visualization")
            else:
                self.report({"ERROR"}, "No valid curve data found")

        return {"FINISHED"}


class SCALEFORM_OT_update_visualization(Operator):
    """
    Update the visualization based on currently selected curves.
    """

    bl_idname = "scaleform.update_visualization"
    bl_label = "Update Visualization"
    bl_description = "Update visualization with currently selected curves"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        # Only enable if visualization is active
        global _visualization_enabled
        return context.scene.scaleform_vis_enabled and _visualization_enabled

    def execute(self, context):
        # Debug info - comment out if not needed
        global _visualization_enabled
        print(
            f"Update visualization requested. Visualization enabled: {_visualization_enabled}"
        )
        print(
            f"Selected curves: {[obj.name for obj in context.selected_objects if obj.type == 'CURVE']}"
        )

        # Temporarily disable visualization to force a refresh
        was_enabled = _visualization_enabled

        if was_enabled:
            disable_visualization(context)

        # Update visualization data
        result = update_visualization_data(context)

        # Re-enable visualization if it was previously enabled
        if was_enabled:
            enable_visualization(context)

        if result:
            self.report({"INFO"}, "Visualization updated")
        else:
            self.report({"ERROR"}, "No valid curve data found")
        return {"FINISHED"}


class SCALEFORM_PT_visualization_panel(Panel):
    """
    Panel for controlling curve visualization.
    """

    bl_label = "Visualization"
    bl_idname = "SCALEFORM_PT_visualization_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Scaleform"
    bl_parent_id = "SCALEFORM_PT_main_panel"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        # Always show this panel if the main panel is visible
        return True

    def draw_header(self, context):
        """Draw the panel header."""
        self.layout.label(icon="OUTLINER_OB_EMPTY")

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Toggle and update buttons
        row = layout.row()
        if scene.scaleform_vis_enabled:
            row.operator(
                "scaleform.toggle_visualization",
                text="Hide Visualization",
                icon="HIDE_ON",
            )
            row = layout.row()
            row.operator("scaleform.update_visualization", icon="FILE_REFRESH")
        else:
            row.operator(
                "scaleform.toggle_visualization",
                text="Show Visualization",
                icon="HIDE_OFF",
            )

        # Visualization options (only show if active)
        if scene.scaleform_vis_enabled:
            box = layout.box()
            box.label(text="Visualization Options:")

            # Show/hide grid
            row = box.row()
            row.prop(scene, "scaleform_vis_show_grid", text="Show Grid", icon="GRID")

            # Show/hide axes
            row = box.row()
            row.prop(
                scene,
                "scaleform_vis_show_axes",
                text="Show Axes",
                icon="ORIENTATION_VIEW",
            )

            # Grid size
            if scene.scaleform_vis_show_grid:
                row = box.row(align=True)
                row.prop(scene, "scaleform_vis_grid_size", text="Size")
                row.prop(scene, "scaleform_vis_grid_divisions", text="Divisions")

            # Dimensions
            global _visualization_data
            if _visualization_data and "dimensions" in _visualization_data:
                dimensions = _visualization_data["dimensions"]
                dimension_box = layout.box()
                dimension_box.label(text="Dimensions:", icon="DRIVER_DISTANCE")

                col = dimension_box.column(align=True)
                col.label(text=f"Width: {dimensions[0]:.2f}")
                col.label(text=f"Height: {dimensions[1]:.2f}")
                col.label(text=f"Depth: {dimensions[2]:.2f}")


# Support for persistent preferences
class SCALEFORM_PersistentPreferences(bpy.types.AddonPreferences):
    """
    Persistent preferences for the Scaleform Calculator addon.

    These preferences will be saved with Blender and persist between sessions.
    """

    # This must match the addon name
    bl_idname = "MLOScaleformTools"

    center_at_origin: bpy.props.BoolProperty(
        name="Center at Origin",
        description="Center the exported SVG at the origin (persists between sessions)",
        default=False,
    )

    use_comma_separator: bpy.props.BoolProperty(
        name="Use Comma as Decimal",
        description="Use comma instead of period as decimal separator (persists between sessions)",
        default=False,
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Persistent Preferences:")

        col = layout.column()
        col.prop(self, "center_at_origin")
        col.prop(self, "use_comma_separator")


# Custom handlers for property changes to sync with preferences
def update_center_at_origin(self, context):
    """Handler for center_at_origin property updates."""
    save_to_preferences()
    return None


def update_use_comma_separator(self, context):
    """Handler for use_comma_separator property updates."""
    save_to_preferences()
    return None


def sync_scene_with_preferences():
    """
    Synchronize scene properties with addon preferences.

    This ensures that persistent settings are used when the addon is loaded.
    """
    try:
        # Get preferences
        addon_prefs = bpy.context.preferences.addons["MLOScaleformTools"].preferences
        # Get settings
        settings = bpy.context.scene.scaleform_settings

        # Sync persistent properties
        settings.center_at_origin = addon_prefs.center_at_origin
        settings.use_comma_separator = addon_prefs.use_comma_separator
    except:
        pass


def save_to_preferences():
    """
    Save current settings to persistent preferences.

    This is called when settings are changed to ensure they persist.
    """
    try:
        # Get preferences
        addon_prefs = bpy.context.preferences.addons["MLOScaleformTools"].preferences
        # Get settings
        settings = bpy.context.scene.scaleform_settings

        # Save to preferences
        addon_prefs.center_at_origin = settings.center_at_origin
        addon_prefs.use_comma_separator = settings.use_comma_separator
    except:
        pass


# Register functions to add to the UI package
def register_visualization_properties():
    """Register properties for controlling visualization."""
    global _visualization_data, _visualization_enabled

    # Get preferences if available
    addon_prefs = None
    try:
        addon_prefs = bpy.context.preferences.addons["MLOScaleformTools"].preferences
    except:
        pass

    # Property for tracking visualization state
    bpy.types.Scene.scaleform_vis_enabled = BoolProperty(
        name="Visualization Enabled",
        description="Whether visualization is currently enabled",
        default=False,
    )

    # Property for showing/hiding grid
    bpy.types.Scene.scaleform_vis_show_grid = BoolProperty(
        name="Show Grid",
        description="Display a reference grid",
        default=False,
        update=lambda self, context: update_grid_visibility(),
    )

    # Property for showing/hiding axes
    bpy.types.Scene.scaleform_vis_show_axes = BoolProperty(
        name="Show Axes",
        description="Display coordinate axes and export direction",
        default=True,
        update=lambda self, context: update_axes_visibility(),
    )

    # Property for grid size
    bpy.types.Scene.scaleform_vis_grid_size = FloatProperty(
        name="Grid Size",
        description="Total size of the grid",
        default=10.0,
        min=0.1,
        max=100.0,
        update=lambda self, context: update_grid_size(),
    )

    # Property for grid divisions
    bpy.types.Scene.scaleform_vis_grid_divisions = IntProperty(
        name="Grid Divisions",
        description="Number of divisions in the grid",
        default=10,
        min=1,
        max=100,
        update=lambda self, context: update_grid_divisions(),
    )

    # Sync property with persistent preferences
    if addon_prefs:
        # Update the scene properties to match persistent preferences
        sync_scene_with_preferences()


def update_grid_visibility():
    """Update grid visibility based on property change."""
    global _visualization_data
    if _visualization_data:
        _visualization_data["show_grid"] = bpy.context.scene.scaleform_vis_show_grid
        # Force viewport update
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def update_axes_visibility():
    """Update axes visibility based on property change."""
    global _visualization_data
    if _visualization_data:
        _visualization_data["show_axes"] = bpy.context.scene.scaleform_vis_show_axes
        # Force viewport update
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def update_grid_size():
    """Update grid size based on property change."""
    global _visualization_data
    if _visualization_data:
        _visualization_data["grid_size"] = bpy.context.scene.scaleform_vis_grid_size
        # Force viewport update
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def update_grid_divisions():
    """Update grid divisions based on property change."""
    global _visualization_data
    if _visualization_data:
        _visualization_data["grid_divisions"] = (
            bpy.context.scene.scaleform_vis_grid_divisions
        )
        # Force viewport update
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def unregister_visualization_properties():
    """Remove registered visualization properties."""
    props_to_remove = [
        "scaleform_vis_enabled",
        "scaleform_vis_show_grid",
        "scaleform_vis_show_axes",
        "scaleform_vis_grid_size",
        "scaleform_vis_grid_divisions",
    ]

    for prop in props_to_remove:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)


# Classes to register with Blender
visualization_classes = [
    SCALEFORM_OT_toggle_visualization,
    SCALEFORM_OT_update_visualization,
    SCALEFORM_PT_visualization_panel,
    SCALEFORM_PersistentPreferences,
]