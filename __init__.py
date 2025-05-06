"""
GTA V Scaleform Minimap Calculator
=================================

A Blender add-on for exporting curves as SVGs for GTA V Scaleform minimaps.

This add-on provides tools for converting between Blender, GTA V world, and
Scaleform coordinate systems, making it easier to create accurate minimap
representations of in-game locations.

Author: rubyys
Version: 1.0.1
Blender: 4.4.0+
"""

bl_info = {
    "name": "GTA V Scaleform Minimap Calculator",
    "author": "rubyys",
    "version": (1, 0, 1),
    "blender": (4, 4, 0),
    "location": "View3D > Sidebar > Scaleform",
    "description": "Export Blender curves to SVG for GTA V Scaleform minimap with coordinate conversion",
    "category": "Import-Export",
}

import bpy
import os
import sys
from importlib import reload
from bpy.app.handlers import persistent

# Add module path if running as script
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.append(script_dir)

# Create a global reference to bl_info
_bl_info = bl_info.copy()

# Import all modules (after creating _bl_info)
from . import constants
from . import geometry
from . import utils
from . import core
from . import ui


# Scene handler functions moved directly to this file to avoid circular imports
@persistent
def on_file_load(dummy):
    """
    Handler called when a new file is loaded.
    This ensures visualizations are cleared when opening a new project.
    """
    # Clear all caches to ensure we don't have stale data
    from .utils.cache import clear_all_caches
    clear_all_caches()
    
    # Disable any active visualization
    if bpy.context:
        try:
            # Import here to avoid circular imports
            from .ui.visualization import disable_visualization, clear_visualization_data
            # First disable the visualization
            disable_visualization(bpy.context)
            # Then clear all visualization data
            clear_visualization_data()
            
            # Force a redraw of all 3D viewports
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
        except Exception as e:
            print(f"Error during visualization cleanup on file load: {e}")
    
    # Reset the visualization enabled property if it exists
    try:
        for scene in bpy.data.scenes:
            if hasattr(scene, "scaleform_vis_enabled"):
                scene.scaleform_vis_enabled = False
    except Exception as e:
        print(f"Error resetting visualization property: {e}")


@persistent
def on_scene_change(dummy):
    """
    Handler called when switching between scenes.
    This ensures visualizations match the current scene.
    """
    # Disable any active visualization in old scene
    if bpy.context:
        try:
            # Import here to avoid circular imports
            from .ui.visualization import disable_visualization, clear_visualization_data
            # First disable the visualization
            disable_visualization(bpy.context)
            # Then clear all visualization data
            clear_visualization_data()
            
            # Force a redraw of all 3D viewports
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
        except Exception as e:
            print(f"Error during visualization cleanup on scene change: {e}")
    
    # Make sure the UI reflects the correct state
    try:
        if hasattr(bpy.context, "scene") and bpy.context.scene and hasattr(bpy.context.scene, "scaleform_vis_enabled"):
            bpy.context.scene.scaleform_vis_enabled = False
    except Exception as e:
        print(f"Error updating visualization UI state: {e}")


# Added new handler for more reliable cleanup
@persistent
def on_load_pre(dummy):
    """
    Handler called just before a new file is loaded.
    This ensures visualizations are cleared before opening a new project.
    """
    # Clear all caches first
    from .utils.cache import clear_all_caches
    clear_all_caches()
    
    # Try to disable visualization before loading new file
    if bpy.context:
        try:
            from .ui.visualization import disable_visualization, clear_visualization_data
            disable_visualization(bpy.context)
            clear_visualization_data()
        except Exception as e:
            print(f"Error during pre-load visualization cleanup: {e}")


def register_scene_handlers():
    """Register the scene and file handlers."""
    # Check if handlers are already registered to avoid duplicates
    if on_load_pre not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(on_load_pre)
        
    if on_file_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(on_file_load)
        
    # For Blender 4.x, use the appropriate handler
    # Blender 4.0+ uses depsgraph_update_post instead of scene_update_post
    if hasattr(bpy.app.handlers, "depsgraph_update_post"):
        if on_scene_change not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(on_scene_change)
    elif hasattr(bpy.app.handlers, "scene_update_post"):
        if on_scene_change not in bpy.app.handlers.scene_update_post:
            bpy.app.handlers.scene_update_post.append(on_scene_change)


def unregister_scene_handlers():
    """Unregister the scene and file handlers."""
    # Remove all handler references
    if on_load_pre in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(on_load_pre)
        
    if on_file_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(on_file_load)
        
    # Try both handler types for compatibility
    if hasattr(bpy.app.handlers, "depsgraph_update_post"):
        if on_scene_change in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(on_scene_change)
    
    if hasattr(bpy.app.handlers, "scene_update_post"):
        if on_scene_change in bpy.app.handlers.scene_update_post:
            bpy.app.handlers.scene_update_post.remove(on_scene_change)


def reload_modules():
    """Reload all modules for development."""
    # Reload in dependency order
    reload(constants)

    # Geometry package
    reload(geometry.base)
    reload(geometry.matrix)
    reload(geometry.utils)
    reload(geometry)

    # Utils package
    reload(utils.cache)
    reload(utils.helpers)
    reload(utils)

    # Core package
    reload(core.calculator)
    reload(core.processor)
    reload(core.exporter)
    reload(core)

    # UI package last
    reload(ui.properties)
    reload(ui.visualization)
    reload(ui.operators)
    reload(ui.panels)
    reload(ui)


def register():
    """Register the add-on with Blender."""
    # Force unregister first to prevent double registration
    force_unregister()

    # Reload modules in development mode
    if hasattr(bpy.app, "debug") and bpy.app.debug:
        reload_modules()

    # Step 1: Register property group class
    bpy.utils.register_class(ui.ScaleformCalculatorSettings)

    # Step 2: Register pointer property for scene
    bpy.types.Scene.scaleform_settings = bpy.props.PointerProperty(
        type=ui.ScaleformCalculatorSettings
    )

    # Step 3: Register additional scene properties
    ui.register()

    # Step 4: Register UI classes in correct order
    for cls in ui.classes:
        if cls.__name__ != "ScaleformCalculatorSettings" and not hasattr(
            bpy.types, cls.__name__
        ):
            try:
                bpy.utils.register_class(cls)
            except Exception as e:
                print(f"Error registering {cls.__name__}: {e}")

    # Step 5: Register scene handlers for visualization cleanup
    register_scene_handlers()
    
    # Step 6: Ensure no visualization is active initially
    try:
        from .ui.visualization import clear_visualization_data
        clear_visualization_data()
    except Exception as e:
        print(f"Error clearing visualization data during registration: {e}")

    print(
        f"Registered {_bl_info['name']} v{'.'.join(str(v) for v in _bl_info['version'])}"
    )


def unregister():
    """Unregister the add-on from Blender."""
    # First disable any active visualizations
    try:
        from .ui.visualization import disable_visualization, clear_visualization_data
        if bpy.context:
            disable_visualization(bpy.context)
        clear_visualization_data()
    except Exception as e:
        print(f"Error cleaning up visualization during unregister: {e}")
    
    # Then unregister scene handlers to prevent errors during cleanup
    unregister_scene_handlers()

    # Clear all caches
    utils.clear_all_caches()

    # Step 1: Unregister UI classes in reverse order
    for cls in reversed(ui.classes):
        try:
            if cls.__name__ != "ScaleformCalculatorSettings" and hasattr(
                bpy.types, cls.__name__
            ):
                bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Error unregistering {cls.__name__}: {e}")

    # Step 2: Unregister additional scene properties
    ui.unregister()

    # Step 3: Unregister the pointer property
    if hasattr(bpy.types.Scene, "scaleform_settings"):
        del bpy.types.Scene.scaleform_settings

    # Step 4: Unregister the property group class
    try:
        bpy.utils.unregister_class(ui.ScaleformCalculatorSettings)
    except Exception as e:
        print(f"Error unregistering ScaleformCalculatorSettings: {e}")

    print(f"Unregistered {_bl_info['name']}")


def force_unregister():
    """Force unregister if already registered to prevent double registration."""
    try:
        # First disable any active visualizations
        try:
            from .ui.visualization import disable_visualization, clear_visualization_data
            if bpy.context:
                disable_visualization(bpy.context)
            clear_visualization_data()
        except Exception as e:
            print(f"Error cleaning up visualization during force unregister: {e}")
            
        # Import locally to avoid import errors during first installation
        from . import ui

        # First unregister properties
        try:
            ui.unregister()
        except:
            pass

        # Unregister scene settings property
        if hasattr(bpy.types.Scene, "scaleform_settings"):
            del bpy.types.Scene.scaleform_settings

        # Unregister UI classes in reverse order
        for cls in reversed(ui.classes):
            try:
                if hasattr(bpy.types, cls.__name__):
                    bpy.utils.unregister_class(cls)
            except:
                pass

    except Exception as e:
        print(f"Error during force unregister: {e}")


if __name__ == "__main__":
    register()