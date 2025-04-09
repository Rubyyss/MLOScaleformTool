"""
GTA V Scaleform Minimap Calculator Add-on for Blender.

This add-on provides tools for exporting Blender curves to SVG format
for use in GTA V Scaleform minimap creation.

It handles coordinate conversion between Blender, world, and Scaleform
coordinate systems, and provides visualization tools to help with positioning.
"""

# Define bl_info at the top of the file
bl_info = {
    "name": "MLOScaleformTools",
    "author": "rubyys",
    "version": (2, 2, 1),
    "blender": (4, 4, 0),
    "location": "View3D > Sidebar > Scaleform",
    "description": "Export Blender curves to SVG for GTA V Scaleform minimap with visualization tools and multi-curve support",
    "category": "Import-Export",
}

import bpy
import os
import sys
from importlib import reload

# Add module path if running as script
if __name__ == "__main__":
    # Get the directory the script is in
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.append(script_dir)

# Local modules
from . import constants
from . import geometry
from . import utils
from . import core
from . import ui

def reload_modules():
    """Reload all modules for development."""
    reload(constants)
    
    # Reload geometry package
    reload(geometry.base)
    reload(geometry.matrix)
    reload(geometry.utils)
    reload(geometry)
    
    # Reload utils package
    reload(utils.cache)
    reload(utils.helpers)
    reload(utils)
    
    # Reload core package
    reload(core.calculator)
    reload(core.processor)
    reload(core.exporter)
    reload(core)
    
    # Reload UI package
    reload(ui.properties)
    reload(ui.visualization)
    reload(ui.operators)
    reload(ui.panels)
    reload(ui)

def register():
    """Register the add-on with Blender."""
    # If in development mode, reload modules
    if hasattr(bpy.app, "debug") and bpy.app.debug:
        reload_modules()
    
    # Register UI classes
    for cls in ui.classes:
        bpy.utils.register_class(cls)
    
    # Register scene properties
    bpy.types.Scene.scaleform_settings = bpy.props.PointerProperty(type=ui.ScaleformCalculatorSettings)
    ui.register_scene_properties()
    
    # Print success message
    print(f"Registered {bl_info['name']} v{'.'.join(str(v) for v in bl_info['version'])}")

def unregister():
    """Unregister the add-on from Blender."""
    # Clear caches
    utils.clear_all_caches()
    
    # Unregister scene properties
    if hasattr(bpy.types.Scene, "scaleform_settings"):
        del bpy.types.Scene.scaleform_settings
    ui.unregister_scene_properties()
    
    # Unregister UI classes in reverse order
    for cls in reversed(ui.classes):
        bpy.utils.unregister_class(cls)
    
    # Print success message
    print(f"Unregistered {bl_info['name']}")

if __name__ == "__main__":
    register()