"""Build a GTA V minimap interior movie (int<hash>.gfx).

How the game uses it (game/frontend/MiniMapRenderThread.cpp, UpdateInterior):
  * loads the movie "INT<hash>" (hash = interior archetype name hash) and calls
    gotoAndStop("INT<hash>") on it;
  * takes the child clip named "interior", places it at (pos.x, -pos.y) of the
    interior instance, rotation -heading (degrees), scale 100 %;
  * shows the current floor by setting alpha 100 on "interior.level_<n>"
    (or "level_u<n>" for negative floors) and alpha 0 on the previous one.
The minimap layer uses 1 px = 1 metre (blips are placed the same way), so the
content of "interior" must be drawn in MLO-local metres with Y flipped.

Shapes are stored `scale` times bigger and the "interior" clip is scaled by
1/scale, which keeps sub-centimetre precision (1 twip = 1/(20*scale) m).
With a power of two scale the placement matrix is exact.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import swf
from .geom import close_path, orient_even_odd, split_islands, to_quadratic

# Rockstar's AS2 boilerplate (identical in every interior movie):
#   frame 1:  var TIMELINE = new com.rockstargames.gtav.minimap.INTERIORS(this); stop();
#   INTERIORS(TIMELINE) -> GameInterface.call("INTERIOR_IS_LOADED", MINIMAP_TYPE, TIMELINE)
FRAME1_ACTION = bytes.fromhex(
    "9610000054494d454c494e45000074686973001c960a00070100000000636f6d001c960f0000726f636b7374617267616d65"
    "73004e9606000067746176004e960900006d696e696d6170004e960b0000494e544552494f525300533c0700")

INTERIORS_CLASS = "__Packages.com.rockstargames.gtav.minimap.INTERIORS"
INTERIORS_INIT = bytes.fromhex(
    "888e000f005f676c6f62616c00636f6d004f626a65637400726f636b7374617267616d65730067746176006d696e696d6170"
    "00494e544552494f52530075690067616d650047616d65496e74657266616365004d494e494d41505f5459504500494e5445"
    "52494f525f49535f4c4f414445440063616c6c0070726f746f7479706500415353657450726f70466c616773009602000800"
    "1c96020008014e12129d0200180096020008001c960d0008010600000000000000000802404f1796020008001c9602000801"
    "4e96020008034e12129d02001e0096020008001c96020008014e960d0008030600000000000000000802404f179602000800"
    "1c96020008014e96020008034e96020008044e12129d0200240096020008001c96020008014e96020008034e960d00080406"
    "00000000000000000802404f1796020008001c96020008014e96020008034e96020008044e96020008054e12129d02002a00"
    "96020008001c96020008014e96020008034e96020008044e960d0008050600000000000000000802404f1796020008001c96"
    "020008014e96020008034e96020008044e96020008054e96020008064e12129d0200cb0096020008011c96020008034e9602"
    "0008044e96020008054e96020008068e1200000100022a000154494d454c494e45005200960400040108011c96020008034e"
    "96020008074e96020008084e96020008094e960200080a4e960900080b070300000008011c96020008034e96020008074e96"
    "020008084e96020008094e960200080c5217870100014f9604000401080d4e870100021796080007010000000208011c9602"
    "0008034e96020008044e96020008054e96020008064e960200080d4e9607000703000000080e3d1700")

GAMEINTERFACE_CLASS = "__Packages.com.rockstargames.ui.game.GameInterface"
GAMEINTERFACE_INIT = bytes.fromhex(
    "88d50016005f676c6f62616c00636f6d004f626a65637400726f636b7374617267616d65730075690067616d650047616d65"
    "496e746572666163650070726f746f747970650063616c6c00666c6173680065787465726e616c0045787465726e616c496e"
    "74657266616365006170706c790047454e455249435f54595045005343524950545f54595045004855445f54595045004d49"
    "4e494d41505f54595045005745425f54595045004355545343454e455f545950450050415553455f545950450053544f5245"
    "00415353657450726f70466c6167730096020008001c96020008014e12129d0200180096020008001c960d00080106000000"
    "00000000000802404f1796020008001c96020008014e96020008034e12129d02001e0096020008001c96020008014e960d00"
    "08030600000000000000000802404f1796020008001c96020008014e96020008034e96020008044e12129d02002400960200"
    "08001c96020008014e96020008034e960d0008040600000000000000000802404f1796020008001c96020008014e96020008"
    "034e96020008044e96020008054e12129d02002a0096020008001c96020008014e96020008034e96020008044e960d000805"
    "0600000000000000000802404f1796020008001c96020008014e96020008034e96020008044e96020008054e96020008064e"
    "12129d0200120196020008011c96020008034e96020008044e96020008054e96020008069b05000000000000870100014f96"
    "0400040108074e8701000217960400040108088e08000000000226002700960a00040102070200000008091c960200080a4e"
    "960200080b4e96020008084e960200080c52174f960d000401080d0600000000000000004f9609000401080e07010000004f"
    "9609000401080f07020000004f9609000401081007030000004f9609000401081107040000004f9609000401081207050000"
    "004f9609000401081307060000004f9609000401081407070000004f96080007010000000208011c96020008034e96020008"
    "044e96020008054e96020008064e96020008074e960700070300000008153d1700")

# Loops are written with the fill on their left as seen on screen. The SWF spec
# puts FillStyle0 on that side, and so do Rockstar's own interior movies
# (int3661284625.gfx, Flash CS5): 132 left/fill0 edges, 26 right/fill1, none reversed.
INTERIOR_FILL_SLOT = 0


@dataclass
class Layer:
    """One drawable: closed paths in metres (MLO-local, y-up) plus a style."""
    paths: list
    fill: Optional[Tuple[int, int, int, int]] = (153, 153, 153, 255)
    stroke_width: float = 0.0  # metres
    stroke: Tuple[int, int, int, int] = (64, 64, 64, 255)
    name: str = ""


@dataclass
class Level:
    index: int
    layers: List[Layer] = field(default_factory=list)

    @property
    def clip_name(self):
        return f"level_{self.index}" if self.index >= 0 else f"level_u{-self.index}"


@dataclass
class InteriorMap:
    hash: int
    levels: List[Level]
    scale: int = 16                 # stored px per metre (power of two keeps the 1/scale matrix exact)
    curve_tolerance: float = 0.005  # metres, cubic -> quadratic error
    linkage_name: str = ""          # optional ExportAssets name for the "interior" sprite
    levels_visible: bool = False    # alpha of every level clip (the game overrides it)
    separate_shapes: bool = True    # one DefineShape per island (outer loop + its holes), like Flash exports
    frame_count: int = 20

    @property
    def label(self):
        return f"INT{self.hash}"

    @property
    def file_name(self):
        return f"int{self.hash}.gfx"


def _to_twips(path, k):
    """metres (y-up) -> twips (y-down)."""
    def t(x, y):
        return (int(round(x * k)), int(round(-y * k)))

    start = t(*path["start"])
    segs = []
    for s in path["segs"]:
        if s[0] == "L":
            segs.append(("L",) + t(s[1], s[2]))
        else:
            segs.append(("Q",) + t(s[1], s[2]) + t(s[3], s[4]))
    return start, segs


def _shape_path(p, k, curve_tol, fill_idx, line_idx):
    start, segs = _to_twips(to_quadratic(p, curve_tol), k)
    if INTERIOR_FILL_SLOT == 0:
        return swf.ShapePath(start, segs, fill_left=fill_idx, fill_right=0, line=line_idx)
    return swf.ShapePath(start, segs, fill_left=0, fill_right=fill_idx, line=line_idx)


def layer_shape_groups(layer, k, curve_tol, separate=True):
    """Paths of a layer as lists of swf.ShapePath, one list per DefineShape.

    separate=False keeps the whole layer in one shape; True gives each island
    (outer loop with its holes) its own shape, plus one for open stroke paths.
    """
    closed = [close_path(p) for p in layer.paths if p.get("closed", True) and p["segs"]]
    opened = [p for p in layer.paths if not p.get("closed", True) and p["segs"]]
    fill_idx = 1 if layer.fill else 0
    line_idx = 1 if layer.stroke_width > 0 else 0
    oriented = orient_even_odd(closed)
    islands = split_islands(oriented) if separate else ([oriented] if oriented else [])
    groups = [[_shape_path(p, k, curve_tol, fill_idx, line_idx) for p in isl] for isl in islands]
    if line_idx and opened:
        groups.append([swf.ShapePath(*_to_twips(to_quadratic(p, curve_tol), k), line=line_idx) for p in opened])
    return [g for g in groups if g]


def build(interior: InteriorMap) -> bytes:
    k = interior.scale * swf.TWIPS
    tags = [
        # Rockstar's movies: flags 0x02 (gradient textures exported), images as DDS (14)
        swf.exporter_info(f"int{interior.hash}", flags=0x02, bitmap_format=14),
        swf.tag(swf.FILE_ATTRIBUTES, b"\0\0\0\0"),
        swf.tag(swf.SET_BACKGROUND_COLOR, b"\xff\xff\xff"),
    ]
    next_id = 1
    level_sprites = []
    for level in sorted(interior.levels, key=lambda lv: lv.index):
        inner = []
        depth = 1
        for layer in level.layers:
            fills = [layer.fill] if layer.fill else []
            lines = []
            if layer.stroke_width > 0:
                lines = [(max(1, int(round(layer.stroke_width * k))), layer.stroke)]
            for paths in layer_shape_groups(layer, k, interior.curve_tolerance, interior.separate_shapes):
                shape_tag, _ = swf.define_shape(next_id, paths, fills, lines)
                tags.append(shape_tag)
                inner.append(swf.place_object2(depth, char_id=next_id, matrix={}))
                next_id += 1
                depth += 1
        inner += [swf.tag(swf.SHOW_FRAME), swf.tag(swf.END)]
        tags.append(swf.define_sprite(next_id, 1, inner))
        level_sprites.append((next_id, level.clip_name))
        next_id += 1

    alpha = 256 if interior.levels_visible else 0
    inner = []
    for depth, (cid, name) in enumerate(level_sprites, 1):
        inner.append(swf.place_object2(depth, char_id=cid, matrix={},
                                       cxform={"mul_rgba": (256, 256, 256, alpha)}, name=name))
    inner += [swf.tag(swf.SHOW_FRAME), swf.tag(swf.END)]
    interior_id = next_id
    tags.append(swf.define_sprite(interior_id, 1, inner))
    next_id += 1
    if interior.linkage_name:
        tags.append(swf.export_assets([(interior_id, interior.linkage_name)]))

    tags.append(swf.do_action(FRAME1_ACTION))
    for cls, code in ((INTERIORS_CLASS, INTERIORS_INIT), (GAMEINTERFACE_CLASS, GAMEINTERFACE_INIT)):
        tags.append(swf.define_sprite(next_id, 0, [swf.tag(swf.END)]))
        tags.append(swf.export_assets([(next_id, cls)]))
        tags.append(swf.do_init_action(next_id, code))
        next_id += 1
    tags.append(swf.tag(swf.SHOW_FRAME))

    inv = 1.0 / interior.scale
    tags.append(swf.frame_label(interior.label))
    tags.append(swf.place_object2(1, char_id=interior_id, matrix={"sx": inv, "sy": inv},
                                  ratio=1, name="interior"))
    frames = max(2, interior.frame_count)
    tags += [swf.tag(swf.SHOW_FRAME)] * (frames - 1)
    tags.append(swf.tag(swf.END))
    return swf.movie(tags, frames)
