import os
import time

import bpy
import numpy as np
from bpy.props import StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from mathutils import Matrix

from . import bl_utils as U
from .core import gfx_interior
from .core.convert import ConvertSettings, convert_level, detect_floors
from .core.geom import path_from_points
from .core.gfx_reader import read_interior

GEOMETRY_TYPES = {"MESH", "CURVE", "SURFACE", "META", "FONT"}


def settings(context):
    return context.scene.gfx_map


def map_objects(context):
    """Curves / flat meshes that go into the GFX (their 'Export' box ticked)."""
    st = settings(context)
    if st.source == "SELECTED":
        objs = [o for o in context.selected_objects if o.type in {"CURVE", "MESH"}]
    else:
        col = U.map_root()
        objs = [o for o in col.all_objects if o.type in {"CURVE", "MESH"}] if col else []
    return [o for o in objs if o.gfx_map.enabled]


def assign_style_material(obj):
    g = obj.gfx_map
    mat = U.material_for(tuple(g.fill_color) if g.use_fill else tuple(g.stroke_color))
    data = obj.data
    if data is None or not hasattr(data, "materials"):
        return
    if len(data.materials):
        data.materials[0] = mat
    else:
        data.materials.append(mat)


def level_z(st, index):
    for lv in st.levels:
        if lv.index == index:
            return lv.floor_z
    return index * 3.0


def ensure_level(st, index, floor_z=None, height=3.0):
    for lv in st.levels:
        if lv.index == index:
            return lv
    lv = st.levels.add()
    lv.index = index
    lv.floor_z = index * 3.0 if floor_z is None else floor_z
    lv.height = height
    return lv


# --------------------------------------------------------------------------- levels

class GFXMAP_OT_level_add(Operator):
    bl_idname = "gfx_map.level_add"
    bl_label = "Add Level"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        st = settings(context)
        idx = max((lv.index for lv in st.levels), default=-1) + 1
        top = max(((lv.floor_z + lv.height) for lv in st.levels), default=0.0)
        lv = ensure_level(st, idx, top, 3.0)
        U.level_collection(context.scene, idx)
        st.levels_index = list(st.levels).index(lv)
        return {"FINISHED"}


class GFXMAP_OT_level_remove(Operator):
    bl_idname = "gfx_map.level_remove"
    bl_label = "Remove Level"
    bl_description = "Remove the level. Its shapes are taken out of the minimap, not deleted"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        st = settings(context)
        return 0 <= st.levels_index < len(st.levels)

    def invoke(self, context, event):
        st = settings(context)
        if level_layers(context, st.levels[st.levels_index].index):
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        st = settings(context)
        index = st.levels[st.levels_index].index
        for o in level_layers(context, index):
            U.remove_from_map(o, context.scene)
        col = bpy.data.collections.get(U.level_collection_name(index))
        if col is not None and not col.all_objects and not col.children:
            bpy.data.collections.remove(col)
        st.levels.remove(st.levels_index)
        st.levels_index = max(0, min(st.levels_index, len(st.levels) - 1))
        return {"FINISHED"}


class GFXMAP_OT_setup(Operator):
    bl_idname = "gfx_map.setup"
    bl_label = "Create Minimap Collection"
    bl_description = "Create the 'GFX Map' collection with one sub-collection per level to start a minimap"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        st = settings(context)
        U.get_collection(context.scene)
        if not len(st.levels):
            ensure_level(st, 0, 0.0, 3.0)
            st.levels_index = 0
        for lv in st.levels:
            U.level_collection(context.scene, lv.index)
        self.report({"INFO"}, f"'{U.COLLECTION_NAME}' ready with {len(st.levels)} level(s)")
        return {"FINISHED"}


class GFXMAP_OT_level_select(Operator):
    bl_idname = "gfx_map.level_select"
    bl_label = "Show Level"
    bl_description = "Select this level in the Levels list"

    index: bpy.props.IntProperty()

    def execute(self, context):
        st = settings(context)
        lv = ensure_level(st, self.index)
        st.levels_index = list(st.levels).index(lv)
        return {"FINISHED"}


def source_triangles(context, objs):
    st = settings(context)
    to_local = U.origin_matrix(st).inverted()
    dg = context.evaluated_depsgraph_get()
    parts = [U.object_triangles(o, dg, to_local) for o in objs]
    parts = [p for p in parts if len(p)]
    return np.concatenate(parts) if parts else np.zeros((0, 3, 3))


def geometry_sources(context):
    col = bpy.data.collections.get(U.COLLECTION_NAME)
    skip = set(col.all_objects) if col else set()
    return [o for o in context.selected_objects if o.type in GEOMETRY_TYPES and o not in skip]


class GFXMAP_OT_levels_detect(Operator):
    bl_idname = "gfx_map.levels_detect"
    bl_label = "Detect Floors"
    bl_description = "Find floor heights from the up-facing area of the selected objects"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        objs = geometry_sources(context)
        if not objs:
            self.report({"ERROR"}, "Select the 3D objects of the interior")
            return {"CANCELLED"}
        tris = source_triangles(context, objs)
        floors = detect_floors(tris)
        if not floors:
            self.report({"ERROR"}, "No floors found")
            return {"CANCELLED"}
        st = settings(context)
        st.levels.clear()
        for i, (z, h) in enumerate(floors):
            ensure_level(st, i, z, h)
        st.levels_index = 0
        self.report({"INFO"}, "Floors: " + ", ".join(f"level_{i} z={z:.2f} h={h:.2f}" for i, (z, h) in enumerate(floors)))
        return {"FINISHED"}


class GFXMAP_OT_levels_from_rooms(Operator):
    bl_idname = "gfx_map.levels_from_rooms"
    bl_label = "From MLO Rooms"
    bl_description = "One level per room floor_id of the MLO archetype selected in Sollumz (heights from room bounds)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return U.sollumz_mlo_archetype(context) is not None

    def execute(self, context):
        st = settings(context)
        arch = U.sollumz_mlo_archetype(context)
        rooms = U.mlo_rooms_by_floor(arch)
        if not rooms:
            self.report({"ERROR"}, "The MLO has no rooms with bounds")
            return {"CANCELLED"}
        st.levels.clear()
        for fid in sorted(rooms):
            zmin = min(r[4] for r in rooms[fid])
            zmax = max(r[5] for r in rooms[fid])
            ensure_level(st, fid, zmin, max(zmax - zmin, 0.5))
        if not st.interior_name:
            st.interior_name = arch.name
        st.levels_index = 0
        self.report({"INFO"}, f"{len(rooms)} floor(s) from {arch.name}")
        return {"FINISHED"}


class GFXMAP_OT_name_from_sollumz(Operator):
    bl_idname = "gfx_map.name_from_sollumz"
    bl_label = "Use Sollumz MLO"
    bl_description = "Take the name of the MLO archetype selected in Sollumz"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return U.sollumz_mlo_archetype(context) is not None

    def execute(self, context):
        settings(context).interior_name = U.sollumz_mlo_archetype(context).name
        return {"FINISHED"}


# --------------------------------------------------------------------------- 3D -> curves

def convert_settings(st):
    return ConvertSettings(mode=st.mode, cell=st.cell, simplify=st.simplify, snap=st.snap, min_area=st.min_area,
                           close_gaps=st.close_gaps, remove_thin=st.remove_thin,
                           floor_tolerance=st.floor_tolerance, max_slope=st.max_slope, walls=st.walls,
                           wall_mode=st.wall_mode, obstacle_min=st.obstacle_min, obstacle_max=st.obstacle_max,
                           cut_height=st.cut_height, wall_width=st.wall_width)


class GFXMAP_OT_generate(Operator):
    bl_idname = "gfx_map.generate"
    bl_label = "3D to Curves"
    bl_description = ("Project the selected 3D objects onto each level and create 2D curves "
                      "(MLO-local metres) in the 'GFX Map' collection")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        st = settings(context)
        objs = geometry_sources(context)
        if not objs:
            self.report({"ERROR"}, "Select the 3D objects to convert (meshes, curves, text...)")
            return {"CANCELLED"}
        t0 = time.perf_counter()
        tris = source_triangles(context, objs)
        if not len(tris):
            self.report({"ERROR"}, "The selection has no faces")
            return {"CANCELLED"}
        if not len(st.levels):
            for i, (z, h) in enumerate(detect_floors(tris)):
                ensure_level(st, i, z, h)
        rooms = {}
        if st.clip_to_rooms:
            arch = U.sollumz_mlo_archetype(context)
            if arch is None:
                self.report({"WARNING"}, "Clip to MLO Rooms: no Sollumz MLO archetype selected, not clipping")
            else:
                rooms = U.mlo_rooms_by_floor(arch)
        cs = convert_settings(st)
        root = U.get_collection(context.scene)
        base = U.origin_matrix(st)
        made = 0
        lines = []
        for lv in st.levels:
            if not lv.enabled:
                continue
            clip = None
            if st.clip_to_rooms and rooms:
                clip = [r[:4] for r in rooms.get(lv.index, [])]
                if not clip:
                    lines.append(f"{U.level_clip_name(lv.index)}: no rooms with floor_id {lv.index}")
                    continue
            try:
                res = convert_level(tris, lv.floor_z, lv.height, cs, clip)
            except ValueError as e:
                self.report({"ERROR"}, str(e))
                return {"CANCELLED"}
            if st.replace:
                for o in list(root.all_objects):
                    if o.gfx_map.generated and o.gfx_map.level == lv.index:
                        data = o.data
                        bpy.data.objects.remove(o)
                        if data is not None and data.users == 0:
                            bpy.data.curves.remove(data)
            clip_name = U.level_clip_name(lv.index)
            sub = U.get_collection(context.scene, f"GFX {clip_name}", root)
            mw = base @ Matrix.Translation((0, 0, lv.floor_z + 0.02))
            others = level_layers(context, lv.index)
            new = []
            for kind, loops, color in (("floor", res["floor"], st.floor_color),
                                       ("walls", res["walls"], st.wall_color)):
                if not loops:
                    continue
                label = "obstacles" if kind == "walls" and st.wall_mode == "OBSTACLES" else kind
                obj = U.new_curve_object(f"{clip_name}_{label}", [path_from_points(l) for l in loops], sub, mw)
                g = obj.gfx_map
                g.level, g.generated = lv.index, kind
                g.preset = "CUSTOM"
                g.fill_color = color
                assign_style_material(obj)
                new.append(obj)
                made += 1
                lines.append(f"{clip_name} {kind}: {len(loops)} loop(s)")
            # floor at the bottom, walls above it, hand-made layers keep their order on top
            for k, o in enumerate(new + [o for o in others if o not in new]):
                o.gfx_map.order = k
        dt = time.perf_counter() - t0
        self.report({"INFO"}, f"{made} curve object(s) in {dt:.2f}s. " + "; ".join(lines))
        return {"FINISHED"}


# --------------------------------------------------------------------------- styles

class GFXMAP_OT_apply_preset(Operator):
    bl_idname = "gfx_map.apply_preset"
    bl_label = "Apply Style to Selected"
    bl_description = "Copy the active curve's level and style to every selected curve"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        src = context.active_object.gfx_map
        n = 0
        for o in context.selected_objects:
            if o.type not in {"CURVE", "MESH"}:
                continue
            g = o.gfx_map
            if o != context.active_object:
                for k in ("level", "order", "preset", "use_fill", "fill_color", "use_stroke",
                          "stroke_color", "stroke_width"):
                    setattr(g, k, getattr(src, k))
            assign_style_material(o)
            n += 1
        self.report({"INFO"}, f"Style applied to {n} object(s)")
        return {"FINISHED"}


# --------------------------------------------------------------------------- layer order

def layer_level(context):
    """Level shown in the Layers panel and the preview: the one selected in the Levels list."""
    st = settings(context)
    if 0 <= st.levels_index < len(st.levels):
        return st.levels[st.levels_index].index
    o = context.active_object
    if o is not None and o.type in {"CURVE", "MESH"} and o in layer_candidates(context):
        return o.gfx_map.level
    return 0


def layer_candidates(context):
    col = U.map_root()
    objs = set(o for o in col.all_objects if o.type in {"CURVE", "MESH"}) if col else set()
    if settings(context).source == "SELECTED":
        objs |= set(o for o in context.selected_objects if o.type in {"CURVE", "MESH"})
    return objs


def level_layers(context, level):
    """Objects of a level in export (draw) order: first = bottom, last = on top."""
    objs = [o for o in layer_candidates(context) if o.gfx_map.level == level]
    return sorted(objs, key=lambda o: (o.gfx_map.order, o.name))


class GFXMAP_OT_layer_move(Operator):
    bl_idname = "gfx_map.layer_move"
    bl_label = "Move Layer"
    bl_description = "Change the draw order of a curve inside its level"
    bl_options = {"REGISTER", "UNDO"}

    name: StringProperty(description="Object to move (empty = active object)")
    direction: bpy.props.EnumProperty(items=[
        ("UP", "Bring Forward", "One step towards the top"),
        ("DOWN", "Send Backward", "One step towards the bottom"),
        ("TOP", "Bring to Front", "Draw above every other curve of the level"),
        ("BOTTOM", "Send to Back", "Draw below every other curve of the level")])

    def execute(self, context):
        obj = bpy.data.objects.get(self.name) if self.name else context.active_object
        if obj is None:
            return {"CANCELLED"}
        layers = level_layers(context, obj.gfx_map.level)
        if obj not in layers:
            self.report({"ERROR"}, f"{obj.name} is not a minimap curve")
            return {"CANCELLED"}
        i = layers.index(obj)
        layers.pop(i)
        j = {"UP": i + 1, "DOWN": i - 1, "TOP": len(layers), "BOTTOM": 0}[self.direction]
        layers.insert(max(0, min(j, len(layers))), obj)
        # renumber the whole level so the order is explicit and stable
        for k, o in enumerate(layers):
            o.gfx_map.order = k
        return {"FINISHED"}


def unassigned_shapes(context):
    """Curves in the view layer that are not part of the minimap yet."""
    root = U.map_root()
    inside = set(root.all_objects) if root else set()
    return [o for o in context.view_layer.objects if o.type == "CURVE" and o not in inside]


class GFXMAP_OT_layer_assign(Operator):
    bl_idname = "gfx_map.layer_assign"
    bl_label = "Assign Selected"
    bl_description = ("Add the selected curves / flat meshes to the selected level: they move into its "
                      "collection and go on top of the draw order")
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return any(o.type in {"CURVE", "MESH"} for o in context.selected_objects)

    def execute(self, context):
        st = settings(context)
        level = layer_level(context)
        ensure_level(st, level)
        layers = level_layers(context, level)
        picked = sorted((o for o in context.selected_objects if o.type in {"CURVE", "MESH"}),
                        key=lambda o: (o.gfx_map.order, o.name))
        for o in picked:
            was_in_map = U.in_map(o)
            U.move_to_level(o, context.scene, level)
            o.gfx_map.level = level
            o.gfx_map.enabled = True
            if o in layers:
                layers.remove(o)
            layers.append(o)
            if not was_in_map:
                o.gfx_map.generated = ""
                assign_style_material(o)
        for k, o in enumerate(layers):
            o.gfx_map.order = k
        self.report({"INFO"}, f"{len(picked)} shape(s) on {U.level_clip_name(level)}")
        return {"FINISHED"}


class GFXMAP_OT_layer_new(Operator):
    bl_idname = "gfx_map.layer_new"
    bl_label = "New Shape"
    bl_description = "Add a 4 x 4 m 2D curve on the selected level, ready to edit"
    bl_options = {"REGISTER", "UNDO"}

    preset: bpy.props.EnumProperty(name="Preset", items=[(k, v[0], "") for k, v in U.PRESETS.items()],
                                   default="ACCESSIBLE")

    def execute(self, context):
        st = settings(context)
        level = layer_level(context)
        ensure_level(st, level)
        layers = level_layers(context, level)
        mw = U.origin_matrix(st) @ Matrix.Translation((0, 0, level_z(st, level) + 0.02))
        name = U.PRESETS[self.preset][0].split(" ")[0].lower()
        obj = U.new_curve_object(name, [path_from_points([(-2, -2), (2, -2), (2, 2), (-2, 2)])],
                                 U.level_collection(context.scene, level), mw)
        g = obj.gfx_map
        g.level, g.order = level, len(layers)
        g.preset = self.preset
        assign_style_material(obj)
        for o in context.selected_objects:
            o.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        return {"FINISHED"}


class GFXMAP_OT_layer_remove(Operator):
    bl_idname = "gfx_map.layer_remove"
    bl_label = "Remove from Minimap"
    bl_description = "Take the active shape out of the minimap (the object is kept, outside the GFX Map collection)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        o = context.active_object
        return o is not None and U.in_map(o)

    def execute(self, context):
        obj = context.active_object
        level = obj.gfx_map.level
        U.remove_from_map(obj, context.scene)
        for k, o in enumerate(level_layers(context, level)):
            o.gfx_map.order = k
        self.report({"INFO"}, f"{obj.name} removed from the minimap")
        return {"FINISHED"}


class GFXMAP_OT_layer_select(Operator):
    bl_idname = "gfx_map.layer_select"
    bl_label = "Select Layer"
    bl_description = "Select this curve (Shift: add to the selection)"
    bl_options = {"REGISTER", "UNDO"}

    name: StringProperty()

    def invoke(self, context, event):
        obj = bpy.data.objects.get(self.name)
        if obj is None or obj.name not in context.view_layer.objects:
            return {"CANCELLED"}
        if not event.shift:
            for o in context.selected_objects:
                o.select_set(False)
        obj.hide_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        return {"FINISHED"}


# --------------------------------------------------------------------------- export / import

def build_interior(context, report, require_hash=True):
    st = settings(context)
    h = st.get_hash()
    if h is None:
        if require_hash:
            report({"ERROR"}, "Set the MLO name (or its hash)")
            return None
        h = 0
    objs = map_objects(context)
    if not objs:
        report({"ERROR"}, "No curves to export (generate them or put curves in the 'GFX Map' collection)")
        return None
    to_local = U.origin_matrix(st).inverted()
    dg = context.evaluated_depsgraph_get()
    levels = {}
    for o in sorted(objs, key=lambda o: (o.gfx_map.order, o.name)):
        g = o.gfx_map
        paths = U.curve_paths(o, to_local) if o.type == "CURVE" else U.mesh_paths(o, dg, to_local)
        if not paths:
            continue
        fill = tuple(int(round(c * 255)) for c in g.fill_color) if g.use_fill else None
        layer = gfx_interior.Layer(paths, fill=fill,
                                   stroke_width=g.stroke_width if g.use_stroke else 0.0,
                                   stroke=tuple(int(round(c * 255)) for c in g.stroke_color), name=o.name)
        levels.setdefault(g.level, gfx_interior.Level(g.level)).layers.append(layer)
    if not levels:
        report({"ERROR"}, "The curves have no splines")
        return None
    name = st.interior_name.strip()
    linkage = name if name and not name.isdigit() and not name.lower().startswith(("0x", "int")) else ""
    return gfx_interior.InteriorMap(hash=h, levels=list(levels.values()), scale=int(st.scale),
                                    curve_tolerance=st.curve_tolerance, linkage_name=linkage,
                                    levels_visible=st.levels_visible, separate_shapes=st.separate_shapes)


class GFXMAP_OT_export(Operator):
    bl_idname = "gfx_map.export"
    bl_label = "Export GFX"
    bl_description = "Write int<hash>.gfx for the minimap (stream it in FiveM or put it in the minimap rpf)"

    def execute(self, context):
        st = settings(context)
        im = build_interior(context, self.report)
        if im is None:
            return {"CANCELLED"}
        try:
            data = gfx_interior.build(im)
        except ValueError as e:
            self.report({"ERROR"}, f"GFX build failed: {e}")
            return {"CANCELLED"}
        folder = bpy.path.abspath(st.output_dir or "//")
        if not folder or folder == "//":
            self.report({"ERROR"}, "Save the .blend or choose an output folder")
            return {"CANCELLED"}
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, im.file_name)
        with open(path, "wb") as f:
            f.write(data)
        levels = ", ".join(lv.clip_name for lv in sorted(im.levels, key=lambda lv: lv.index))
        self.report({"INFO"}, f"Wrote {path} ({len(data)} bytes; {levels})")
        return {"FINISHED"}


class GFXMAP_OT_import(Operator, ImportHelper):
    bl_idname = "gfx_map.import_gfx"
    bl_label = "Import GFX"
    bl_description = "Load an interior minimap .gfx/.swf as editable curves"
    bl_options = {"REGISTER", "UNDO"}
    filename_ext = ".gfx"
    filter_glob: StringProperty(default="*.gfx;*.swf", options={"HIDDEN"})

    def execute(self, context):
        st = settings(context)
        try:
            with open(self.filepath, "rb") as f:
                res = read_interior(f.read())
        except (OSError, ValueError, IndexError) as e:
            self.report({"ERROR"}, f"Cannot read {os.path.basename(self.filepath)}: {e}")
            return {"CANCELLED"}
        if res["hash"] is not None and not st.interior_name.strip():
            st.interior_name = str(res["hash"])
        root = U.get_collection(context.scene)
        base = U.origin_matrix(st)
        count = 0
        for idx in sorted(res["levels"]):
            ensure_level(st, idx)
            clip_name = U.level_clip_name(idx)
            sub = U.get_collection(context.scene, f"GFX {clip_name}", root)
            mw = base @ Matrix.Translation((0, 0, level_z(st, idx) + 0.02))
            existing = level_layers(context, idx)
            for k, o in enumerate(existing):
                o.gfx_map.order = k
            for order, layer in enumerate(res["levels"][idx]):
                obj = U.new_curve_object(f"{clip_name}_{order:02d}", layer["paths"], sub, mw)
                g = obj.gfx_map
                g.level, g.order, g.preset = idx, len(existing) + order, "CUSTOM"
                if layer["fill"]:
                    g.use_fill = True
                    g.fill_color = [c / 255 for c in layer["fill"]]
                else:
                    g.use_fill = False
                if layer.get("stroke"):
                    w, col = layer["stroke"]
                    g.use_stroke, g.stroke_width = True, w
                    g.stroke_color = [c / 255 for c in col]
                assign_style_material(obj)
                count += 1
        self.report({"INFO"}, f"Imported {count} shape(s) on {len(res['levels'])} level(s), label {res['label']}")
        return {"FINISHED"}


class GFXMAP_OT_preview(Operator):
    bl_idname = "gfx_map.preview"
    bl_label = "Preview"
    bl_description = ("Build the GFX in memory and render the level as the minimap draws it "
                      "(shown in an Image Editor)")

    open_window: bpy.props.BoolProperty(default=True, options={"SKIP_SAVE"})

    def execute(self, context):
        from . import preview
        img = preview.update(context, self.report)
        if img is None:
            return {"CANCELLED"}
        if self.open_window:
            preview.show(context, img)
        return {"FINISHED"}


class GFXMAP_OT_preview_level(Operator):
    bl_idname = "gfx_map.preview_level"
    bl_label = "Preview Level"
    bl_description = "Preview the previous / next level"

    step: bpy.props.IntProperty(default=1)

    def execute(self, context):
        from . import preview
        st = settings(context)
        levels = preview.available_levels(context)
        if not levels:
            return {"CANCELLED"}
        cur = preview.current_level(context)
        if cur in levels:
            i = (levels.index(cur) + self.step) % len(levels)
        else:
            i = 0
        st.preview_follow = False
        st.preview_level = levels[i]
        preview.update(context, self.report)
        return {"FINISHED"}


class GFXMAP_OT_import_ybn(Operator, ImportHelper):
    bl_idname = "gfx_map.import_ybn"
    bl_label = "Import Collision (.ybn.xml)"
    bl_description = ("Load an MLO collision exported as XML (CodeWalker / Sollumz) as a mesh in MLO-local space, "
                      "selected and ready for 3D to Curves")
    bl_options = {"REGISTER", "UNDO"}
    filename_ext = ".xml"
    filter_glob: StringProperty(default="*.ybn.xml;*.xml", options={"HIDDEN"})

    def execute(self, context):
        from .core.ybn_xml import read_ybn_xml
        try:
            tris = read_ybn_xml(self.filepath)
        except Exception as e:  # malformed XML, missing nodes
            self.report({"ERROR"}, f"Cannot read {os.path.basename(self.filepath)}: {e}")
            return {"CANCELLED"}
        if not len(tris):
            self.report({"ERROR"}, "No collision polygons in the file")
            return {"CANCELLED"}
        name = os.path.basename(self.filepath).split(".")[0]
        verts = tris.reshape(-1, 3)
        me = bpy.data.meshes.new(name)
        me.vertices.add(len(verts))
        me.vertices.foreach_set("co", verts.ravel())
        me.loops.add(len(verts))
        me.loops.foreach_set("vertex_index", np.arange(len(verts)))
        me.polygons.add(len(tris))
        me.polygons.foreach_set("loop_start", np.arange(0, len(verts), 3))
        me.polygons.foreach_set("loop_total", np.full(len(tris), 3))
        me.update(calc_edges=True)
        me.validate()
        obj = bpy.data.objects.new(name, me)
        context.scene.collection.objects.link(obj)
        obj.matrix_world = U.origin_matrix(settings(context))
        obj.display_type = "WIRE"
        for o in context.selected_objects:
            o.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        st = settings(context)
        if not st.interior_name.strip():
            st.interior_name = name
        self.report({"INFO"}, f"{len(tris)} collision triangles from {name}")
        return {"FINISHED"}


class GFXMAP_OT_copy_native(Operator):
    bl_idname = "gfx_map.copy_native"
    bl_label = "Copy Script Line"
    bl_description = "Copy a SetRadarAsInteriorThisFrame call (fake interior placement) to the clipboard"

    text: StringProperty()

    def execute(self, context):
        context.window_manager.clipboard = self.text
        self.report({"INFO"}, self.text)
        return {"FINISHED"}


classes = (GFXMAP_OT_level_add, GFXMAP_OT_level_remove, GFXMAP_OT_levels_detect, GFXMAP_OT_levels_from_rooms,
           GFXMAP_OT_name_from_sollumz, GFXMAP_OT_generate, GFXMAP_OT_apply_preset, GFXMAP_OT_export,
           GFXMAP_OT_import, GFXMAP_OT_copy_native, GFXMAP_OT_layer_move, GFXMAP_OT_layer_select,
           GFXMAP_OT_preview, GFXMAP_OT_preview_level, GFXMAP_OT_setup, GFXMAP_OT_level_select,
           GFXMAP_OT_layer_assign, GFXMAP_OT_layer_new, GFXMAP_OT_layer_remove, GFXMAP_OT_import_ybn)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
