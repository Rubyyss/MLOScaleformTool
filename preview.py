"""Minimap preview: builds the .gfx in memory, renders one level and shows it in Blender."""

import bpy

from .core import gfx_interior
from .core.gfx_reader import read_interior
from .core.preview import content_bounds, render_levels

IMAGE_NAME = "GFX Map Preview"
last_info = {}
_pending = {"timer": False}


def _settings(context):
    return context.scene.gfx_map


def available_levels(context):
    from .ops import layer_candidates
    return sorted({o.gfx_map.level for o in layer_candidates(context)})


def current_level(context):
    st = _settings(context)
    if st.preview_follow:
        from .ops import layer_level
        return layer_level(context)
    return st.preview_level


def update(context, report=None):
    """Render the preview image. Returns the image or None."""
    from .ops import build_interior
    st = _settings(context)
    msgs = []
    im = build_interior(context, (report or (lambda lvl, msg: msgs.append(msg))), require_hash=False)
    if im is None:
        return None
    try:
        data = gfx_interior.build(im)
        res = read_interior(data)
    except (ValueError, IndexError) as e:
        if report:
            report({"ERROR"}, f"GFX build failed: {e}")
        return None
    level = current_level(context)
    levels = res["levels"]
    rgba, info = render_levels(levels, level, size=st.preview_size,
                               background=tuple(int(round(c * 255)) for c in st.preview_background),
                               grid=st.preview_grid, origin=st.preview_origin, ghost_below=st.preview_ghost,
                               frame=content_bounds(levels))
    h, w = rgba.shape[:2]
    img = bpy.data.images.get(IMAGE_NAME)
    if img is None:
        img = bpy.data.images.new(IMAGE_NAME, w, h, alpha=False)
    elif tuple(img.size) != (w, h):
        img.scale(w, h)
    img.pixels.foreach_set(rgba.ravel())
    img.update()
    last_info.clear()
    last_info.update(level=level, size=(w, h), ppm=info["ppm"], bytes=len(data),
                     levels=sorted(levels), shapes=sum(len(v) for v in levels.values()))
    for win in context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "IMAGE_EDITOR" and area.spaces.active.image == img:
                area.tag_redraw()
    return img


def show(context, img):
    """Show the image in an existing Image Editor, else in a new window."""
    for win in context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "IMAGE_EDITOR" and area.spaces.active.image == img:
                return
    for win in context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "IMAGE_EDITOR":
                area.spaces.active.image = img
                return
    before = set(context.window_manager.windows[:])
    bpy.ops.wm.window_new()
    new = [w for w in context.window_manager.windows if w not in before]
    if not new:
        return
    area = max(new[0].screen.areas, key=lambda a: a.width * a.height)
    area.type = "IMAGE_EDITOR"
    space = area.spaces.active
    space.image = img
    with context.temp_override(window=new[0], area=area, region=area.regions[-1]):
        try:
            bpy.ops.image.view_all(fit_view=True)
        except RuntimeError:
            pass


# --------------------------------------------------------------------------- auto refresh

def _refresh():
    _pending["timer"] = False
    wm = bpy.context.window_manager
    if not wm.windows:
        return None
    win = wm.windows[0]
    with bpy.context.temp_override(window=win, scene=win.scene):
        ctx = bpy.context
        if ctx.scene.gfx_map.preview_auto and bpy.data.images.get(IMAGE_NAME):
            try:
                update(ctx)
            except Exception as e:  # never break the depsgraph loop
                print("GFX Map preview:", e)
    return None


def _on_depsgraph(scene, depsgraph):
    st = getattr(scene, "gfx_map", None)
    if st is None or not st.preview_auto or _pending["timer"]:
        return
    if not bpy.data.images.get(IMAGE_NAME):
        return
    for u in depsgraph.updates:
        idt = u.id
        if isinstance(idt, (bpy.types.Object, bpy.types.Curve, bpy.types.Mesh, bpy.types.Scene)):
            _pending["timer"] = True
            bpy.app.timers.register(_refresh, first_interval=0.35)
            return


def register():
    if _on_depsgraph not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph)


def unregister():
    if _on_depsgraph in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_depsgraph)
    if bpy.app.timers.is_registered(_refresh):
        bpy.app.timers.unregister(_refresh)
