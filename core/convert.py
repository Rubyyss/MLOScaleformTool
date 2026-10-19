"""Turn triangles (MLO-local metres) into minimap outlines per floor."""

import math
from dataclasses import dataclass

import numpy as np

from .raster import Grid, close, dilate, open_, section_segments, split_closed, triangle_normals_z
from .snap import boundary_edges, snap_loops


@dataclass
class ConvertSettings:
    mode: str = "FLOOR"         # FLOOR (walkable, up-facing) | FOOTPRINT (everything in the floor band)
    cell: float = 0.05          # metres per raster cell
    simplify: float = 0.005     # outline tolerance in metres, applied to the snapped (exact) points
    snap: bool = True           # move outline vertices onto the real mesh corners / edges
    min_area: float = 0.25      # drop islands / holes smaller than this (m2)
    close_gaps: float = 0.10    # morphological closing (m), fills cracks between floor pieces
    remove_thin: float = 0.2    # morphological opening (m), removes slivers such as wall tops
    floor_tolerance: float = 0.6  # FLOOR: faces whose height is within +-this of the floor height
    max_slope: float = 40.0     # FLOOR: steepest face that still counts as floor (degrees)
    walls: bool = False         # also produce a second (darker) layer drawn over the floor
    wall_mode: str = "OBSTACLES"  # OBSTACLES: anything you bump into (Rockstar style) | SECTION: cut walls
    obstacle_min: float = 0.25  # OBSTACLES: band above the floor that blocks walking (m)
    obstacle_max: float = 2.0
    cut_height: float = 1.2     # SECTION: cut height above the floor (m)
    wall_width: float = 0.15    # minimum drawn width for single-plane walls (m)


def _grid_for(xy_min, xy_max, cell):
    return Grid(xy_min[0], xy_min[1], xy_max[0], xy_max[1], cell)


def floor_mask(tris, floor_z, height, s: ConvertSettings, grid: Grid):
    zc = tris[:, :, 2]
    if s.mode == "FLOOR":
        nz = triangle_normals_z(tris)
        cz = zc.mean(axis=1)
        sel = (nz >= math.cos(math.radians(s.max_slope))) & \
              (cz >= floor_z - s.floor_tolerance) & (cz <= floor_z + s.floor_tolerance)
    else:
        top = floor_z + max(height, 0.2) - 0.1
        sel = (zc.max(axis=1) >= floor_z - 0.05) & (zc.min(axis=1) <= top)
    g = grid.empty_like()
    g.fill_triangles(tris[sel][:, :, :2])
    return g, sel


def snap_targets(tris, sel, s: ConvertSettings):
    """Real edges the floor outline can snap to."""
    xy = tris[sel][:, :, :2]
    if s.mode == "FLOOR":
        return boundary_edges(xy)
    e = np.concatenate([xy[:, [0, 1]], xy[:, [1, 2]], xy[:, [2, 0]]]) if len(xy) else np.zeros((0, 2, 2))
    return e[np.hypot(*(e[:, 1] - e[:, 0]).T) > 1e-6] if len(e) else e


def rect_edges(rects):
    out = []
    for x0, y0, x1, y1 in rects:
        c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        out += [(c[i], c[(i + 1) % 4]) for i in range(4)]
    return np.array(out, dtype=np.float64).reshape(-1, 2, 2)


def wall_mask(tris, floor_z, s: ConvertSettings, grid: Grid):
    segs = section_segments(tris, floor_z + s.cut_height)
    closed, opened = split_closed(segs)
    g = grid.empty_like()
    g.fill_nonzero(closed)
    g.stroke_segments(closed, 0.0)  # walls thinner than a cell stay visible
    g.stroke_segments(opened, s.wall_width, keep_solid=False)
    # snap only to solid walls: single-plane walls get an artificial width that must stay
    return g, closed


def obstacle_mask(tris, floor_z, s: ConvertSettings, grid: Grid, floor: Grid):
    """Footprint of everything between floor+obstacle_min and floor+obstacle_max, inside the floor."""
    zc = tris[:, :, 2]
    sel = (zc.max(axis=1) > floor_z + s.obstacle_min) & (zc.min(axis=1) < floor_z + s.obstacle_max)
    g = grid.empty_like()
    g.fill_triangles(tris[sel][:, :, :2])
    g.data &= floor.data
    return g, sel


def _cells(m, cell):
    return int(round(m / cell))


def postprocess(g: Grid, s: ConvertSettings, clip=None):
    d = g.data
    if s.close_gaps > 0:
        d = close(d, _cells(s.close_gaps / 2, g.cell))
    if s.remove_thin > 0:
        r = _cells(s.remove_thin / 2, g.cell)
        opened = open_(d, r)
        # give back what the opening shaved off next to the kept areas (corners of rotated rooms)
        d = opened | (d & dilate(opened, r + 1))
    if clip is not None:
        d = d & clip.data
    g.data = d
    return g


def convert_level(tris, floor_z, height, s: ConvertSettings, clip_rects=None):
    """Return {"floor": loops, "walls": loops}; loops are [(x, y), ...] in metres, fill on the left."""
    tris = np.asarray(tris, dtype=np.float64).reshape(-1, 3, 3)
    out = {"floor": [], "walls": []}
    if len(tris) == 0:
        return out
    lo = tris[:, :, :2].reshape(-1, 2).min(axis=0)
    hi = tris[:, :, :2].reshape(-1, 2).max(axis=0)
    grid = _grid_for(lo, hi, s.cell)
    clip = None
    if clip_rects:
        clip = grid.empty_like()
        clip.fill_rects(clip_rects)
    # with snapping the raster only needs a light clean-up; the real tolerance is applied after
    raster_tol = min(s.simplify, s.cell * 0.5) if s.snap else s.simplify
    fm, sel = floor_mask(tris, floor_z, height, s, grid)
    fm = postprocess(fm, s, clip)
    out["floor"] = fm.trace(raster_tol, s.min_area)
    extra = rect_edges(clip_rects) if clip_rects else np.zeros((0, 2, 2))
    if s.snap:
        targets = np.concatenate([snap_targets(tris, sel, s), extra])
        out["floor"] = snap_loops(out["floor"], targets, s.cell, s.simplify)
    if s.walls and s.wall_mode == "OBSTACLES":
        om, osel = obstacle_mask(tris, floor_z, s, grid, fm)
        if s.remove_thin > 0:
            om.data = open_(om.data, _cells(s.remove_thin / 2, grid.cell))
        out["walls"] = om.trace(raster_tol, s.min_area * 0.2)
        if s.snap:
            sub = ConvertSettings(**{**s.__dict__, "mode": "FOOTPRINT"})
            targets = np.concatenate([snap_targets(tris, osel, sub), snap_targets(tris, sel, s), extra])
            out["walls"] = snap_loops(out["walls"], targets, s.cell, s.simplify)
    elif s.walls:
        wm, segs = wall_mask(tris, floor_z, s, grid)
        if clip is not None:
            wm.data &= clip.data
        out["walls"] = wm.trace(raster_tol, s.min_area * 0.1)
        if s.snap:
            out["walls"] = snap_loops(out["walls"], np.concatenate([segs, extra]), s.cell, s.simplify)
    return out


def detect_floors(tris, min_area=4.0, merge=1.2, max_slope=40.0):
    """Find floor heights from up-facing area. Returns [(z, height), ...] bottom to top."""
    tris = np.asarray(tris, dtype=np.float64).reshape(-1, 3, 3)
    if len(tris) == 0:
        return []
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    n = np.cross(b - a, c - a)
    area_xy = np.abs(n[:, 2]) * 0.5
    L = np.linalg.norm(n, axis=1)
    L[L == 0] = 1
    up = (n[:, 2] / L) >= math.cos(math.radians(max_slope))
    cz = tris[:, :, 2].mean(axis=1)
    if not up.any():
        return [(float(tris[:, :, 2].min()), float(np.ptp(tris[:, :, 2])))]
    z, w = cz[up], area_xy[up]
    step = 0.1
    zmin, zmax = z.min(), z.max()
    bins = np.floor((z - zmin) / step).astype(np.int64)
    hist = np.bincount(bins, weights=w)
    peaks = []
    for i in np.argsort(-hist):
        if hist[i] < min_area:
            break
        zi = zmin + (i + 0.5) * step
        if all(abs(zi - p) >= merge for p in peaks):
            peaks.append(zi)
    peaks.sort()
    # snap each peak to the area-weighted mean of its bin neighbourhood
    snapped = []
    for p in peaks:
        m = np.abs(z - p) <= step * 1.5
        snapped.append(float(np.average(z[m], weights=w[m])) if m.any() else float(p))
    top = float(tris[:, :, 2].max())
    out = []
    for i, zf in enumerate(snapped):
        nxt = snapped[i + 1] if i + 1 < len(snapped) else top
        out.append((round(zf, 3), round(max(nxt - zf, 0.5), 3)))
    return out
