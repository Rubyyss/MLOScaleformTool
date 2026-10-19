"""Software preview of an interior .gfx: what one level looks like on the minimap.

The image is rendered from the GFX bytes themselves (read back with
gfx_reader), so it shows what the file really contains: fills in draw order,
holes, strokes and colours. North (+Y of the MLO) is up, 1 m = `ppm` pixels.
"""

import math

import numpy as np

from .geom import bounds, flatten
from .gfx_reader import read_interior
from .raster import Grid

MINIMAP_BG = (56, 74, 80)  # background of the retail minimap bitmaps


def _grid(x0, y0, w, h, cell):
    g = Grid.__new__(Grid)
    g.cell, g.x0, g.y0, g.w, g.h = float(cell), float(x0), float(y0), int(w), int(h)
    g.data = np.zeros((g.h, g.w), dtype=bool)
    return g


def _segments(paths, steps=8):
    segs = []
    for p in paths:
        pts = flatten(p, steps)
        if len(pts) < 2:
            continue
        a = np.asarray(pts, dtype=np.float64)
        if p.get("closed", True):
            b = np.roll(a, -1, axis=0)
        else:
            a, b = a[:-1], a[1:]
        segs.append(np.stack([a, b], axis=1))
    return np.concatenate(segs) if segs else np.zeros((0, 2, 2))


def content_bounds(levels):
    bb = [bounds(L["paths"]) for layers in levels.values() for L in layers]
    bb = [b for b in bb if b]
    if not bb:
        return (-5.0, -5.0, 5.0, 5.0)
    return (min(b[0] for b in bb), min(b[1] for b in bb), max(b[2] for b in bb), max(b[3] for b in bb))


def render_levels(levels, level, size=512, background=MINIMAP_BG, grid=True, origin=True,
                  ghost_below=True, margin=0.08, supersample=2, frame=None):
    """Render one level -> (rgba float array (h, w, 4) in sRGB 0-1, info dict).

    levels: read_interior()["levels"]. frame: optional (xmin, ymin, xmax, ymax) to keep
    the same framing between levels (default: bounds of every level).
    """
    xmin, ymin, xmax, ymax = frame or content_bounds(levels)
    span = max(xmax - xmin, ymax - ymin, 1.0)
    pad = span * margin
    xmin, ymin, xmax, ymax = xmin - pad, ymin - pad, xmax + pad, ymax + pad
    ppm = size / max(xmax - xmin, ymax - ymin)  # output pixels per metre
    w = max(16, int(round((xmax - xmin) * ppm)))
    h = max(16, int(round((ymax - ymin) * ppm)))
    ss = max(1, int(supersample))
    cell = 1.0 / (ppm * ss)
    W, H = w * ss, h * ss

    img = np.empty((H, W, 3), dtype=np.float32)
    img[:] = np.asarray(background, dtype=np.float32) / 255.0

    def blend(mask, rgb, alpha):
        if not mask.any():
            return
        a = float(alpha)
        img[mask] = img[mask] * (1 - a) + np.asarray(rgb, dtype=np.float32) * a

    if grid:
        xs = np.arange(math.ceil(xmin), math.floor(xmax) + 1)
        ys = np.arange(math.ceil(ymin), math.floor(ymax) + 1)
        for strong in (False, True):
            m = np.zeros((H, W), dtype=bool)
            lw = 1 if not strong else max(1, ss)
            for x in xs:
                if (int(x) % 5 == 0) != strong:
                    continue
                c = int((x - xmin) / cell)
                m[:, max(0, c):min(W, c + lw)] = True
            for y in ys:
                if (int(y) % 5 == 0) != strong:
                    continue
                r = int((y - ymin) / cell)
                m[max(0, r):min(H, r + lw), :] = True
            blend(m, (1, 1, 1), 0.10 if strong else 0.05)

    def draw_level(layers, dim):
        for L in layers:
            segs = _segments(L["paths"])
            if L.get("fill"):
                g = _grid(xmin, ymin, W, H, cell)
                g.fill_nonzero(segs)
                r, gg, b, a = L["fill"]
                blend(g.data, (r / 255, gg / 255, b / 255), a / 255 * dim)
            if L.get("stroke"):
                wdt, (r, gg, b, a) = L["stroke"]
                g = _grid(xmin, ymin, W, H, cell)
                g.stroke_segments(segs, max(wdt, cell), keep_solid=False)
                blend(g.data, (r / 255, gg / 255, b / 255), a / 255 * dim)

    if ghost_below:
        below = [i for i in levels if i < level]
        if below:
            draw_level(levels[max(below)], 0.25)
    draw_level(levels.get(level, []), 1.0)

    if origin and xmin <= 0 <= xmax and ymin <= 0 <= ymax:
        cx, cy = int(-xmin / cell), int(-ymin / cell)
        arm = int(0.6 / cell)
        t = max(1, ss)
        m = np.zeros((H, W), dtype=bool)
        m[max(0, cy - t // 2):cy + t - t // 2, max(0, cx - arm):cx + arm] = True
        m[max(0, cy - arm):cy + arm, max(0, cx - t // 2):cx + t - t // 2] = True
        blend(m, (1.0, 0.85, 0.1), 0.95)

    if ss > 1:
        img = img.reshape(h, ss, w, ss, 3).mean(axis=(1, 3))
    rgba = np.concatenate([img, np.ones((h, w, 1), dtype=np.float32)], axis=2)
    info = {"ppm": ppm, "frame": (xmin, ymin, xmax, ymax), "size": (w, h)}
    return rgba, info


def render_gfx(data, level=0, **kw):
    res = read_interior(data)
    rgba, info = render_levels(res["levels"], level, **kw)
    info["levels"] = sorted(res["levels"])
    info["label"] = res["label"]
    return rgba, info
