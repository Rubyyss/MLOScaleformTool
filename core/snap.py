"""Snap raster-traced outlines onto the real geometry.

The raster pass gives the right topology (which areas are filled, holes,
merged pieces) but its vertices sit up to a cell away from the true edges,
so corners get chamfered and straight walls come out slightly skewed.
Here every outline vertex is moved onto the source geometry: onto the nearest
real vertex (corner) when one is close, otherwise onto the nearest real edge.
Points that land on the same straight edge become collinear and are dropped,
so the result is the exact mesh outline wherever the raster found it.
"""

import math

import numpy as np

from .geom import rdp, signed_area

EPS = 1e-6


def _key(p, q):
    return (int(round(p[0] / q)), int(round(p[1] / q)))


def boundary_edges(tris_xy, quant=1e-4):
    """Edges used by exactly one triangle (the outline of a triangle set), as (M, 2, 2)."""
    if len(tris_xy) == 0:
        return np.zeros((0, 2, 2))
    t = np.asarray(tris_xy, dtype=np.float64)
    e = np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]])
    k = np.round(e / quant).astype(np.int64)
    a = k[:, 0]
    b = k[:, 1]
    swap = (a[:, 0] > b[:, 0]) | ((a[:, 0] == b[:, 0]) & (a[:, 1] > b[:, 1]))
    lo = np.where(swap[:, None], b, a)
    hi = np.where(swap[:, None], a, b)
    keys = np.concatenate([lo, hi], axis=1)
    degenerate = (keys[:, 0] == keys[:, 2]) & (keys[:, 1] == keys[:, 3])
    _, inv, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    once = (counts[inv.ravel()] == 1) & ~degenerate
    return e[once]


class Snapper:
    """Nearest real vertex / edge lookup with a uniform hash grid."""

    def __init__(self, segments, radius):
        segs = np.asarray(segments, dtype=np.float64).reshape(-1, 2, 2)
        if len(segs):
            L = np.hypot(*(segs[:, 1] - segs[:, 0]).T)
            segs = segs[L > EPS]
        self.r = float(radius)
        self.segs = segs
        pts = segs.reshape(-1, 2) if len(segs) else np.zeros((0, 2))
        if len(pts):
            q = np.round(pts / 1e-5).astype(np.int64)
            _, idx = np.unique(q, axis=0, return_index=True)
            pts = pts[np.sort(idx)]
        self.pts = pts
        h = self.r
        self.pgrid = {}
        for i, (x, y) in enumerate(pts):
            self.pgrid.setdefault((math.floor(x / h), math.floor(y / h)), []).append(i)
        self.sgrid = {}
        for i, ((x0, y0), (x1, y1)) in enumerate(segs):
            for gx in range(math.floor(min(x0, x1) / h) - 1, math.floor(max(x0, x1) / h) + 2):
                for gy in range(math.floor(min(y0, y1) / h) - 1, math.floor(max(y0, y1) / h) + 2):
                    self.sgrid.setdefault((gx, gy), []).append(i)

    def _near(self, grid, x, y):
        h = self.r
        gx, gy = math.floor(x / h), math.floor(y / h)
        out = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                out.extend(grid.get((gx + dx, gy + dy), ()))
        return out

    def vertex(self, x, y):
        idx = self._near(self.pgrid, x, y)
        if not idx:
            return None
        P = self.pts[idx]
        d = np.hypot(P[:, 0] - x, P[:, 1] - y)
        i = int(np.argmin(d))
        return (float(P[i, 0]), float(P[i, 1])) if d[i] <= self.r else None

    def along(self, a, b, band):
        """Real vertices within `band` of segment a-b (strictly between its ends), ordered from a."""
        (ax, ay), (bx, by) = a, b
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        if L2 <= EPS * EPS:
            return []
        h = self.r
        idx = set()
        for gx in range(math.floor(min(ax, bx) / h) - 1, math.floor(max(ax, bx) / h) + 2):
            for gy in range(math.floor(min(ay, by) / h) - 1, math.floor(max(ay, by) / h) + 2):
                idx.update(self.pgrid.get((gx, gy), ()))
        if not idx:
            return []
        P = self.pts[sorted(idx)]
        t = ((P[:, 0] - ax) * dx + (P[:, 1] - ay) * dy) / L2
        d = np.abs((P[:, 0] - ax) * dy - (P[:, 1] - ay) * dx) / math.sqrt(L2)
        tol = 1e-4 / math.sqrt(L2)
        m = (t > tol) & (t < 1 - tol) & (d <= band)
        order = np.argsort(t[m])
        return [(float(x), float(y)) for x, y in P[m][order]]

    def edge(self, x, y):
        idx = sorted(set(self._near(self.sgrid, x, y)))
        if not idx:
            return None
        S = self.segs[idx]
        A, B = S[:, 0], S[:, 1]
        AB = B - A
        t = np.clip(((x - A[:, 0]) * AB[:, 0] + (y - A[:, 1]) * AB[:, 1]) / (AB ** 2).sum(axis=1), 0, 1)
        Q = A + AB * t[:, None]
        d = np.hypot(Q[:, 0] - x, Q[:, 1] - y)
        i = int(np.argmin(d))
        if d[i] > self.r:
            return None
        return (float(Q[i, 0]), float(Q[i, 1])), idx[i]


def snap_loop(loop, snapper: Snapper, corner_radius):
    """Move each vertex onto real corners/edges; returns the cleaned loop (or the original)."""
    out = []
    for x, y in loop:
        v = snapper.vertex(x, y) if corner_radius > 0 else None
        if v is not None and math.hypot(v[0] - x, v[1] - y) <= corner_radius:
            out.append(v)
            continue
        e = snapper.edge(x, y)
        out.append(e[0] if e is not None else (x, y))
    # drop repeats (several raster points around one corner)
    clean = []
    for p in out:
        if not clean or math.hypot(p[0] - clean[-1][0], p[1] - clean[-1][1]) > EPS * 10:
            clean.append(p)
    while len(clean) > 1 and math.hypot(clean[0][0] - clean[-1][0], clean[0][1] - clean[-1][1]) <= EPS * 10:
        clean.pop()
    if len(clean) < 3:
        return list(loop)
    # put back the real vertices the raster skipped between two snapped points (arcs, small steps)
    filled = []
    n = len(clean)
    for i in range(n):
        a, b = clean[i], clean[(i + 1) % n]
        filled.append(a)
        filled.extend(snapper.along(a, b, corner_radius))
    clean = filled
    a0, a1 = signed_area(loop), signed_area(clean)
    if a1 == 0 or (a0 > 0) != (a1 > 0) or abs(a1 - a0) > abs(a0) * 0.5 + 1e-6:
        return list(loop)  # snapping folded the loop: keep the raster version
    return clean


def drop_collinear(loop, tol):
    """Closed-loop RDP with a tiny tolerance: removes points lying on straight runs."""
    if len(loop) < 4:
        return loop
    i0 = min(range(len(loop)), key=lambda i: loop[i])
    pts = loop[i0:] + loop[:i0]
    x0, y0 = pts[0]
    i1 = max(range(len(pts)), key=lambda i: (pts[i][0] - x0) ** 2 + (pts[i][1] - y0) ** 2)
    a = rdp(pts[:i1 + 1], tol)
    b = rdp(pts[i1:] + [pts[0]], tol)
    res = a[:-1] + b[:-1]
    return res if len(res) >= 3 else loop


def despike(loop, max_len):
    """Remove back-and-forth spikes and near-duplicate points left by snapping.

    Where two real edges run a few millimetres apart (a wall base next to the
    floor edge), consecutive points can snap to alternate edges and the outline
    zigzags. A vertex whose outline reverses direction over a short distance
    is removed, as is any point closer than 0.1 mm to the previous one.
    """
    pts = list(loop)
    changed = True
    while changed and len(pts) > 3:
        changed = False
        i = 0
        while i < len(pts) and len(pts) > 3:
            p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            ax, ay = p1[0] - p0[0], p1[1] - p0[1]
            bx, by = p2[0] - p1[0], p2[1] - p1[1]
            la, lb = math.hypot(ax, ay), math.hypot(bx, by)
            if la < 1e-4:
                pts.pop(i)
                changed = True
                continue
            if lb > 1e-9 and min(la, lb) < max_len and (ax * bx + ay * by) / (la * lb) < -0.7:
                pts.pop(i)
                changed = True
                continue
            i += 1
    return pts


def merge_close(loop, dist):
    """Replace runs of points closer than `dist` by their midpoint (double edges a few mm apart)."""
    if len(loop) < 4 or dist <= 0:
        return loop
    out = []
    for p in loop:
        if out and math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) < dist:
            q = out[-1]
            out[-1] = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        else:
            out.append(p)
    if len(out) > 3 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) < dist:
        q = out.pop()
        out[0] = ((out[0][0] + q[0]) / 2, (out[0][1] + q[1]) / 2)
    return out if len(out) >= 3 else loop


def snap_loops(loops, segments, cell, simplify):
    """Snap every loop; simplify is the final tolerance on the snapped (exact) points."""
    if not len(segments):
        return loops
    sn = Snapper(segments, 2.0 * cell)  # edges: the raster is at most ~1-2 cells off
    out = []
    for lp in loops:
        s = snap_loop(lp, sn, 1.5 * cell)  # corners: only when clearly next to one
        s = despike(s, 2.0 * cell)
        s = merge_close(s, min(0.25 * cell, 0.01))
        s = despike(s, 2.0 * cell)
        s = drop_collinear(s, max(simplify, 1e-4))
        out.append(s)
    return out
