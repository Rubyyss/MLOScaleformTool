"""Minimal SWF / Scaleform GFX tag writer.

Only what a GTA V minimap interior movie needs: shapes (solid fills, lines,
straight and quadratic edges), sprites, PlaceObject2, frame labels, exports
and raw action bytecode. Coordinates passed to this module are in twips.
"""

import struct

TWIPS = 20

# Tag codes
END = 0
SHOW_FRAME = 1
SET_BACKGROUND_COLOR = 9
DO_ACTION = 12
DEFINE_SHAPE2 = 22
PLACE_OBJECT2 = 26
DEFINE_SHAPE3 = 32
DEFINE_SPRITE = 39
FRAME_LABEL = 43
EXPORT_ASSETS = 56
DO_INIT_ACTION = 59
FILE_ATTRIBUTES = 69
GFX_EXPORTER_INFO = 1000

# Largest delta a StraightEdge/CurvedEdge record can hold (NumBits is UB[4] + 2 = 17 bits signed).
MAX_EDGE_DELTA = (1 << 16) - 1


class BitWriter:
    def __init__(self):
        self.buf = bytearray()
        self.acc = 0
        self.nbits = 0

    def ub(self, value, n):
        if n == 0:
            return
        if value < 0 or value >> n:
            raise ValueError(f"{value} does not fit in UB[{n}]")
        for i in range(n - 1, -1, -1):
            self.acc = (self.acc << 1) | ((value >> i) & 1)
            self.nbits += 1
            if self.nbits == 8:
                self.buf.append(self.acc)
                self.acc = 0
                self.nbits = 0

    def sb(self, value, n):
        if n == 0:
            if value:
                raise ValueError("non-zero value with 0 bits")
            return
        lo, hi = -(1 << (n - 1)), (1 << (n - 1)) - 1
        if not lo <= value <= hi:
            raise ValueError(f"{value} does not fit in SB[{n}]")
        self.ub(value & ((1 << n) - 1), n)

    def align(self):
        if self.nbits:
            self.ub(0, 8 - self.nbits)

    def u8(self, v):
        self.align()
        self.buf.append(v & 0xFF)

    def u16(self, v):
        self.align()
        self.buf += struct.pack("<H", v)

    def raw(self, data):
        self.align()
        self.buf += data

    def bytes(self):
        self.align()
        return bytes(self.buf)


def sbits(*values):
    """Minimum signed bit count holding all values."""
    n = 1
    for v in values:
        v = int(v)
        need = (v if v >= 0 else ~v).bit_length() + 1
        n = max(n, need)
    return n


def ubits(*values):
    return max(1, max(int(v).bit_length() for v in values))


def write_rect(w, xmin, xmax, ymin, ymax):
    n = sbits(xmin, xmax, ymin, ymax)
    w.ub(n, 5)
    for v in (xmin, xmax, ymin, ymax):
        w.sb(int(v), n)
    w.align()


def write_matrix(w, sx=1.0, sy=1.0, r0=0.0, r1=0.0, tx=0, ty=0):
    """Flash MATRIX: [sx r1 tx; r0 sy ty] with r0 = RotateSkew0, r1 = RotateSkew1."""
    if sx != 1.0 or sy != 1.0:
        a, d = round(sx * 65536), round(sy * 65536)
        n = sbits(a, d)
        w.ub(1, 1)
        w.ub(n, 5)
        w.sb(a, n)
        w.sb(d, n)
    else:
        w.ub(0, 1)
    if r0 or r1:
        b, c = round(r0 * 65536), round(r1 * 65536)
        n = sbits(b, c)
        w.ub(1, 1)
        w.ub(n, 5)
        w.sb(b, n)
        w.sb(c, n)
    else:
        w.ub(0, 1)
    tx, ty = int(round(tx)), int(round(ty))
    if tx or ty:
        n = sbits(tx, ty)
        w.ub(n, 5)
        w.sb(tx, n)
        w.sb(ty, n)
    else:
        w.ub(0, 5)
    w.align()


def write_cxform_alpha(w, mul_rgba=(256, 256, 256, 256), add_rgba=None):
    """CXFORMWITHALPHA."""
    vals = list(mul_rgba) + (list(add_rgba) if add_rgba else [])
    n = max(sbits(*vals), 1)
    w.ub(1 if add_rgba else 0, 1)
    w.ub(1, 1)
    w.ub(n, 4)
    for v in mul_rgba:
        w.sb(v, n)
    if add_rgba:
        for v in add_rgba:
            w.sb(v, n)
    w.align()


def tag(code, body=b""):
    body = bytes(body)
    if len(body) < 63 and code not in (DEFINE_SHAPE2, DEFINE_SHAPE3):
        return struct.pack("<H", (code << 6) | len(body)) + body
    return struct.pack("<HI", (code << 6) | 63, len(body)) + body


def cstr(s):
    return s.encode("utf-8") + b"\0"


# --------------------------------------------------------------------------- shapes

class ShapePath:
    """One closed or open sub-path in twips.

    segments: list of ("L", x, y) or ("Q", cx, cy, x, y); start is (x0, y0).
    fill_left / fill_right: fill style index (1-based, 0 = none) on each side
    of the travel direction, in Flash's y-down space.
    """

    def __init__(self, start, segments, fill_left=0, fill_right=0, line=0):
        self.start = start
        self.segments = segments
        self.fill_left = fill_left
        self.fill_right = fill_right
        self.line = line


def _split_line(x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    pieces = max(1, -(-max(abs(dx), abs(dy)) // MAX_EDGE_DELTA))
    pts = []
    for i in range(1, pieces + 1):
        pts.append((x0 + round(dx * i / pieces), y0 + round(dy * i / pieces)))
    return pts


def _quad_fits(x0, y0, cx, cy, x1, y1):
    return max(abs(cx - x0), abs(cy - y0), abs(x1 - cx), abs(y1 - cy)) <= MAX_EDGE_DELTA


def _split_quad(x0, y0, cx, cy, x1, y1):
    if _quad_fits(x0, y0, cx, cy, x1, y1):
        return [(cx, cy, x1, y1)]
    ax, ay = (x0 + cx) / 2, (y0 + cy) / 2
    bx, by = (cx + x1) / 2, (cy + y1) / 2
    mx, my = round((ax + bx) / 2), round((ay + by) / 2)
    return (_split_quad(x0, y0, round(ax), round(ay), mx, my)
            + _split_quad(mx, my, round(bx), round(by), x1, y1))


def _write_styles(w, fills, lines, shape3):
    # FILLSTYLEARRAY
    if len(fills) >= 0xFF:
        w.u8(0xFF)
        w.u16(len(fills))
    else:
        w.u8(len(fills))
    for rgba in fills:
        w.u8(0x00)  # solid
        w.raw(bytes(rgba[:4] if shape3 else rgba[:3]))
    # LINESTYLEARRAY
    if len(lines) >= 0xFF:
        w.u8(0xFF)
        w.u16(len(lines))
    else:
        w.u8(len(lines))
    for width, rgba in lines:
        w.u16(int(width))
        w.raw(bytes(rgba[:4] if shape3 else rgba[:3]))


def define_shape(char_id, paths, fills, lines=()):
    """Build a DefineShape2/3 tag.

    fills: list of (r, g, b, a) 0-255; lines: list of (width_twips, (r, g, b, a)).
    Uses DefineShape3 when any colour has alpha < 255.
    """
    shape3 = any(c[3] < 255 for c in fills) or any(c[3] < 255 for _, c in lines)
    xs, ys = [], []
    for p in paths:
        xs.append(p.start[0])
        ys.append(p.start[1])
        for s in p.segments:
            xs.extend(s[1::2])
            ys.extend(s[2::2])
    if not xs:
        xs = ys = [0]
    pad = max((wd for wd, _ in lines), default=0) // 2
    bounds = (int(min(xs)) - pad, int(max(xs)) + pad, int(min(ys)) - pad, int(max(ys)) + pad)

    w = BitWriter()
    w.raw(struct.pack("<H", char_id))
    write_rect(w, *bounds)
    _write_styles(w, fills, lines, shape3)
    nf = ubits(len(fills)) if fills else 0
    nl = ubits(len(lines)) if lines else 0
    w.ub(nf, 4)
    w.ub(nl, 4)

    cur_f0 = cur_f1 = cur_l = 0
    first = True
    for p in paths:
        # STYLECHANGERECORD with moveTo
        x, y = int(p.start[0]), int(p.start[1])
        f0, f1, ln = p.fill_left, p.fill_right, p.line
        flags = 0x01
        if first or f0 != cur_f0:
            flags |= 0x02
        if first or f1 != cur_f1:
            flags |= 0x04
        if (first or ln != cur_l) and nl:
            flags |= 0x08
        w.ub(0, 1)
        w.ub(flags, 5)
        n = sbits(x, y)
        w.ub(n, 5)
        w.sb(x, n)
        w.sb(y, n)
        if flags & 0x02:
            w.ub(f0, nf)
        if flags & 0x04:
            w.ub(f1, nf)
        if flags & 0x08:
            w.ub(ln, nl)
        cur_f0, cur_f1, cur_l = f0, f1, ln
        first = False

        for seg in p.segments:
            if seg[0] == "L":
                for nx, ny in _split_line(x, y, int(seg[1]), int(seg[2])):
                    dx, dy = nx - x, ny - y
                    if dx == 0 and dy == 0:
                        continue
                    n = max(sbits(dx, dy), 2)
                    w.ub(1, 1)  # edge
                    w.ub(1, 1)  # straight
                    w.ub(n - 2, 4)
                    if dx and dy:
                        w.ub(1, 1)
                        w.sb(dx, n)
                        w.sb(dy, n)
                    elif dx:
                        w.ub(0, 1)
                        w.ub(0, 1)
                        w.sb(dx, n)
                    else:
                        w.ub(0, 1)
                        w.ub(1, 1)
                        w.sb(dy, n)
                    x, y = nx, ny
            else:
                for cx, cy, ax, ay in _split_quad(x, y, int(seg[1]), int(seg[2]), int(seg[3]), int(seg[4])):
                    c_dx, c_dy = cx - x, cy - y
                    a_dx, a_dy = ax - cx, ay - cy
                    if not (c_dx or c_dy or a_dx or a_dy):
                        continue
                    n = max(sbits(c_dx, c_dy, a_dx, a_dy), 2)
                    w.ub(1, 1)
                    w.ub(0, 1)  # curved
                    w.ub(n - 2, 4)
                    w.sb(c_dx, n)
                    w.sb(c_dy, n)
                    w.sb(a_dx, n)
                    w.sb(a_dy, n)
                    x, y = ax, ay
    w.ub(0, 6)  # EndShapeRecord
    return tag(DEFINE_SHAPE3 if shape3 else DEFINE_SHAPE2, w.bytes()), bounds


# --------------------------------------------------------------------------- display list

def place_object2(depth, char_id=None, matrix=None, cxform=None, name=None, ratio=None):
    w = BitWriter()
    flags = 0
    if char_id is not None:
        flags |= 0x02
    if matrix is not None:
        flags |= 0x04
    if cxform is not None:
        flags |= 0x08
    if ratio is not None:
        flags |= 0x10
    if name is not None:
        flags |= 0x20
    w.u8(flags)
    w.u16(depth)
    if char_id is not None:
        w.u16(char_id)
    if matrix is not None:
        write_matrix(w, **matrix)
    if cxform is not None:
        write_cxform_alpha(w, **cxform)
    if ratio is not None:
        w.u16(ratio)
    if name is not None:
        w.raw(cstr(name))
    return tag(PLACE_OBJECT2, w.bytes())


def define_sprite(char_id, frame_count, inner_tags):
    body = struct.pack("<HH", char_id, frame_count) + b"".join(inner_tags)
    return tag(DEFINE_SPRITE, body)


def frame_label(name):
    return tag(FRAME_LABEL, cstr(name))


def export_assets(items):
    body = struct.pack("<H", len(items))
    for char_id, name in items:
        body += struct.pack("<H", char_id) + cstr(name)
    return tag(EXPORT_ASSETS, body)


def do_action(code):
    return tag(DO_ACTION, code)


def do_init_action(sprite_id, code):
    return tag(DO_INIT_ACTION, struct.pack("<H", sprite_id) + code)


def exporter_info(swf_name, version=0x36F, flags=0, bitmap_format=13, prefix=""):
    """Tag 1000 that must be the first tag of a .gfx (GFxLoaderImpl::ReadExporterInfoTag)."""
    p = prefix.encode()
    n = swf_name.encode()
    body = struct.pack("<HIH", version, flags, bitmap_format)
    body += bytes([len(p)]) + p + bytes([len(n)]) + n
    body += struct.pack("<H", 0)  # no AMP code offsets
    return tag(GFX_EXPORTER_INFO, body)


def movie(tags, frame_count, stage_twips=(0, 6000, 0, 6000), fps=30.0, version=8, signature=b"GFX"):
    w = BitWriter()
    write_rect(w, *stage_twips)
    w.raw(struct.pack("<HH", int(round(fps * 256)), frame_count))
    body = w.bytes() + b"".join(tags)
    return signature + bytes([version]) + struct.pack("<I", 8 + len(body)) + body
