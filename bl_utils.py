"""Blender-side helpers: mesh triangles, curve <-> path conversion, Sollumz MLO data."""

import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

from .core.geom import is_straight_cubic, quad_to_cubic

COLLECTION_NAME = "GFX Map"

PRESETS = {
    # name: (label, rgba 0-1). Floor / obstacles / door are Rockstar's retail values
    # (int3661284625.gfx: 150, 112, 245); Limits is the dark grey of MLOScaleformTools.
    "ACCESSIBLE": ("Floor", (150 / 255, 150 / 255, 150 / 255, 1.0)),
    "ENTITIES": ("Obstacles / Entities", (112 / 255, 112 / 255, 112 / 255, 1.0)),
    "NEXT_AREA": ("Door / Next Area", (245 / 255, 245 / 255, 245 / 255, 1.0)),
    "LIMITS": ("Limits", (63 / 255, 63 / 255, 63 / 255, 1.0)),
}


# --------------------------------------------------------------------------- space

def origin_matrix(settings) -> Matrix:
    """World matrix of the MLO origin (identity when no origin object is set)."""
    if settings.origin is not None:
        return settings.origin.matrix_world.normalized()
    return Matrix.Identity(4)


def origin_heading(settings) -> float:
    if settings.origin is None:
        return 0.0
    return math.degrees(settings.origin.matrix_world.to_euler("XYZ").z)


# --------------------------------------------------------------------------- meshes

def object_triangles(obj, depsgraph, to_local: Matrix):
    """Evaluated triangles of any geometry object, in MLO-local space -> (N, 3, 3)."""
    ev = obj.evaluated_get(depsgraph)
    try:
        mesh = ev.to_mesh()
    except RuntimeError:
        return np.zeros((0, 3, 3))
    if mesh is None:
        return np.zeros((0, 3, 3))
    try:
        mesh.calc_loop_triangles()
        nv = len(mesh.vertices)
        nt = len(mesh.loop_triangles)
        if nv == 0 or nt == 0:
            return np.zeros((0, 3, 3))
        co = np.empty(nv * 3, dtype=np.float64)
        mesh.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        idx = np.empty(nt * 3, dtype=np.int64)
        mesh.loop_triangles.foreach_get("vertices", idx)
        m = np.array(to_local @ ev.matrix_world, dtype=np.float64)
        co = co @ m[:3, :3].T + m[:3, 3]
        tris = co[idx.reshape(-1, 3)]
        if np.linalg.det(m[:3, :3]) < 0:
            tris = tris[:, ::-1]  # mirrored object: keep normals outward
        return tris
    finally:
        ev.to_mesh_clear()


# --------------------------------------------------------------------------- curves -> paths

def _spline_paths(spline, m):
    def p2(v):
        w = m @ Vector((v[0], v[1], v[2]))
        return (w.x, w.y)

    closed = spline.use_cyclic_u
    if spline.type == "BEZIER":
        bp = spline.bezier_points
        if len(bp) < 2:
            return None
        pts = [(p2(b.co), p2(b.handle_left), p2(b.handle_right)) for b in bp]
        segs = []
        pairs = list(zip(pts[:-1], pts[1:]))
        if closed:
            pairs.append((pts[-1], pts[0]))
        for (co0, _, hr0), (co1, hl1, _) in pairs:
            if is_straight_cubic(co0, hr0, hl1, co1, 1e-6):
                segs.append(("L", co1[0], co1[1]))
            else:
                segs.append(("C", hr0[0], hr0[1], hl1[0], hl1[1], co1[0], co1[1]))
        return {"start": pts[0][0], "segs": segs, "closed": closed}
    pts = [p2(p.co) for p in spline.points]
    if len(pts) < 2:
        return None
    return {"start": pts[0], "segs": [("L", x, y) for x, y in pts[1:]], "closed": closed}


def curve_paths(obj, to_local: Matrix):
    m = to_local @ obj.matrix_world
    out = []
    for sp in obj.data.splines:
        p = _spline_paths(sp, m)
        if p:
            out.append(p)
    return out


def mesh_paths(obj, depsgraph, to_local: Matrix):
    """Flat mesh drawn by hand -> boundary loops of its faces (each face as a loop)."""
    ev = obj.evaluated_get(depsgraph)
    mesh = ev.to_mesh()
    try:
        m = to_local @ ev.matrix_world
        out = []
        for poly in mesh.polygons:
            pts = [(m @ mesh.vertices[i].co) for i in poly.vertices]
            pts = [(v.x, v.y) for v in pts]
            out.append({"start": pts[0], "segs": [("L", x, y) for x, y in pts[1:]], "closed": True})
        return out
    finally:
        ev.to_mesh_clear()


# --------------------------------------------------------------------------- paths -> curves

def material_for(rgba):
    r, g, b, a = rgba
    name = "GFX %02X%02X%02X%02X" % tuple(int(round(c * 255)) for c in (r, g, b, a))
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = (r, g, b, a)
    return mat


def new_curve_object(name, paths, collection, matrix_world, poly=True):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    for p in paths:
        has_curves = any(s[0] != "L" for s in p["segs"])
        if poly and not has_curves:
            pts = [p["start"]] + [(s[1], s[2]) for s in p["segs"]]
            if p.get("closed", True) and len(pts) > 1 and _same(pts[0], pts[-1]):
                pts.pop()
            sp = cu.splines.new("POLY")
            sp.points.add(len(pts) - 1)
            for pt, (x, y) in zip(sp.points, pts):
                pt.co = (x, y, 0.0, 1.0)
        else:
            _bezier_spline(cu, p)
            continue
        sp.use_cyclic_u = p.get("closed", True)
    obj = bpy.data.objects.new(name, cu)
    collection.objects.link(obj)
    obj.matrix_world = matrix_world
    return obj


def _same(a, b, eps=1e-7):
    return abs(a[0] - b[0]) < eps and abs(a[1] - b[1]) < eps


def _bezier_spline(cu, p):
    # nodes with (co, handle_left, handle_right)
    nodes = [[p["start"], None, None]]
    cur = p["start"]
    for s in p["segs"]:
        if s[0] == "L":
            end = (s[1], s[2])
            h0 = (cur[0] + (end[0] - cur[0]) / 3, cur[1] + (end[1] - cur[1]) / 3)
            h1 = (cur[0] + 2 * (end[0] - cur[0]) / 3, cur[1] + 2 * (end[1] - cur[1]) / 3)
        elif s[0] == "Q":
            end = (s[3], s[4])
            h0, h1 = quad_to_cubic(cur, (s[1], s[2]), end)
        else:
            end = (s[5], s[6])
            h0, h1 = (s[1], s[2]), (s[3], s[4])
        nodes[-1][2] = h0
        nodes.append([end, h1, None])
        cur = end
    closed = p.get("closed", True)
    if closed and len(nodes) > 1 and _same(nodes[0][0], nodes[-1][0]):
        last = nodes.pop()
        nodes[0][1] = last[1]
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(nodes) - 1)
    for bp, (co, hl, hr) in zip(sp.bezier_points, nodes):
        bp.handle_left_type = bp.handle_right_type = "FREE"
        bp.co = (co[0], co[1], 0.0)
        bp.handle_left = (hl or co)[0], (hl or co)[1], 0.0
        bp.handle_right = (hr or co)[0], (hr or co)[1], 0.0
    sp.use_cyclic_u = closed


def get_collection(scene, name=COLLECTION_NAME, parent=None):
    parent = parent or scene.collection
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
    if col.name not in {c.name for c in parent.children}:
        try:
            parent.children.link(col)
        except RuntimeError:
            pass
    return col


def level_clip_name(index):
    return f"level_{index}" if index >= 0 else f"level_u{-index}"


def level_collection_name(index):
    return f"GFX {level_clip_name(index)}"


def map_root():
    """The 'GFX Map' collection, or None before the minimap is set up."""
    return bpy.data.collections.get(COLLECTION_NAME)


def level_collection(scene, index):
    return get_collection(scene, level_collection_name(index), get_collection(scene))


def in_map(obj):
    root = map_root()
    return root is not None and obj.name in root.all_objects


def move_to_level(obj, scene, index):
    """Put obj only in the level's sub-collection (it leaves every other collection)."""
    target = level_collection(scene, index)
    for c in list(obj.users_collection):
        if c != target:
            c.objects.unlink(obj)
    if obj.name not in target.objects:
        target.objects.link(obj)


def remove_from_map(obj, scene):
    """Take obj out of the minimap without deleting it."""
    root = map_root()
    if root is None:
        return
    tree = {root} | set(root.children_recursive)
    for c in list(obj.users_collection):
        if c in tree:
            c.objects.unlink(obj)
    if not obj.users_collection:
        scene.collection.objects.link(obj)


# --------------------------------------------------------------------------- Sollumz

def sollumz_mlo_archetype(context):
    """Selected MLO archetype in Sollumz' YTYP panel, or None."""
    scene = context.scene
    ytyps = getattr(scene, "ytyps", None)
    if not ytyps or not (0 <= scene.ytyp_index < len(ytyps)):
        return None
    ytyp = ytyps[scene.ytyp_index]
    arch = getattr(ytyp, "selected_archetype", None)
    if arch is None:
        return None
    if str(getattr(arch, "type", "")) not in ("sollumz_archetype_mlo", "ArchetypeType.MLO"):
        return None
    return arch


def mlo_rooms_by_floor(arch):
    """{floor_id: [(xmin, ymin, xmax, ymax, zmin, zmax), ...]} without the limbo room."""
    out = {}
    for room in arch.rooms:
        if room.name.lower() == "limbo":
            continue
        mn, mx = room.bb_min, room.bb_max
        if (mx[0] - mn[0]) <= 0 or (mx[1] - mn[1]) <= 0:
            continue
        out.setdefault(int(room.floor_id), []).append((mn[0], mn[1], mx[0], mx[1], mn[2], mx[2]))
    return out
