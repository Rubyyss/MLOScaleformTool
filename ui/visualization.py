"""
Visualization tools for GTA V Scaleform Minimap Calculator addon.

This module provides 3D visualization functionality to help users
understand the mapping of curves to minimap coordinates.
"""

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from typing import List, Tuple, Any, Optional

from ..constants import (
    BOUNDS_COLOR, REAL_BOUNDS_COLOR, DIRECTION_COLOR, 
    CENTER_COLOR, LINE_WIDTH
)
from ..geometry.utils import GeometryUtils
from ..geometry import GPointF, GRectF

def draw_callback_bounds(self, context):
    """
    OpenGL drawing callback for bounds visualization.
    
    This function is called by Blender to draw bounds visualization
    in the 3D viewport.
    
    Args:
        self: Owner operator instance
        context: Current context
    """
    # Only draw if we have valid data
    if not context.scene.scaleform_has_valid_data:
        return

    # Get the operator class that stores the visualization data
    cls = bpy.types.SCALEFORM_OT_toggle_bounds_display
    if not hasattr(cls, "calculated_bounds") or cls.calculated_bounds is None:
        return
        
    # Create the shader for drawing lines
    shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
    
    # Draw calculated bounds
    if hasattr(cls, "calculated_bounds"):
        coords = GeometryUtils.create_bounds_coordinates(cls.calculated_bounds)
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": coords})
        shader.bind()
        shader.uniform_float("color", BOUNDS_COLOR)
        gpu.state.line_width_set(LINE_WIDTH)
        batch.draw(shader)
    
    # Draw real bounds
    if hasattr(cls, "real_bounds"):
        coords = GeometryUtils.create_bounds_coordinates(cls.real_bounds)
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": coords})
        shader.bind()
        shader.uniform_float("color", REAL_BOUNDS_COLOR)
        gpu.state.line_width_set(LINE_WIDTH)
        batch.draw(shader)
    
    # Draw center point
    if hasattr(cls, "center_point"):
        center_x, center_y = cls.center_point.x, cls.center_point.y
        cross_size = 0.5
        center_coords = [
            (center_x - cross_size, center_y, 0),
            (center_x + cross_size, center_y, 0),
            (center_x, center_y - cross_size, 0),
            (center_x, center_y + cross_size, 0)
        ]
        batch = batch_for_shader(shader, 'LINES', {"pos": center_coords})
        shader.bind()
        shader.uniform_float("color", CENTER_COLOR)
        gpu.state.line_width_set(LINE_WIDTH)
        batch.draw(shader)
    
    # Draw direction arrow
    if hasattr(cls, "center_point"):
        # Default direction is down (-Y in Blender)
        direction = GPointF(0, -1)
        arrow_coords = GeometryUtils.create_arrow_coordinates(cls.center_point, direction, size=2.0)
        batch = batch_for_shader(shader, 'LINES', {"pos": arrow_coords})
        shader.bind()
        shader.uniform_float("color", DIRECTION_COLOR)
        gpu.state.line_width_set(LINE_WIDTH)
        batch.draw(shader)
    
    # Reset line width to avoid affecting other drawing
    gpu.state.line_width_set(1.0)

def create_preview_mesh(context, curve_data, settings):
    """
    Create a preview mesh for the minimap.
    
    This creates a visual representation of how the curve will appear
    on the minimap.
    
    Args:
        context: Blender context
        curve_data: Processed curve data
        settings: Addon settings
        
    Returns:
        Created mesh object or None if failed
    """
    if not curve_data.get("valid", False):
        return None
    
    # Create a new mesh and object
    preview_mesh = bpy.data.meshes.new(name="MinimapPreview")
    preview_obj = bpy.data.objects.new("MinimapPreview", preview_mesh)
    
    # Link to the scene
    context.collection.objects.link(preview_obj)
    
    # Set as selected and active
    for obj in context.selected_objects:
        obj.select_set(False)
    preview_obj.select_set(True)
    context.view_layer.objects.active = preview_obj
    
    # Create vertices and edges for the bounds
    verts = []
    edges = []
    
    # Create bounds rectangle
    bounds = curve_data["bounds"]
    bounds_verts = [
        (bounds.left, bounds.top, 0.1),
        (bounds.right, bounds.top, 0.1),
        (bounds.right, bounds.bottom, 0.1),
        (bounds.left, bounds.bottom, 0.1)
    ]
    
    # Add vertices and edges for bounds
    base_idx = len(verts)
    verts.extend(bounds_verts)
    edges.extend([
        (base_idx, base_idx + 1),
        (base_idx + 1, base_idx + 2),
        (base_idx + 2, base_idx + 3),
        (base_idx + 3, base_idx)
    ])
    
    # Create center cross
    center = curve_data["center"]
    cross_size = 0.3
    center_verts = [
        (center.x - cross_size, center.y, 0.1),
        (center.x + cross_size, center.y, 0.1),
        (center.x, center.y - cross_size, 0.1),
        (center.x, center.y + cross_size, 0.1)
    ]
    
    # Add vertices and edges for center cross
    base_idx = len(verts)
    verts.extend(center_verts)
    edges.extend([
        (base_idx, base_idx + 1),
        (base_idx + 2, base_idx + 3)
    ])
    
    # Create the mesh from vertices and edges
    preview_mesh.from_pydata(verts, edges, [])
    preview_mesh.update()
    
    # Add a material to make it visible
    if "MinimapPreviewMaterial" not in bpy.data.materials:
        mat = bpy.data.materials.new("MinimapPreviewMaterial")
        mat.diffuse_color = (0.2, 0.8, 0.2, 1.0)
        mat.use_nodes = True
    else:
        mat = bpy.data.materials["MinimapPreviewMaterial"]
    
    preview_obj.data.materials.append(mat)
    
    return preview_obj

def remove_preview_mesh():
    """
    Remove any existing minimap preview mesh objects.
    """
    for obj in bpy.data.objects:
        if obj.name.startswith("MinimapPreview"):
            bpy.data.objects.remove(obj, do_unlink=True)
    
    # Clean up any unused meshes
    for mesh in bpy.data.meshes:
        if mesh.name.startswith("MinimapPreview") and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    
    # Clean up any unused materials
    if "MinimapPreviewMaterial" in bpy.data.materials and bpy.data.materials["MinimapPreviewMaterial"].users == 0:
        bpy.data.materials.remove(bpy.data.materials["MinimapPreviewMaterial"])
