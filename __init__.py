"""
GTA V Scaleform Minimap Calculator Add-on for Blender.

This add-on provides tools for exporting Blender curves to SVG format
for use in GTA V Scaleform minimap creation.

It handles coordinate conversion between Blender, world, and Scaleform
coordinate systems, and provides visualization tools to help with positioning.
"""

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

# Force unregister if already registered to prevent double registration
def force_unregister():
    try:
        # Import locally to avoid import errors during first installation
        from . import ui
        
        # Unregister UI classes in reverse order
        for cls in reversed(ui.classes):
            try:
                if hasattr(bpy.types, cls.__name__):
                    bpy.utils.unregister_class(cls)
            except:
                pass
                
        # Unregister scene properties
        if hasattr(bpy.types.Scene, "scaleform_settings"):
            del bpy.types.Scene.scaleform_settings
            
        # Try to unregister scene properties using the UI module
        try:
            from . import ui
            ui.unregister_scene_properties()
        except:
            pass
            
    except Exception as e:
        print(f"Error during force unregister: {e}")

# Add module path if running as script
if __name__ == "__main__":
    # Get the directory the script is in
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.append(script_dir)

# Create a global reference to bl_info that can be imported by other modules
_bl_info = bl_info.copy()

# Local modules - import only after setting up _bl_info
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
    if hasattr(ui, "visualization"):
        reload(ui.visualization)
    reload(ui.operators)
    reload(ui.panels)
    reload(ui)

def register():
    """Register the add-on with Blender."""
    # Make sure we're not already registered
    force_unregister()
    
    # If in development mode, reload modules
    if hasattr(bpy.app, "debug") and bpy.app.debug:
        reload_modules()
    
    # Register UI classes with checks
    for cls in ui.classes:
        if not hasattr(bpy.types, cls.__name__):
            try:
                bpy.utils.register_class(cls)
            except Exception as e:
                print(f"Error registering {cls.__name__}: {e}")
    
    # Register scene properties if not already registered
    if not hasattr(bpy.types.Scene, "scaleform_settings"):
        bpy.types.Scene.scaleform_settings = bpy.props.PointerProperty(type=ui.ScaleformCalculatorSettings)
        
    # Register additional scene properties
    ui.register_scene_properties()
    
    # Print success message
    print(f"Registered {_bl_info['name']} v{'.'.join(str(v) for v in _bl_info['version'])}")

def unregister():
    """Unregister the add-on from Blender."""
    # Clear caches
    utils.clear_all_caches()
    
    # Unregister scene properties
    if hasattr(bpy.types.Scene, "scaleform_settings"):
        del bpy.types.Scene.scaleform_settings
        
    # Unregister additional scene properties
    ui.unregister_scene_properties()
    
    # Unregister UI classes in reverse order
    for cls in reversed(ui.classes):
        try:
            if hasattr(bpy.types, cls.__name__):
                bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Error unregistering {cls.__name__}: {e}")
    
    # Print success message
    print(f"Unregistered {_bl_info['name']}")

if __name__ == "__main__":
    register()