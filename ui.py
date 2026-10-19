import bpy
from bpy.types import Panel, UIList

from . import bl_utils as U
from .ops import layer_candidates, layer_level, level_layers, map_objects, settings, unassigned_shapes


def measure(context):
    """Per-level bounds (MLO-local metres) of the curves that will be exported."""
    st = settings(context)
    to_local = U.origin_matrix(st).inverted()
    levels = {}
    for o in map_objects(context):
        m = to_local @ o.matrix_world
        if o.type == "CURVE":
            pts = []
            for sp in o.data.splines:
                if sp.type == "BEZIER":
                    pts += [m @ b.co for b in sp.bezier_points]
                else:
                    pts += [m @ p.co.to_3d() for p in sp.points]
        else:
            pts = [m @ v.co for v in o.data.vertices]
        if not pts:
            continue
        b = levels.setdefault(o.gfx_map.level, [1e30, 1e30, -1e30, -1e30, 0])
        b[0] = min(b[0], min(p.x for p in pts))
        b[1] = min(b[1], min(p.y for p in pts))
        b[2] = max(b[2], max(p.x for p in pts))
        b[3] = max(b[3], max(p.y for p in pts))
        b[4] += 1
    return levels


class GFXMAP_UL_levels(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        row.label(text=U.level_clip_name(item.index))
        row.prop(item, "floor_z", text="Z")
        row.prop(item, "height", text="H")


class GFXMAP_UL_layers(UIList):
    """Shapes of the selected level over bpy.data.objects, top of the draw order first."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        g = item.gfx_map
        row = layout.row(align=True)
        sw = row.row(align=True)
        sw.ui_units_x = 1.3
        sw.prop(g, "fill_color" if g.use_fill else "stroke_color", text="")
        row.prop(item, "name", text="", emboss=False,
                 icon="OUTLINER_OB_CURVE" if item.type == "CURVE" else "OUTLINER_OB_MESH")
        if g.generated:
            row.label(text="", icon="MOD_REMESH")
        row.prop(g, "enabled", text="", emboss=False,
                 icon="CHECKBOX_HLT" if g.enabled else "CHECKBOX_DEHLT")
        row.prop(item, "hide_viewport", text="", emboss=False)

    def filter_items(self, context, data, propname):
        objs = getattr(data, propname)
        level = layer_level(context)
        cand = layer_candidates(context)
        flags = [0] * len(objs)
        shown = []
        for i, o in enumerate(objs):
            if o in cand and o.gfx_map.level == level:
                if self.filter_name and self.filter_name.lower() not in o.name.lower():
                    continue
                flags[i] = self.bitflag_filter_item
                shown.append(i)
        shown.sort(key=lambda i: (objs[i].gfx_map.order, objs[i].name), reverse=True)
        order = [0] * len(objs)
        pos = 0
        for i in shown:
            order[i] = pos
            pos += 1
        for i in range(len(objs)):
            if not flags[i]:
                order[i] = pos
                pos += 1
        return flags, order


class _Base:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MLOScaleformTool"


class _NeedsMap(_Base):
    """Sub-panels appear once the 'GFX Map' collection exists."""

    @classmethod
    def poll(cls, context):
        return U.map_root() is not None


class GFXMAP_PT_interior(_Base, Panel):
    bl_label = "MLOScaleformTool"

    def draw(self, context):
        st = settings(context)
        lay = self.layout
        if U.map_root() is None:
            box = lay.box()
            col = box.column(align=True)
            col.label(text="Start a minimap", icon="WORLD")
            col.label(text="Creates the 'GFX Map' collection with")
            col.label(text="one sub-collection per level.")
            row = box.row()
            row.scale_y = 1.6
            row.operator("gfx_map.setup", icon="COLLECTION_NEW")
            box.operator("gfx_map.import_gfx", text="Or Import an Existing GFX", icon="IMPORT")
            return
        lay.use_property_split = True
        row = lay.row(align=True)
        row.prop(st, "interior_name")
        if hasattr(context.scene, "ytyps"):
            row.operator("gfx_map.name_from_sollumz", text="", icon="EYEDROPPER")
        h = st.get_hash()
        col = lay.column(align=True)
        if h is None:
            col.label(text="Name required: the file is int<joaat(name)>.gfx", icon="ERROR")
        else:
            col.label(text=f"Hash {h}  (0x{h:08X})")
            col.label(text=f"File  int{h}.gfx   Label  INT{h}")
        lay.prop(st, "origin")


class GFXMAP_PT_levels(_NeedsMap, Panel):
    bl_label = "Levels"
    bl_parent_id = "GFXMAP_PT_interior"

    def draw(self, context):
        st = settings(context)
        lay = self.layout
        row = lay.row()
        row.template_list("GFXMAP_UL_levels", "", st, "levels", st, "levels_index", rows=3)
        col = row.column(align=True)
        col.operator("gfx_map.level_add", text="", icon="ADD")
        col.operator("gfx_map.level_remove", text="", icon="REMOVE")
        if 0 <= st.levels_index < len(st.levels):
            lv = st.levels[st.levels_index]
            lay.prop(lv, "index")
        row = lay.row(align=True)
        row.operator("gfx_map.levels_detect", icon="SNAP_FACE")
        if hasattr(context.scene, "ytyps"):
            row.operator("gfx_map.levels_from_rooms", icon="HOME")


class GFXMAP_PT_convert(_NeedsMap, Panel):
    bl_label = "3D to Curves"
    bl_parent_id = "GFXMAP_PT_interior"

    def draw(self, context):
        st = settings(context)
        lay = self.layout
        lay.use_property_split = True
        lay.prop(st, "mode")
        col = lay.column(align=True)
        col.prop(st, "snap")
        col.prop(st, "cell")
        col.prop(st, "simplify")
        col.prop(st, "min_area")
        col = lay.column(align=True)
        col.prop(st, "close_gaps")
        col.prop(st, "remove_thin")
        if st.mode == "FLOOR":
            col = lay.column(align=True)
            col.prop(st, "floor_tolerance")
            col.prop(st, "max_slope")
        lay.prop(st, "floor_color")
        lay.prop(st, "walls")
        if st.walls:
            lay.prop(st, "wall_mode")
            col = lay.column(align=True)
            if st.wall_mode == "OBSTACLES":
                col.prop(st, "obstacle_min")
                col.prop(st, "obstacle_max")
            else:
                col.prop(st, "cut_height")
                col.prop(st, "wall_width")
            lay.prop(st, "wall_color")
        if hasattr(context.scene, "ytyps"):
            lay.prop(st, "clip_to_rooms")
        lay.prop(st, "replace")
        lay.operator("gfx_map.import_ybn", icon="MOD_PHYSICS")
        lay.operator("gfx_map.generate", icon="OUTLINER_OB_CURVE")


class GFXMAP_PT_style(_Base, Panel):
    bl_label = "Curve Style"
    bl_parent_id = "GFXMAP_PT_interior"

    @classmethod
    def poll(cls, context):
        o = context.active_object
        return U.map_root() is not None and o is not None and o.type in {"CURVE", "MESH"}

    def draw(self, context):
        g = context.active_object.gfx_map
        lay = self.layout
        lay.use_property_split = True
        lay.prop(g, "level")
        row = lay.row(align=True, heading="Order")
        for d, icon in (("BOTTOM", "TRIA_DOWN_BAR"), ("DOWN", "TRIA_DOWN"), ("UP", "TRIA_UP"), ("TOP", "TRIA_UP_BAR")):
            op = row.operator("gfx_map.layer_move", text="", icon=icon)
            op.direction, op.name = d, context.active_object.name
        row.prop(g, "order", text="")
        lay.prop(g, "preset")
        row = lay.row(heading="Fill")
        row.prop(g, "use_fill", text="")
        sub = row.row()
        sub.active = g.use_fill
        sub.prop(g, "fill_color", text="")
        row = lay.row(heading="Stroke")
        row.prop(g, "use_stroke", text="")
        sub = row.row(align=True)
        sub.active = g.use_stroke
        sub.prop(g, "stroke_color", text="")
        sub.prop(g, "stroke_width", text="")
        lay.operator("gfx_map.apply_preset", icon="BRUSHES_ALL")


class GFXMAP_PT_layers(_NeedsMap, Panel):
    bl_label = "Layers"
    bl_parent_id = "GFXMAP_PT_interior"

    def draw(self, context):
        st = settings(context)
        lay = self.layout
        level = layer_level(context)
        layers = level_layers(context, level)
        lay.label(text=f"{U.level_clip_name(level)}: {len(layers)} shape(s), top first", icon="RENDERLAYERS")

        if layers:
            row = lay.row()
            row.template_list("GFXMAP_UL_layers", "", bpy.data, "objects", st, "layers_active",
                              rows=max(4, min(len(layers), 8)))
            col = row.column(align=True)
            col.operator("gfx_map.layer_new", text="", icon="ADD")
            col.operator("gfx_map.layer_remove", text="", icon="REMOVE")
            col.separator()
            for d, icon in (("TOP", "TRIA_UP_BAR"), ("UP", "TRIA_UP"), ("DOWN", "TRIA_DOWN"),
                            ("BOTTOM", "TRIA_DOWN_BAR")):
                op = col.operator("gfx_map.layer_move", text="", icon=icon)
                op.direction, op.name = d, ""
            row = lay.row(align=True)
            row.operator("gfx_map.layer_assign", icon="IMPORT")
        else:
            box = lay.box()
            col = box.column(align=True)
            col.label(text=f"{U.level_clip_name(level)} has no shapes yet", icon="INFO")
            col.label(text="Assign selected curves, add a")
            col.label(text="New Shape or use 3D to Curves.")
            row = box.row(align=True)
            row.scale_y = 1.3
            row.operator("gfx_map.layer_assign", icon="IMPORT")
            row.operator("gfx_map.layer_new", icon="ADD")

        o = context.active_object
        if o is not None and o in layer_candidates(context) and o.gfx_map.level != level:
            row = lay.row(align=True)
            row.label(text=f"Active is on {U.level_clip_name(o.gfx_map.level)}", icon="ERROR")
            op = row.operator("gfx_map.level_select", text="Show")
            op.index = o.gfx_map.level
        loose = unassigned_shapes(context)
        if loose:
            lay.label(text=f"{len(loose)} loose curve(s) outside GFX Map", icon="UNLINKED")


class GFXMAP_PT_preview(_NeedsMap, Panel):
    bl_label = "Preview"
    bl_parent_id = "GFXMAP_PT_interior"

    def draw(self, context):
        from . import preview
        st = settings(context)
        lay = self.layout
        row = lay.row(align=True)
        row.scale_y = 1.4
        row.operator("gfx_map.preview", icon="IMAGE_DATA", text="Show Preview")
        row.prop(st, "preview_auto", text="", icon="FILE_REFRESH")
        row = lay.row(align=True)
        op = row.operator("gfx_map.preview_level", text="", icon="TRIA_LEFT")
        op.step = -1
        row.label(text=U.level_clip_name(preview.current_level(context)))
        op = row.operator("gfx_map.preview_level", text="", icon="TRIA_RIGHT")
        op.step = 1
        row.prop(st, "preview_follow", text="", icon="RESTRICT_SELECT_OFF")
        col = lay.column(align=True)
        col.use_property_split = True
        col.prop(st, "preview_size")
        col.prop(st, "preview_background")
        row = lay.row(align=True)
        row.prop(st, "preview_grid", toggle=True)
        row.prop(st, "preview_origin", toggle=True)
        row.prop(st, "preview_ghost", text="Ghost", toggle=True)
        info = preview.last_info
        if info:
            c = lay.column(align=True)
            c.label(text=f"{U.level_clip_name(info['level'])}: {info['size'][0]}x{info['size'][1]} px, "
                         f"{info['ppm']:.1f} px/m", icon="INFO")
            c.label(text=f"GFX {info['bytes']} bytes, {info['shapes']} shapes, levels "
                         + ", ".join(str(i) for i in info["levels"]))


class GFXMAP_PT_export(_NeedsMap, Panel):
    bl_label = "Export"
    bl_parent_id = "GFXMAP_PT_interior"

    def draw(self, context):
        st = settings(context)
        lay = self.layout
        lay.use_property_split = True
        lay.prop(st, "source")
        lay.prop(st, "scale")
        lay.prop(st, "curve_tolerance")
        lay.prop(st, "separate_shapes")
        lay.prop(st, "levels_visible")
        lay.prop(st, "output_dir")
        row = lay.row(align=True)
        row.scale_y = 1.4
        row.operator("gfx_map.export", icon="EXPORT")
        row.operator("gfx_map.import_gfx", icon="IMPORT")


class GFXMAP_PT_measure(_NeedsMap, Panel):
    bl_label = "GTA Measurements"
    bl_parent_id = "GFXMAP_PT_interior"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        st = settings(context)
        lay = self.layout
        k = int(st.scale)
        col = lay.column(align=True)
        col.label(text="Minimap: 1 px = 1 m (MLO-local, Y flipped)")
        col.label(text=f"Stored x{k}: interior clip scale 1/{k} = {1 / k:g} (exact)")
        col.label(text=f"Precision: 1 twip = {1000 / (20 * k):.2f} mm")
        levels = measure(context)
        if not levels:
            lay.label(text="No curves to measure", icon="INFO")
        for idx in sorted(levels):
            x0, y0, x1, y1, n = levels[idx]
            box = lay.box()
            c = box.column(align=True)
            c.label(text=f"{U.level_clip_name(idx)}  ({n} object(s))", icon="MESH_PLANE")
            c.label(text=f"X {x0:.3f} .. {x1:.3f}   Y {y0:.3f} .. {y1:.3f} m")
            c.label(text=f"Size {x1 - x0:.3f} x {y1 - y0:.3f} m")
            c.label(text=f"Flash px: x {x0:.2f}..{x1:.2f}  y {-y1:.2f}..{-y0:.2f}")
        m = U.origin_matrix(st)
        t = m.translation
        heading = U.origin_heading(st)
        box = lay.box()
        c = box.column(align=True)
        c.label(text="Placement used by the game", icon="ORIENTATION_GLOBAL")
        c.label(text=f"Interior pos ({t.x:.3f}, {t.y:.3f}, {t.z:.3f})  heading {heading:.2f}°")
        c.label(text=f"Clip at ({t.x:.2f}, {-t.y:.2f}) px, rotation {-heading:.2f}°")
        h = st.get_hash()
        if h is not None:
            signed = h - (1 << 32) if h >= 1 << 31 else h
            lvl = st.levels[st.levels_index].index if 0 <= st.levels_index < len(st.levels) else 0
            text = f"SetRadarAsInteriorThisFrame({signed}, {t.x:.3f}, {t.y:.3f}, {round(heading)}, {lvl})"
            op = box.operator("gfx_map.copy_native", icon="COPYDOWN")
            op.text = text


classes = (GFXMAP_UL_levels, GFXMAP_UL_layers, GFXMAP_PT_interior, GFXMAP_PT_levels, GFXMAP_PT_convert, GFXMAP_PT_style,
           GFXMAP_PT_layers, GFXMAP_PT_preview,
           GFXMAP_PT_export, GFXMAP_PT_measure)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
