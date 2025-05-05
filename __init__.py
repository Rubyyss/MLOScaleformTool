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

    print(
        f"Registered {_bl_info['name']} v{'.'.join(str(v) for v in _bl_info['version'])}"
    )


def unregister():
    """Unregister the add-on from Blender."""
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
