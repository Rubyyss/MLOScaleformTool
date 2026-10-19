"""2D path helpers (pure Python): loops, nesting, simplification, Bezier conversion.

A path is a dict {"start": (x, y), "segs": [...], "closed": bool} where a segment
is ("L", x, y), ("Q", cx, cy, x, y) or ("C", c1x, c1y, c2x, c2y, x, y).
Units are metres in MLO-local space (x right, y forward/up on the map).
"""

import math


# --------------------------------------------------------------------------- basic polygon ops

def signed_area(pts):
    a = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        a += x0 * y1 - x1 * y0
    return a * 0.5


def point_in_polygon(x, y, pts):
    inside = False
    n = len(pts)
    j = n - 1
    for i in range(n):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y):
            xc = xi + (y - yi) * (xj - xi) / (yj - yi)
            if x < xc:
                inside = not inside
        j = i
    return inside


def _perp_dist(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy)
    if L == 0:
        return math.hypot(px - ax, py - ay)
    return abs(dx * (ay - py) - dy * (ax - px)) / L


def rdp(pts, tol):
    """Ramer-Douglas-Peucker for an open polyline (iterative)."""
    if len(pts) < 3 or tol <= 0:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i0, i1 = stack.pop()
        best, idx = -1.0, -1
        a, b = pts[i0], pts[i1]
        for i in range(i0 + 1, i1):
            d = _perp_dist(pts[i], a, b)
            if d > best:
                best, idx = d, i
        if best > tol:
            keep[idx] = True
            stack.append((i0, idx))
            stack.append((idx, i1))
    return [p for p, k in zip(pts, keep) if k]


def simplify_loop(pts, tol):
    """RDP on a closed loop, anchored at the two most distant points."""
    if len(pts) < 4 or tol <= 0:
        return list(pts)
    # anchor 0 = leftmost point, anchor 1 = farthest point from it
    i0 = min(range(len(pts)), key=lambda i: pts[i])
    pts = pts[i0:] + pts[:i0]
    x0, y0 = pts[0]
    i1 = max(range(len(pts)), key=lambda i: (pts[i][0] - x0) ** 2 + (pts[i][1] - y0) ** 2)
    a = rdp(pts[:i1 + 1], tol)
    b = rdp(pts[i1:] + [pts[0]], tol)
    out = a[:-1] + b[:-1]
    # drop collinear leftovers
    return out if len(out) >= 3 else list(pts)


def remove_collinear(pts, eps=1e-9):
    out = []
    n = len(pts)
    for i in range(n):
        p0 = pts[i - 1]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        cross = (p1[0] - p0[0]) * (p2[1] - p1[1]) - (p1[1] - p0[1]) * (p2[0] - p1[0])
        if abs(cross) > eps:
            out.append(p1)
    return out if len(out) >= 3 else pts


# --------------------------------------------------------------------------- Bezier helpers

def cubic_point(p0, p1, p2, p3, t):
    mt = 1 - t
    a, b, c, d = mt * mt * mt, 3 * mt * mt * t, 3 * mt * t * t, t * t * t
    return (a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
            a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1])


def _split_cubic(p0, p1, p2, p3, t=0.5):
    def lerp(a, b):
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    p01, p12, p23 = lerp(p0, p1), lerp(p1, p2), lerp(p2, p3)
    p012, p123 = lerp(p01, p12), lerp(p12, p23)
    m = lerp(p012, p123)
    return (p0, p01, p012, m), (m, p123, p23, p3)


def cubic_to_quads(p0, p1, p2, p3, tol, depth=0):
    """Approximate a cubic Bezier with quadratic segments [(c, end), ...]."""
    # Error of the single-quad midpoint approximation: sqrt(3)/36 * |p3 - 3p2 + 3p1 - p0|
    ex = p3[0] - 3 * p2[0] + 3 * p1[0] - p0[0]
    ey = p3[1] - 3 * p2[1] + 3 * p1[1] - p0[1]
    err = math.sqrt(3) / 36 * math.hypot(ex, ey)
    if err <= tol or depth >= 10:
        c = ((3 * (p1[0] + p2[0]) - p0[0] - p3[0]) / 4,
             (3 * (p1[1] + p2[1]) - p0[1] - p3[1]) / 4)
        return [(c, p3)]
    a, b = _split_cubic(p0, p1, p2, p3)
    return cubic_to_quads(*a, tol, depth + 1) + cubic_to_quads(*b, tol, depth + 1)


def quad_to_cubic(p0, c, p1):
    return ((p0[0] + 2 / 3 * (c[0] - p0[0]), p0[1] + 2 / 3 * (c[1] - p0[1])),
            (p1[0] + 2 / 3 * (c[0] - p1[0]), p1[1] + 2 / 3 * (c[1] - p1[1])))


def is_straight_cubic(p0, p1, p2, p3, eps=1e-6):
    return _perp_dist(p1, p0, p3) < eps and _perp_dist(p2, p0, p3) < eps


# --------------------------------------------------------------------------- paths

def path_from_points(pts, closed=True):
    return {"start": tuple(pts[0]), "segs": [("L", x, y) for x, y in pts[1:]], "closed": closed}


def flatten(path, steps=8):
    """Polyline approximation (used for area / nesting tests only)."""
    pts = [path["start"]]
    cur = path["start"]
    for s in path["segs"]:
        if s[0] == "L":
            cur = (s[1], s[2])
            pts.append(cur)
        elif s[0] == "Q":
            c, e = (s[1], s[2]), (s[3], s[4])
            for i in range(1, steps + 1):
                t = i / steps
                mt = 1 - t
                pts.append((mt * mt * cur[0] + 2 * mt * t * c[0] + t * t * e[0],
                            mt * mt * cur[1] + 2 * mt * t * c[1] + t * t * e[1]))
            cur = e
        else:
            c1, c2, e = (s[1], s[2]), (s[3], s[4]), (s[5], s[6])
            for i in range(1, steps + 1):
                pts.append(cubic_point(cur, c1, c2, e, i / steps))
            cur = e
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    return pts


def reverse_path(path):
    """Reverse travel direction (works for L/Q/C segments)."""
    nodes = [path["start"]]
    for s in path["segs"]:
        nodes.append((s[-2], s[-1]))
    segs = []
    for i in range(len(path["segs"]) - 1, -1, -1):
        s = path["segs"][i]
        prev = nodes[i]
        if s[0] == "L":
            segs.append(("L", prev[0], prev[1]))
        elif s[0] == "Q":
            segs.append(("Q", s[1], s[2], prev[0], prev[1]))
        else:
            segs.append(("C", s[3], s[4], s[1], s[2], prev[0], prev[1]))
    return {"start": nodes[-1], "segs": segs, "closed": path.get("closed", True)}


def to_quadratic(path, tol):
    """Replace cubic segments with quadratic approximations (SWF has no cubics)."""
    segs = []
    cur = path["start"]
    for s in path["segs"]:
        if s[0] == "C":
            c1, c2, e = (s[1], s[2]), (s[3], s[4]), (s[5], s[6])
            if is_straight_cubic(cur, c1, c2, e):
                segs.append(("L", e[0], e[1]))
            else:
                for c, end in cubic_to_quads(cur, c1, c2, e, tol):
                    segs.append(("Q", c[0], c[1], end[0], end[1]))
            cur = e
        else:
            segs.append(s)
            cur = (s[-2], s[-1])
    return {"start": path["start"], "segs": segs, "closed": path.get("closed", True)}


def close_path(path):
    """Make sure a closed path ends exactly on its start point."""
    if not path["segs"]:
        return path
    last = path["segs"][-1]
    if (last[-2], last[-1]) != tuple(path["start"]):
        path = dict(path)
        path["segs"] = path["segs"] + [("L", path["start"][0], path["start"][1])]
    return path


def orient_even_odd(paths):
    """Return closed paths oriented so the filled interior is on the LEFT (CCW, y-up).

    Fill follows the even-odd rule over all loops (like a Blender 2D curve):
    a loop nested inside an odd number of others is a hole.
    """
    flat = [flatten(p) for p in paths]
    areas = [signed_area(f) for f in flat]
    out = []
    for i, p in enumerate(paths):
        if len(flat[i]) < 3 or abs(areas[i]) < 1e-12:
            continue
        # sample a point that is surely on the loop, nudged inside it
        tx, ty = _interior_probe(flat[i], areas[i])
        depth = 0
        for j, f in enumerate(flat):
            if j != i and len(f) >= 3 and abs(areas[j]) > abs(areas[i]) * 1e-9 and point_in_polygon(tx, ty, f):
                depth += 1
        want_ccw = depth % 2 == 0
        is_ccw = areas[i] > 0
        out.append(p if want_ccw == is_ccw else reverse_path(p))
    return out


def split_islands(oriented):
    """Group paths from orient_even_odd into islands: [outer, holes directly inside it...].

    Outer loops are CCW. Each hole (CW) goes to the smallest outer loop that
    contains it; a loop inside a hole is a new island of its own.
    """
    flat = [flatten(p) for p in oriented]
    areas = [signed_area(f) for f in flat]
    outers = [i for i, a in enumerate(areas) if a > 0]
    groups = {i: [oriented[i]] for i in outers}
    order = list(outers)
    for i, a in enumerate(areas):
        if a > 0:
            continue
        # a point just inside the hole polygon, hence inside the loop that holds it
        x, y = _interior_probe(flat[i], a)
        best = None
        for j in outers:
            if abs(areas[j]) > abs(a) and point_in_polygon(x, y, flat[j]):
                if best is None or areas[j] < areas[best]:
                    best = j
        if best is None:  # orphan hole: keep it as its own group so nothing is lost
            groups[i] = [oriented[i]]
            order.append(i)
        else:
            groups[best].append(oriented[i])
    return [groups[i] for i in order]


def _interior_probe(pts, area):
    """A point just inside the loop next to its first edge."""
    (x0, y0), (x1, y1) = pts[0], pts[1]
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L  # left normal
    if area < 0:
        nx, ny = -nx, -ny
    eps = 1e-4 * max(L, 1e-3)
    return (x0 + x1) / 2 + nx * eps, (y0 + y1) / 2 + ny * eps


def bounds(paths):
    xs, ys = [], []
    for p in paths:
        xs.append(p["start"][0])
        ys.append(p["start"][1])
        for s in p["segs"]:
            xs.extend(s[1::2])
            ys.extend(s[2::2])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)
