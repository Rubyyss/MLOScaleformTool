import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty, FloatProperty, FloatVectorProperty,
                       IntProperty, PointerProperty, StringProperty)

from .bl_utils import PRESETS
from .core.joaat import parse_hash

PRESET_ITEMS = [(k, v[0], "") for k, v in PRESETS.items()] + [("CUSTOM", "Custom", "")]


def _style_changed(self, context):
    from .ops import assign_style_material
    obj = self.id_data
    if isinstance(obj, bpy.types.Object) and obj.type in {"CURVE", "MESH"}:
        assign_style_material(obj)


def _preview_changed(self, context):
    from . import preview
    if bpy.data.images.get(preview.IMAGE_NAME):
        preview.update(context)


_NO_INDEX = -(1 << 30)


def _level_index_changed(self, context):
    """Renaming a level moves its shapes and renames its collection."""
    from . import bl_utils as U
    old, new = self.prev_index, self.index
    self.prev_index = new
    if old == _NO_INDEX or old == new:
        return
    root = U.map_root()
    if root is None:
        return
    col = bpy.data.collections.get(U.level_collection_name(old))
    if col is not None and bpy.data.collections.get(U.level_collection_name(new)) is None:
        col.name = U.level_collection_name(new)
    for o in list(root.all_objects):
        if o.gfx_map.level == old:
            o.gfx_map.level = new  # moves it (see _object_level_changed)


def _object_level_changed(self, context):
    from . import bl_utils as U
    obj = self.id_data
    if isinstance(obj, bpy.types.Object) and U.in_map(obj):
        U.move_to_level(obj, context.scene, self.level)


def _levels_index_changed(self, context):
    _preview_changed(self, context)


def _get_layer_active(self):
    o = bpy.context.view_layer.objects.active if bpy.context.view_layer else None
    return bpy.data.objects.find(o.name) if o is not None else -1


def _set_layer_active(self, value):
    if not 0 <= value < len(bpy.data.objects):
        return
    obj = bpy.data.objects[value]
    vl = bpy.context.view_layer
    if obj.name not in vl.objects:
        return
    for o in bpy.context.selected_objects:
        o.select_set(False)
    if obj.hide_get():
        obj.hide_set(False)
    obj.select_set(True)
    vl.objects.active = obj


def _apply_preset(self, context):
    if self.preset in PRESETS:
        self.fill_color = PRESETS[self.preset][1]


class GFXMAP_LevelItem(bpy.types.PropertyGroup):
    index: IntProperty(name="Level", update=_level_index_changed,
                       description="Floor index: level_<n> clip (negative = level_u<n>). "
                                   "The game shows room floor_id + interior floor id")
    prev_index: IntProperty(default=_NO_INDEX, options={"HIDDEN"})
    floor_z: FloatProperty(name="Floor Z", unit="LENGTH", description="Height of this floor in MLO-local space")
    height: FloatProperty(name="Height", default=3.0, min=0.2, unit="LENGTH",
                          description="Distance to the floor above (Footprint mode band)")
    enabled: BoolProperty(name="Generate", default=True)


class GFXMAP_ObjectSettings(bpy.types.PropertyGroup):
    level: IntProperty(name="Level", update=_object_level_changed,
                       description="level_<n> clip this curve is drawn in (moves it to that level's collection)")
    enabled: BoolProperty(name="Export", default=True, update=_preview_changed,
                          description="Include this shape in the GFX")
    order: IntProperty(name="Order", description="Draw order inside the level (higher = on top)")
    preset: EnumProperty(name="Preset", items=PRESET_ITEMS, default="ACCESSIBLE", update=_apply_preset)
    use_fill: BoolProperty(name="Fill", default=True, update=_style_changed)
    fill_color: FloatVectorProperty(name="Fill", subtype="COLOR", size=4, min=0, max=1,
                                    default=PRESETS["ACCESSIBLE"][1], update=_style_changed)
    use_stroke: BoolProperty(name="Stroke", default=False)
    stroke_color: FloatVectorProperty(name="Stroke", subtype="COLOR", size=4, min=0, max=1,
                                      default=PRESETS["LIMITS"][1])
    stroke_width: FloatProperty(name="Width", default=0.1, min=0.0, unit="LENGTH",
                                description="Line width in metres")
    generated: StringProperty(description="Set by Generate (floor/walls); regenerated curves replace these")


class GFXMAP_SceneSettings(bpy.types.PropertyGroup):
    # interior
    interior_name: StringProperty(
        name="MLO Name",
        description="Interior archetype name (or a hash: 123456, 0x..., int123456). "
                    "The file is int<joaat(name)>.gfx")
    origin: PointerProperty(
        name="MLO Origin", type=bpy.types.Object,
        description="Object at the interior's origin (its position/rotation = the MLO entity). "
                    "Empty = Blender world origin is the MLO origin")
    scale: EnumProperty(
        name="Precision", default="32",
        items=[(str(v), f"x{v}", f"Shapes stored at {v} px per metre (1 twip = {100 / (20 * v):.2f} cm); "
                                    f"the interior clip is scaled 1/{v}") for v in (1, 2, 4, 8, 16, 32)],
        description="Stored resolution. Powers of two keep the 1/scale matrix exact")
    curve_tolerance: FloatProperty(name="Curve Tolerance", default=0.005, min=0.0001, unit="LENGTH",
                                   description="Max error when Bezier curves become Flash quadratic curves")
    levels_visible: BoolProperty(name="Levels Visible", default=False,
                                 description="Export level clips with alpha 100 (handy to preview in JPEXS). "
                                             "The game sets the alpha itself")
    separate_shapes: BoolProperty(name="Separate Shapes", default=True,
                                  description="Write every island of a curve (outer outline + its holes) as its own "
                                              "shape, like Flash does. Off: one shape per curve object")
    output_dir: StringProperty(name="Output", subtype="DIR_PATH", default="//")
    source: EnumProperty(name="Export", default="COLLECTION", items=[
        ("COLLECTION", "GFX Map Collection", "Every curve inside the 'GFX Map' collection"),
        ("SELECTED", "Selected", "Selected curves / flat meshes")])

    # levels
    levels: CollectionProperty(type=GFXMAP_LevelItem)
    levels_index: IntProperty(update=_levels_index_changed)
    layers_active: IntProperty(get=_get_layer_active, set=_set_layer_active)

    # 3D -> curves
    mode: EnumProperty(name="Mode", default="FLOOR", items=[
        ("FLOOR", "Floor", "Up-facing faces near each floor height (walkable area)"),
        ("FOOTPRINT", "Footprint", "Everything between the floor and the floor above, seen from the top")])
    cell: FloatProperty(name="Resolution", default=0.05, min=0.005, max=2.0, unit="LENGTH",
                        description="Raster cell size: decides which areas are filled. With Snap on the "
                                    "outline is exact anyway; without it, accurate to about a cell")
    simplify: FloatProperty(name="Simplify", default=0.005, min=0.0, unit="LENGTH",
                            description="Allowed deviation from the real outline. With Snap on, the outline "
                                        "is the exact mesh edge; raise this to drop small details")
    snap: BoolProperty(name="Snap to Geometry", default=True,
                       description="Move outline vertices onto the real mesh corners and edges "
                                   "(exact shapes instead of raster-accurate ones)")
    min_area: FloatProperty(name="Min Area", default=0.25, min=0.0, description="Drop islands/holes smaller than this (m²)")
    close_gaps: FloatProperty(name="Close Gaps", default=0.10, min=0.0, unit="LENGTH",
                              description="Fill cracks narrower than this between floor pieces")
    remove_thin: FloatProperty(name="Remove Thin", default=0.20, min=0.0, unit="LENGTH",
                               description="Remove slivers thinner than this (wall tops, skirting)")
    floor_tolerance: FloatProperty(name="Floor Tolerance", default=0.6, min=0.0, unit="LENGTH",
                                   description="Floor mode: faces within ± this of the floor height")
    max_slope: FloatProperty(name="Max Slope", default=40.0, min=0.0, max=89.0,
                             description="Floor mode: steepest face counted as floor (degrees)")
    walls: BoolProperty(name="Obstacles Layer", default=True,
                        description="Also draw a darker layer over the floor (Rockstar draws furniture, "
                                    "counters and fixtures this way)")
    wall_mode: EnumProperty(name="Layer", default="OBSTACLES", items=[
        ("OBSTACLES", "Obstacles", "Footprint of everything between Min and Max above the floor, inside the "
                                   "floor (Rockstar style)"),
        ("SECTION", "Wall Cut", "Horizontal cut through the walls at Cut Height")])
    obstacle_min: FloatProperty(name="Min Height", default=0.25, min=0.0, unit="LENGTH",
                                description="Obstacles start this high above the floor (lower = steps, rugs)")
    obstacle_max: FloatProperty(name="Max Height", default=2.0, min=0.1, unit="LENGTH",
                                description="Obstacles end this high above the floor (higher = lamps, shelves)")
    cut_height: FloatProperty(name="Cut Height", default=1.2, min=0.05, unit="LENGTH")
    wall_width: FloatProperty(name="Thin Wall Width", default=0.15, min=0.0, unit="LENGTH",
                              description="Drawn width of single-plane walls")
    clip_to_rooms: BoolProperty(name="Clip to MLO Rooms", default=False,
                                description="Keep only what lies inside the Sollumz rooms of each floor_id")
    replace: BoolProperty(name="Replace Previous", default=True,
                          description="Delete curves generated before for the same levels")
    floor_color: FloatVectorProperty(name="Floor", subtype="COLOR", size=4, min=0, max=1,
                                     default=PRESETS["ACCESSIBLE"][1])
    wall_color: FloatVectorProperty(name="Obstacles", subtype="COLOR", size=4, min=0, max=1,
                                    default=PRESETS["ENTITIES"][1])

    # preview
    preview_size: IntProperty(name="Size", default=768, min=128, max=4096, update=_preview_changed,
                              description="Longest side of the preview image in pixels")
    preview_background: FloatVectorProperty(name="Background", subtype="COLOR_GAMMA", size=3, min=0, max=1,
                                            default=(56 / 255, 74 / 255, 80 / 255),
                                            description="Minimap background (retail minimap colour by default)",
                                            update=_preview_changed)
    preview_grid: BoolProperty(name="Metre Grid", default=True, update=_preview_changed,
                               description="Thin line every metre, stronger every 5 m")
    preview_origin: BoolProperty(name="MLO Origin", default=True, update=_preview_changed,
                                 description="Yellow cross where the game anchors the interior (entity position)")
    preview_ghost: BoolProperty(name="Ghost Level Below", default=True, update=_preview_changed)
    preview_auto: BoolProperty(name="Auto Refresh", default=True,
                               description="Re-render the preview when the curves change")
    preview_follow: BoolProperty(name="Follow Selected Level", default=True, update=_preview_changed,
                                 description="Preview the level selected in the Levels list")
    preview_level: IntProperty(name="Level", update=_preview_changed)

    def get_hash(self):
        return parse_hash(self.interior_name) if self.interior_name.strip() else None


classes = (GFXMAP_LevelItem, GFXMAP_ObjectSettings, GFXMAP_SceneSettings)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.gfx_map = PointerProperty(type=GFXMAP_SceneSettings)
    bpy.types.Object.gfx_map = PointerProperty(type=GFXMAP_ObjectSettings)


def unregister():
    del bpy.types.Object.gfx_map
    del bpy.types.Scene.gfx_map
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
