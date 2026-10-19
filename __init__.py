"""MLOScaleformTool: 3D interiors -> 2D curves -> minimap interior .gfx (Scaleform)."""

from . import ops, preview, props, ui

_modules = (props, ops, preview, ui)


def register():
    for m in _modules:
        m.register()


def unregister():
    for m in reversed(_modules):
        m.unregister()
