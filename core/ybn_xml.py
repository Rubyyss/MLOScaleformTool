"""Read collision triangles from a CodeWalker / Sollumz .ybn.xml (MLO-local metres).

Vertex position = Vertices[i] + GeometryCenter, then CompositeTransform
(CodeWalker BoundGeometry.GetVertexPos). Box polygons give four corners
v1..v4 of a cuboid with c = mean, A = (v1+v2-v3-v4)/4, B = (v1-v2+v3-v4)/4,
C = (v1-v2-v3+v4)/4 (the same box CodeWalker draws for BoundPolygonBox).
Spheres, capsules and cylinders are approximated by their bounding boxes.
"""

import xml.etree.ElementTree as ET

import numpy as np

_BOX_FACES = [  # corners indexed by sign bits (sa, sb, sc) -> index sa*4 + sb*2 + sc, sign bit 1 = +
    (0, 1, 3, 2), (4, 6, 7, 5),   # -A, +A
    (0, 4, 5, 1), (2, 3, 7, 6),   # -B, +B
    (0, 2, 6, 4), (1, 5, 7, 3),   # -C, +C
]


def _vec(node, default=(0.0, 0.0, 0.0)):
    if node is None:
        return np.array(default, dtype=np.float64)
    return np.array([float(node.get(k, 0)) for k in "xyz"], dtype=np.float64)


def _matrix(node):
    if node is None or not (node.text or "").strip():
        return np.eye(4)
    vals = [float(v) for v in node.text.replace(",", " ").split()]
    if len(vals) != 16:
        return np.eye(4)
    # CodeWalker writes the matrix row by row with the translation in the last row
    return np.array(vals, dtype=np.float64).reshape(4, 4).T


def box_triangles(v1, v2, v3, v4):
    c = (v1 + v2 + v3 + v4) / 4
    A = (v1 + v2 - v3 - v4) / 4
    B = (v1 - v2 + v3 - v4) / 4
    C = (v1 - v2 - v3 + v4) / 4
    corners = [c + (1 if i & 4 else -1) * A + (1 if i & 2 else -1) * B + (1 if i & 1 else -1) * C
               for i in range(8)]
    tris = []
    for a, b, cc, d in _BOX_FACES:
        tris.append([corners[a], corners[b], corners[cc]])
        tris.append([corners[a], corners[cc], corners[d]])
    tris = np.array(tris)
    # make every face point away from the centre (A/B/C may form a left-handed basis)
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    out = (tris.mean(axis=1) - c)
    flip = (n * out).sum(axis=1) < 0
    tris[flip] = tris[flip][:, ::-1]
    return tris


def _aabb_triangles(lo, hi):
    c = (lo + hi) / 2
    h = (hi - lo) / 2
    return box_triangles(c + h * [1, 1, 1], c + h * [1, -1, -1], c + h * [-1, 1, -1], c + h * [-1, -1, 1])


def _geometry_triangles(item, parent_matrix):
    center = _vec(item.find("GeometryCenter"))
    m = parent_matrix @ _matrix(item.find("CompositeTransform"))
    vnode = item.find("Vertices")
    if vnode is None or not (vnode.text or "").strip():
        return []
    raw = [float(v) for v in vnode.text.replace(",", " ").split()]
    V = np.array(raw, dtype=np.float64).reshape(-1, 3) + center
    V = V @ m[:3, :3].T + m[:3, 3]
    out = []
    polys = item.find("Polygons")
    if polys is None:
        return out
    for p in polys:
        tag = p.tag
        if tag == "Triangle":
            out.append(V[[int(p.get("v1")), int(p.get("v2")), int(p.get("v3"))]][None])
        elif tag == "Box":
            out.append(box_triangles(*(V[int(p.get(k))] for k in ("v1", "v2", "v3", "v4"))))
        elif tag in ("Sphere", "Capsule", "Cylinder"):
            r = float(p.get("radius", 0))
            pts = [V[int(p.get(k))] for k in ("v", "v1", "v2") if p.get(k) is not None]
            if pts:
                P = np.array(pts)
                out.append(_aabb_triangles(P.min(axis=0) - r, P.max(axis=0) + r))
    return out


def _walk(bounds, matrix, out):
    kind = bounds.get("type", "")
    if kind in ("Geometry", "GeometryBVH"):
        out += _geometry_triangles(bounds, matrix)
    elif kind == "Composite":
        children = bounds.find("Children")
        for child in (children if children is not None else []):
            m = matrix @ _matrix(child.find("CompositeTransform"))
            if child.get("type") in ("Geometry", "GeometryBVH"):
                out += _geometry_triangles(child, matrix)
            else:
                _walk(child, m, out)
    elif kind == "Box":
        c = _vec(bounds.find("BoxCenter"))
        lo, hi = _vec(bounds.find("BoxMin")), _vec(bounds.find("BoxMax"))
        t = _aabb_triangles(lo, hi)
        out.append(t @ matrix[:3, :3].T + matrix[:3, 3])
        del c


def read_ybn_xml(path_or_text):
    """Return (N, 3, 3) triangles in the bound's local space."""
    if "<" in path_or_text[:200]:
        root = ET.fromstring(path_or_text)
    else:
        root = ET.parse(path_or_text).getroot()
    bounds = root.find("Bounds") if root.tag != "Bounds" else root
    out = []
    _walk(bounds, np.eye(4), out)
    return np.concatenate(out) if out else np.zeros((0, 3, 3))
