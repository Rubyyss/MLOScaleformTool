"""3D -> 2D: rasterise projected geometry on a metric grid and trace outlines.

Everything works in MLO-local metres. grid[iy, ix] covers the square
[x0 + ix*cell, x0 + (ix+1)*cell) x [y0 + iy*cell, y0 + (iy+1)*cell).
"""

import math

import numpy as np

from .geom import rdp, remove_collinear, signed_area, simplify_loop


class Grid:
    def __init__(self, xmin, ymin, xmax, ymax, cell, margin=2):
        self.cell = float(cell)
        self.x0 = math.floor(xmin / cell) * cell - margin * cell
        self.y0 = math.floor(ymin / cell) * cell - margin * cell
        self.w = int(math.ceil((xmax - self.x0) / cell)) + margin + 1
        self.h = int(math.ceil((ymax - self.y0) / cell)) + margin + 1
        if self.w * self.h > 64_000_000:
            raise ValueError(f"grid {self.w}x{self.h} too large: raise the cell size")
        self.data = np.zeros((self.h, self.w), dtype=bool)

    def empty_like(self):
        g = Grid.__new__(Grid)
        g.cell, g.x0, g.y0, g.w, g.h = self.cell, self.x0, self.y0, self.w, self.h
        g.data = np.zeros_like(self.data)
        return g

    # ---------------------------------------------------------------- filling

    def fill_triangles(self, tris):
        """tris: (N, 3, 2) array. Cell centres inside a triangle are set."""
        if len(tris) == 0:
            return
        c = self.cell
        t = (np.asarray(tris, dtype=np.float64) - (self.x0, self.y0)) / c - 0.5  # centre-sample space
        mn = np.floor(t.min(axis=1)).astype(np.int64) + 1
        mx = np.floor(t.max(axis=1)).astype(np.int64)
        mn = np.maximum(mn, 0)
        mx[:, 0] = np.minimum(mx[:, 0], self.w - 1)
        mx[:, 1] = np.minimum(mx[:, 1], self.h - 1)
        ok = np.all(mx >= mn, axis=1)
        data = self.data
        for i in np.nonzero(ok)[0]:
            (ax, ay), (bx, by), (cx, cy) = t[i]
            area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
            if abs(area) < 1e-12:
                continue
            xs = np.arange(mn[i, 0], mx[i, 0] + 1, dtype=np.float64)
            ys = np.arange(mn[i, 1], mx[i, 1] + 1, dtype=np.float64)[:, None]
            s = 1.0 if area > 0 else -1.0
            e0 = s * ((bx - ax) * (ys - ay) - (by - ay) * (xs - ax))
            e1 = s * ((cx - bx) * (ys - by) - (cy - by) * (xs - bx))
            e2 = s * ((ax - cx) * (ys - cy) - (ay - cy) * (xs - cx))
            inside = (e0 >= 0) & (e1 >= 0) & (e2 >= 0)
            data[mn[i, 1]:mx[i, 1] + 1, mn[i, 0]:mx[i, 0] + 1] |= inside

    def fill_rects(self, rects):
        """rects: iterable of (xmin, ymin, xmax, ymax)."""
        c = self.cell
        for xmin, ymin, xmax, ymax in rects:
            i0 = max(0, int(math.ceil((xmin - self.x0) / c - 0.5)))
            i1 = min(self.w - 1, int(math.floor((xmax - self.x0) / c - 0.5)))
            j0 = max(0, int(math.ceil((ymin - self.y0) / c - 0.5)))
            j1 = min(self.h - 1, int(math.floor((ymax - self.y0) / c - 0.5)))
            if i1 >= i0 and j1 >= j0:
                self.data[j0:j1 + 1, i0:i1 + 1] = True

    def fill_nonzero(self, segs):
        """Scan-line non-zero winding fill of oriented closed outlines (M, 2, 2).

        Segments must keep the solid on their left (see section_segments), so
        overlapping solids merge and hollow parts stay empty. Rows whose
        winding does not return to zero (broken outlines) are skipped.
        """
        if len(segs) == 0:
            return
        s = (np.asarray(segs, dtype=np.float64) - (self.x0, self.y0)) / self.cell - 0.5
        y0, y1 = s[:, 0, 1], s[:, 1, 1]
        x0, x1 = s[:, 0, 0], s[:, 1, 0]
        lo, hi = np.minimum(y0, y1), np.maximum(y0, y1)
        r0 = np.maximum(np.ceil(lo).astype(np.int64), 0)
        r1 = np.minimum(np.ceil(hi).astype(np.int64) - 1, self.h - 1)  # rows with lo <= r < hi
        n = np.maximum(r1 - r0 + 1, 0)
        if n.sum() == 0:
            return
        idx = np.repeat(np.arange(len(s)), n)
        rows = np.concatenate([np.arange(a, a + k) for a, k in zip(r0, n) if k > 0]).astype(np.int64)
        t = (rows - y0[idx]) / (y1[idx] - y0[idx])
        xs = x0[idx] + t * (x1[idx] - x0[idx])
        wind = np.where(y1[idx] > y0[idx], -1, 1).astype(np.int32)  # downward edge = entering
        balance = np.bincount(rows, weights=wind, minlength=self.h)
        keep = balance[rows] == 0
        rows, xs, wind = rows[keep], xs[keep], wind[keep]
        if len(rows) == 0:
            return
        c = np.clip(np.ceil(xs).astype(np.int64), 0, self.w)
        diff = np.zeros((self.h, self.w + 1), dtype=np.int32)
        np.add.at(diff, (rows, c), wind)
        self.data |= np.cumsum(diff[:, :-1], axis=1) != 0

    def stroke_segments(self, segs, width, keep_solid=True):
        """Mark cells along segments and thicken them to `width` metres.

        With keep_solid, lines lying on an already filled area are not
        thickened, so solid (closed) walls keep their exact size and only
        single-plane walls get the minimum width.
        """
        if len(segs) == 0:
            return
        s = (np.asarray(segs, dtype=np.float64) - (self.x0, self.y0)) / self.cell
        L = np.hypot(*(s[:, 1] - s[:, 0]).T)
        n = np.maximum(np.ceil(L * 2).astype(np.int64), 1) + 1
        idx = np.repeat(np.arange(len(s)), n)
        t = np.concatenate([np.linspace(0, 1, k) for k in n])
        p = s[idx, 0] + (s[idx, 1] - s[idx, 0]) * t[:, None]
        ix = np.clip(np.floor(p[:, 0]).astype(np.int64), 0, self.w - 1)
        iy = np.clip(np.floor(p[:, 1]).astype(np.int64), 0, self.h - 1)
        line = np.zeros_like(self.data)
        line[iy, ix] = True
        if keep_solid:
            line &= ~dilate(self.data, 1)
        r = max(0, int(round(width / self.cell / 2)))
        self.data |= dilate(line, r)

    # ---------------------------------------------------------------- tracing

    def trace(self, simplify=0.0, min_area=0.0):
        """Outline loops in metres: outer CCW, holes CW (fill on the left)."""
        loops = trace_pixels(self.data)
        out = []
        c = self.cell
        for lp in loops:
            pts = [(self.x0 + i * c, self.y0 + j * c) for i, j in destair(lp)]
            pts = remove_collinear(pts)
            if simplify > 0:
                pts = simplify_loop(pts, simplify)
            if len(pts) < 3:
                continue
            a = signed_area(pts)
            if abs(a) < max(min_area, 1e-12):
                continue
            out.append(pts)
        return out


def dilate(mask, r):
    """Square structuring element: keeps axis-aligned corners exact under open/close."""
    if r <= 0:
        return mask.copy()
    out = mask.copy()
    h, w = mask.shape
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            ys0, ys1 = max(0, dy), min(h, h + dy)
            xs0, xs1 = max(0, dx), min(w, w + dx)
            out[ys0:ys1, xs0:xs1] |= mask[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out


def erode(mask, r):
    if r <= 0:
        return mask.copy()
    return ~dilate(~mask, r)


def close(mask, r):
    return erode(dilate(mask, r), r)


def open_(mask, r):
    return dilate(erode(mask, r), r)


def destair(loop):
    """Replace pixel staircases by edge midpoints, keeping real corners.

    loop: unit-edge vertices. A vertex between two straight runs of at least
    two unit edges is a real corner and is kept; elsewhere (stairs of a
    diagonal) the unit-edge midpoints are used, which follow the true edge.
    """
    n = len(loop)
    if n < 4:
        return loop
    dirs = [(loop[(i + 1) % n][0] - loop[i][0], loop[(i + 1) % n][1] - loop[i][1]) for i in range(n)]
    # run length of the straight run each unit edge belongs to
    run = [0] * n
    start = next((i for i in range(n) if dirs[i] != dirs[i - 1]), None)
    if start is None:
        return loop
    i = start
    while True:
        j = i
        while dirs[(j + 1) % n] == dirs[i] and (j + 1) % n != start:
            j += 1
        length = j - i + 1
        for k in range(i, j + 1):
            run[k % n] = length
        i = (j + 1) % n if j + 1 < start + n else start
        if i == start or j + 1 >= start + n:
            break
    out = []
    for i in range(n):
        prev = (i - 1) % n
        if dirs[prev] != dirs[i] and run[prev] >= 2 and run[i] >= 2:
            out.append(loop[i])
        x0, y0 = loop[i]
        x1, y1 = loop[(i + 1) % n]
        out.append(((x0 + x1) / 2, (y0 + y1) / 2))
    return out


def split_closed(segs, eps=1e-4):
    """Split section segments (M,2,2) into (closed-outline segs, open-chain segs)."""
    if len(segs) == 0:
        return segs, segs
    keys = np.round(np.asarray(segs).reshape(-1, 2) / eps).astype(np.int64)
    _, node = np.unique(keys, axis=0, return_inverse=True)
    node = node.reshape(-1, 2)
    deg = np.bincount(node.ravel(), minlength=node.max() + 1)
    # union-find over nodes
    parent = list(range(len(deg)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, b in node.tolist():
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    roots = np.array([find(a) for a in range(len(deg))])
    bad = np.zeros(len(deg), dtype=bool)
    odd_roots = np.unique(roots[deg % 2 == 1])
    bad[np.isin(roots, odd_roots)] = True
    seg_open = bad[node[:, 0]]
    segs = np.asarray(segs)
    return segs[~seg_open], segs[seg_open]


def trace_pixels(mask):
    """Boundary loops along pixel edges in integer vertex coordinates (x, y).

    Each loop keeps filled pixels on its left (y-up), so outer boundaries are
    CCW and holes CW. Diagonal-only contacts are kept apart (4-connectivity).
    """
    m = np.pad(mask, 1)
    h, w = m.shape
    # pixel (j, i) of m spans vertices (i-1 .. i, j-1 .. j) in original coords
    edges = []
    f = m[1:-1, 1:-1]
    # bottom side: neighbour below (j-1) empty -> edge (i, j) -> (i+1, j) [y-up: left side is +y]
    jj, ii = np.nonzero(f & ~m[:-2, 1:-1])
    edges.append(np.stack([ii, jj, ii + 1, jj], 1))
    # right side: neighbour right empty -> (i+1, j) -> (i+1, j+1)
    jj, ii = np.nonzero(f & ~m[1:-1, 2:])
    edges.append(np.stack([ii + 1, jj, ii + 1, jj + 1], 1))
    # top side: neighbour above empty -> (i+1, j+1) -> (i, j+1)
    jj, ii = np.nonzero(f & ~m[2:, 1:-1])
    edges.append(np.stack([ii + 1, jj + 1, ii, jj + 1], 1))
    # left side: neighbour left empty -> (i, j+1) -> (i, j)
    jj, ii = np.nonzero(f & ~m[1:-1, :-2])
    edges.append(np.stack([ii, jj + 1, ii, jj], 1))
    E = np.concatenate(edges).tolist()
    if not E:
        return []
    out_by_start = {}
    for k, (sx, sy, ex, ey) in enumerate(E):
        out_by_start.setdefault((sx, sy), []).append(k)
    used = bytearray(len(E))
    loops = []
    for k0 in range(len(E)):
        if used[k0]:
            continue
        loop = []
        k = k0
        while not used[k]:
            used[k] = 1
            sx, sy, ex, ey = E[k]
            loop.append((sx, sy))
            cands = [c for c in out_by_start[(ex, ey)] if not used[c]]
            if not cands:
                break
            if len(cands) == 1:
                k = cands[0]
            else:
                dx, dy = ex - sx, ey - sy
                # left turn keeps us hugging the filled pixel
                k = max(cands, key=lambda c: dx * (E[c][3] - E[c][1]) - dy * (E[c][2] - E[c][0]))
        if len(loop) >= 4:
            loops.append(loop)
    return loops


# --------------------------------------------------------------------------- mesh helpers

def triangle_normals_z(tris3):
    a, b, c = tris3[:, 0], tris3[:, 1], tris3[:, 2]
    n = np.cross(b - a, c - a)
    L = np.linalg.norm(n, axis=1)
    L[L == 0] = 1
    return n[:, 2] / L


def section_segments(tris3, z):
    """Intersection of triangles (N,3,3) with the plane Z = z -> (M, 2, 2).

    Each segment is oriented with the face normal on its right, so for a
    closed mesh with outward normals the solid lies on the segment's left.
    """
    if len(tris3) == 0:
        return np.zeros((0, 2, 2))
    d = tris3[:, :, 2] - z
    d = np.where(d == 0, 1e-9, d)
    pos = d > 0
    npos = pos.sum(axis=1)
    sel = (npos == 1) | (npos == 2)
    T, D, P = tris3[sel], d[sel], pos[sel]
    out = np.zeros((len(T), 2, 2))
    # the "lonely" vertex is the one whose sign differs from the other two
    lonely = np.where(P.sum(axis=1) == 1, np.argmax(P, axis=1), np.argmin(P, axis=1))
    r = np.arange(len(T))
    i0 = lonely
    i1 = (lonely + 1) % 3
    i2 = (lonely + 2) % 3
    for k, other in enumerate((i1, i2)):
        a, b = T[r, i0], T[r, other]
        da, db = D[r, i0], D[r, other]
        t = da / (da - db)
        out[:, k] = (a + (b - a) * t[:, None])[:, :2]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    d = out[:, 1] - out[:, 0]
    flip = (d[:, 0] * -n[:, 1] + d[:, 1] * n[:, 0]) < 0  # travel along (-ny, nx)
    out[flip] = out[flip][:, ::-1]
    return out
