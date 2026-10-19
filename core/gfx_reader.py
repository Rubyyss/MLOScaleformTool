"""Read a minimap interior .gfx/.swf back into levels of filled paths (metres).

Used by the importer and by the round-trip tests. Handles DefineShape1-4,
nested sprites with matrices, solid / gradient / bitmap fills (the latter two
are imported with an approximate colour) and line styles.
"""

import struct
import zlib

from .geom import flatten, reverse_path, signed_area


class Bits:
    def __init__(self, data, pos=0):
        self.d = data
        self.p = pos * 8

    def u(self, n):
        v = 0
        for _ in range(n):
            v = (v << 1) | ((self.d[self.p >> 3] >> (7 - (self.p & 7))) & 1)
            self.p += 1
        return v

    def s(self, n):
        v = self.u(n)
        return v - (1 << n) if n and v >> (n - 1) else v

    def align(self):
        self.p = (self.p + 7) & ~7

    def u8(self):
        self.align()
        v = self.d[self.p >> 3]
        self.p += 8
        return v

    def u16(self):
        self.align()
        v, = struct.unpack_from("<H", self.d, self.p >> 3)
        self.p += 16
        return v

    @property
    def byte(self):
        return (self.p + 7) >> 3


def read_rect(b):
    n = b.u(5)
    r = [b.s(n) for _ in range(4)]
    b.align()
    return r


def read_matrix(b):
    a = d = 1.0
    r0 = r1 = 0.0
    if b.u(1):
        n = b.u(5)
        a, d = b.s(n) / 65536, b.s(n) / 65536
    if b.u(1):
        n = b.u(5)
        r0, r1 = b.s(n) / 65536, b.s(n) / 65536
    n = b.u(5)
    tx, ty = b.s(n), b.s(n)
    b.align()
    # x' = a*x + r1*y + tx ; y' = r0*x + d*y + ty
    return (a, r0, r1, d, tx, ty)


IDENTITY = (1.0, 0.0, 0.0, 1.0, 0, 0)


def mat_mul(m, n):
    """m applied after n (parent @ child)."""
    a, b, c, d, tx, ty = m
    a2, b2, c2, d2, tx2, ty2 = n
    return (a * a2 + c * b2, b * a2 + d * b2,
            a * c2 + c * d2, b * c2 + d * d2,
            a * tx2 + c * ty2 + tx, b * tx2 + d * ty2 + ty)


def mat_apply(m, x, y):
    a, b, c, d, tx, ty = m
    return a * x + c * y + tx, b * x + d * y + ty


def _read_cxform_alpha(b):
    ha, hm = b.u(1), b.u(1)
    n = b.u(4)
    mul = [b.s(n) for _ in range(4)] if hm else [256] * 4
    add = [b.s(n) for _ in range(4)] if ha else [0] * 4
    b.align()
    return mul, add


def _read_rgb(b, alpha):
    c = [b.u8(), b.u8(), b.u8()]
    c.append(b.u8() if alpha else 255)
    return tuple(c)


def _read_gradient(b, alpha, focal):
    b.align()
    b.u(2)
    b.u(2)
    n = b.u(4)
    cols = []
    for _ in range(n):
        b.u8()
        cols.append(_read_rgb(b, alpha))
    if focal:
        b.u16()
    return cols


def _read_fills(b, ver):
    n = b.u8()
    if n == 0xFF:
        n = b.u16()
    out = []
    alpha = ver >= 3
    for _ in range(n):
        t = b.u8()
        if t == 0x00:
            out.append(_read_rgb(b, alpha))
        elif t in (0x10, 0x12, 0x13):
            read_matrix(b)
            cols = _read_gradient(b, alpha, t == 0x13)
            out.append(cols[0] if cols else (128, 128, 128, 255))
        elif t in (0x40, 0x41, 0x42, 0x43):
            b.u16()
            read_matrix(b)
            out.append((128, 128, 128, 255))
        else:
            raise ValueError(f"unknown fill style type {t:#x}")
    return out


def _read_lines(b, ver):
    n = b.u8()
    if n == 0xFF:
        n = b.u16()
    out = []
    for _ in range(n):
        w = b.u16()
        if ver == 4:
            b.u(2)
            join = b.u(2)
            has_fill = b.u(1)
            b.u(1); b.u(1); b.u(1); b.u(5); b.u(1); b.u(2)
            b.align()
            if join == 2:
                b.u16()
            if has_fill:
                col = _read_fills_one(b)
            else:
                col = _read_rgb(b, True)
        else:
            col = _read_rgb(b, ver >= 3)
        out.append((w, col))
    return out


def _read_fills_one(b):
    t = b.u8()
    if t == 0x00:
        return _read_rgb(b, True)
    if t in (0x10, 0x12, 0x13):
        read_matrix(b)
        cols = _read_gradient(b, True, t == 0x13)
        return cols[0] if cols else (128, 128, 128, 255)
    b.u16()
    read_matrix(b)
    return (128, 128, 128, 255)


def parse_shape(body, ver):
    """Return (id, edges, fills, lines). edges: (fill0, fill1, line, seg) with global style ids."""
    cid, = struct.unpack_from("<H", body)
    b = Bits(body, 2)
    read_rect(b)
    if ver == 4:
        read_rect(b)
        b.u8()
    fills = _read_fills(b, ver)
    lines = _read_lines(b, ver)
    fill_base, line_base = 0, 0
    all_fills = list(fills)
    all_lines = list(lines)
    nf, nl = b.u(4), b.u(4)
    x = y = 0
    f0 = f1 = ln = 0
    edges = []
    while True:
        if b.u(1) == 0:
            flags = b.u(5)
            if flags == 0:
                break
            if flags & 1:
                n = b.u(5)
                x, y = b.s(n), b.s(n)
            if flags & 2:
                v = b.u(nf)
                f0 = v + fill_base if v else 0
            if flags & 4:
                v = b.u(nf)
                f1 = v + fill_base if v else 0
            if flags & 8:
                v = b.u(nl)
                ln = v + line_base if v else 0
            if flags & 16:
                fill_base, line_base = len(all_fills), len(all_lines)
                all_fills += _read_fills(b, ver)
                all_lines += _read_lines(b, ver)
                nf, nl = b.u(4), b.u(4)
        elif b.u(1):
            n = b.u(4) + 2
            if b.u(1):
                dx, dy = b.s(n), b.s(n)
            elif b.u(1):
                dx, dy = 0, b.s(n)
            else:
                dx, dy = b.s(n), 0
            edges.append((f0, f1, ln, ("L", x, y, x + dx, y + dy)))
            x += dx
            y += dy
        else:
            n = b.u(4) + 2
            cx, cy = x + b.s(n), y + b.s(n)
            ax, ay = cx + b.s(n), cy + b.s(n)
            edges.append((f0, f1, ln, ("Q", x, y, cx, cy, ax, ay)))
            x, y = ax, ay
    return cid, edges, all_fills, all_lines


def _reverse_seg(seg):
    if seg[0] == "L":
        return ("L", seg[3], seg[4], seg[1], seg[2])
    return ("Q", seg[5], seg[6], seg[3], seg[4], seg[1], seg[2])


def chain_loops(segs):
    """Join oriented segments (start -> end) into paths, preferring closed loops."""
    by_start = {}
    for i, s in enumerate(segs):
        by_start.setdefault((s[1], s[2]), []).append(i)
    used = [False] * len(segs)
    paths = []
    for i in range(len(segs)):
        if used[i]:
            continue
        used[i] = True
        chain = [segs[i]]
        start = (segs[i][1], segs[i][2])
        end = (segs[i][-2], segs[i][-1])
        while end != start:
            nxt = None
            for j in by_start.get(end, ()):
                if not used[j]:
                    nxt = j
                    break
            if nxt is None:
                break
            used[nxt] = True
            chain.append(segs[nxt])
            end = (segs[nxt][-2], segs[nxt][-1])
        paths.append((chain, end == start))
    return paths


def shape_to_layers(edges, fills, lines, fill1_is_right=False):
    """Group edges by fill style into loops.

    SWF spec (and Rockstar's Flash CS5 movies): FillStyle0 is on the left of the
    edge as seen on screen, FillStyle1 on the right. Loops come out with the fill
    on their left. Files written with the opposite habit (some converters, the
    add-on before 1.6) read back reversed; read_interior fixes the sign.
    """
    layers = []
    for fi in range(1, len(fills) + 1):
        segs = []
        line_use = {}
        for f0, f1, ln, seg in edges:
            if f0 == fi and f1 == fi:
                continue
            if ln and fi in (f0, f1):
                line_use[ln] = line_use.get(ln, 0) + 1
            if f1 == fi:
                segs.append(seg if fill1_is_right else _reverse_seg(seg))
            elif f0 == fi:
                segs.append(_reverse_seg(seg) if fill1_is_right else seg)
        if segs:
            line = lines[max(line_use, key=line_use.get) - 1] if line_use else None
            layers.append({"fill": fills[fi - 1], "loops": chain_loops(segs), "line": line})
    for li in range(1, len(lines) + 1):
        segs = [seg for f0, f1, ln, seg in edges if ln == li and not f0 and not f1]
        if segs:
            layers.append({"fill": None, "loops": chain_loops(segs), "line": lines[li - 1]})
    return layers


class Movie:
    def __init__(self, data):
        if data[:3] in (b"CFX", b"CWS"):
            data = data[:8] + zlib.decompress(data[8:])
        elif data[:3] not in (b"GFX", b"FWS"):
            raise ValueError("not a GFX/SWF file")
        self.data = data
        self.version = data[3]
        b = Bits(data, 8)
        self.stage = read_rect(b)
        p = b.byte
        self.fps, self.frame_count = struct.unpack_from("<HH", data, p)
        self.shapes = {}
        self.sprites = {}
        self.exports = {}
        self.root = self._read_timeline(p + 4, len(data))

    def _read_timeline(self, p, end):
        """Return list of frames; each frame = (label, [placements]) with display list snapshot."""
        d = self.data
        frames = []
        display = {}
        label = None
        while p < end:
            cl, = struct.unpack_from("<H", d, p)
            p += 2
            code, ln = cl >> 6, cl & 63
            if ln == 63:
                ln, = struct.unpack_from("<I", d, p)
                p += 4
            body = d[p:p + ln]
            if code in (2, 22, 32, 83):
                ver = {2: 1, 22: 2, 32: 3, 83: 4}[code]
                cid, edges, fills, lines = parse_shape(body, ver)
                self.shapes[cid] = (edges, fills, lines)
            elif code == 39:
                cid, = struct.unpack_from("<H", body)
                self.sprites[cid] = self._read_timeline(p + 4, p + ln)
            elif code == 26:
                fl = body[0]
                depth, = struct.unpack_from("<H", body, 1)
                b = Bits(body, 3)
                entry = dict(display.get(depth, {})) if fl & 1 else {}
                if fl & 2:
                    entry["char"] = b.u16()
                if fl & 4:
                    entry["matrix"] = read_matrix(b)
                if fl & 8:
                    entry["cxform"] = _read_cxform_alpha(b)
                if fl & 16:
                    b.u16()
                if fl & 32:
                    q = b.byte
                    e = body.index(0, q)
                    entry["name"] = body[q:e].decode("utf-8", "replace")
                entry.setdefault("matrix", IDENTITY)
                display[depth] = entry
            elif code == 28:
                depth, = struct.unpack_from("<H", body)
                display.pop(depth, None)
            elif code == 43:
                label = body[:body.index(0)].decode("utf-8", "replace")
            elif code == 56:
                n, = struct.unpack_from("<H", body)
                q = 2
                for _ in range(n):
                    cid, = struct.unpack_from("<H", body, q)
                    e = body.index(0, q + 2)
                    self.exports[body[q + 2:e].decode()] = cid
                    q = e + 1
            elif code == 1:
                frames.append((label, dict(display)))
                label = None
            elif code == 0:
                break
            p += ln
        return frames

    # ------------------------------------------------------------------ interior extraction

    def find_interior(self):
        """Return (label, entry) of the 'interior' clip on the root timeline."""
        for label, disp in self.root:
            for depth in sorted(disp):
                e = disp[depth]
                if e.get("name") == "interior":
                    return label, e
        # fall back: first sprite placed on the root
        for label, disp in self.root:
            for depth in sorted(disp):
                e = disp[depth]
                if e.get("char") in self.sprites:
                    return label, e
        raise ValueError("no 'interior' clip found")

    def collect(self, char, matrix, out, path=()):
        """Flatten shapes under a character into (matrix, shape_id, path-of-names)."""
        if char in self.shapes:
            out.append((matrix, char, path))
            return
        frames = self.sprites.get(char)
        if not frames:
            return
        _, disp = frames[0]
        for depth in sorted(disp):
            e = disp[depth]
            if "char" not in e:
                continue
            self.collect(e["char"], mat_mul(matrix, e["matrix"]), out, path + (e.get("name") or "",))


def _level_index(name):
    if not name or not name.startswith("level_"):
        return None
    s = name[6:]
    if s.startswith("u") and s[1:].isdigit():
        return -int(s[1:])
    if s.lstrip("-").isdigit():
        return int(s)
    return None


def read_interior(data, fill1_is_right=False):
    """Return dict(hash, label, levels={index: [layer]}, scale) with paths in metres.

    The 'interior' clip transform (minus the game's 100 % placement) maps twips
    to minimap pixels = metres, Y flipped.
    """
    mv = Movie(data)
    label, entry = mv.find_interior()
    items = []
    mv.collect(entry["char"], entry["matrix"], items)
    h = None
    if label and label.upper().startswith("INT") and label[3:].isdigit():
        h = int(label[3:])
    levels = {}
    for matrix, sid, names in items:
        idx = None
        for n in names:
            idx = _level_index(n)
            if idx is not None:
                break
        if idx is None:
            idx = 0
        edges, fills, lines = mv.shapes[sid]

        def conv(x, y, m=matrix):
            px, py = mat_apply(m, x, y)
            return (px / 20.0, -py / 20.0)

        for layer in shape_to_layers(edges, fills, lines, fill1_is_right):
            paths = []
            for chain, closed in layer["loops"]:
                first = chain[0]
                path = {"start": conv(first[1], first[2]), "segs": [], "closed": closed}
                for s in chain:
                    if s[0] == "L":
                        path["segs"].append(("L",) + conv(s[3], s[4]))
                    else:
                        path["segs"].append(("Q",) + conv(s[3], s[4]) + conv(s[5], s[6]))
                paths.append(path)
            closed = [p for p in paths if p["closed"]]
            if closed and sum(signed_area(flatten(p)) for p in closed) < 0:
                paths = [reverse_path(p) if p["closed"] else p for p in paths]  # other fill-side habit
            out = {"fill": layer["fill"], "paths": paths}
            if layer["line"]:
                w, col = layer["line"]
                sx = (matrix[0] ** 2 + matrix[1] ** 2) ** 0.5
                out["stroke"] = (w * sx / 20.0, col)
            levels.setdefault(idx, []).append(out)
    return {"hash": h, "label": label, "levels": levels, "interior_matrix": entry["matrix"]}


def filled_area(paths):
    """Signed area sum (positive when loops are oriented with fill on the left, y-up)."""
    return sum(signed_area(flatten(p)) for p in paths if p.get("closed", True))
