# MLOScaleformTool v1.10

A Blender extension that turns a 3D interior (MLO) into a GTA V interior minimap:
**3D → 2D curves → `int<hash>.gfx`** (Scaleform). It writes the `.gfx` directly, with no Flash or JPEXS involved, and it
can also import existing `.gfx` files as editable curves.

- Blender 4.2 or later (tested on 5.2).
- Sidebar (N) tab: **MLOScaleformTool**.

---

## Installation

Drag `MLOScaleformTool-v1.10.0.zip` into Blender, or use *Edit → Preferences → Get Extensions → Install from Disk*.

Sollumz is optional. When it is enabled, extra buttons read the MLO (name, floors from `floor_id`, clipping to rooms).

---

## Workflow

1. **Start the minimap:** *Create Minimap Collection* creates the `GFX Map` collection with one sub-collection per
   floor. You can also start from *Or Import an Existing GFX*.
2. **MLO name:** the interior archetype name, or its hash directly (`123456`, `0x…`, `int123456`).
   The file is named `int<joaat(name)>.gfx`, and the panel shows the hash, the file name and the `INT<hash>` label.
   With Sollumz, the eyedropper takes the name of the selected MLO.
3. **MLO Origin:** an object at the interior's origin, with the entity's position and rotation. Empty = Blender's world
   origin is the MLO origin. Everything is exported in MLO-local metres.
4. **Levels:** one floor per `level_<n>` clip (negative floors = `level_u<n>`), with its floor height (Z) and height (H).
   *Detect Floors* finds them in the selected geometry; *From MLO Rooms* (Sollumz) creates one per `floor_id`.
5. **3D to Curves:** select the geometry (meshes, curves, text…) and press *3D to Curves*. It creates a floor curve and,
   optionally, an obstacles curve per floor. *Import Collision (.ybn.xml)* loads the MLO collision exported as XML
   (CodeWalker / Sollumz), ready to convert.
6. **Style and layers:** set colours, draw order and which curves are exported (see below).
7. **Preview:** renders the floor the way the minimap draws it.
8. **Export GFX:** writes `int<hash>.gfx` to the output folder.

---

## Panels

### 3D to Curves

| Option | What it does |
|---|---|
| **Mode** | *Floor*: up-facing faces near each floor height (walkable area). *Footprint*: everything between the floor and the floor above, seen from the top. |
| **Snap to Geometry** | Moves the outline vertices onto the real mesh corners and edges (exact shape; 0 mm error in the tests). |
| **Resolution** | Raster cell size that decides which areas are filled (0.05 m by default). |
| **Simplify** | Allowed deviation from the real outline; raise it to drop small details. |
| **Min Area** | Drops islands and holes smaller than this (m²). |
| **Close Gaps / Remove Thin** | Fills cracks between floor pieces and removes thin slivers (wall tops, skirting). |
| **Floor Tolerance / Max Slope** | Floor mode: height margin and steepest slope that count as floor. |
| **Obstacles Layer** | A darker layer over the floor. *Obstacles*: footprint of everything between Min and Max above the floor (Rockstar style: furniture, counters). *Wall Cut*: horizontal cut through the walls at *Cut Height*. |
| **Clip to MLO Rooms** | (Sollumz) Keeps only what lies inside the rooms of each `floor_id`. |
| **Replace Previous** | Deletes the curves generated before for the same floors. |

### Curve Style

For the active curve: floor, draw order, colour preset, fill and stroke (width in metres).
*Apply Style to Selected* copies the floor and style to the other selected curves.

Presets (values from Rockstar's retail GFX `int3661284625`):

| Preset | Colour |
|---|---|
| Floor | 150, 150, 150 |
| Obstacles / Entities | 112, 112, 112 |
| Door / Next Area | 245, 245, 245 |
| Limits | 63, 63, 63 |

Rockstar does not draw walls: furniture goes in grey 112.

### Layers

Lists the shapes of the selected floor, top first. You can move them up and down the draw order, include or exclude each
one from the export, add a *New Shape* (a 4 × 4 m square to edit), use *Assign Selected* (puts curves or flat meshes on
the floor) and *Remove from Minimap* (takes the shape out without deleting the object).

### Preview

Builds the GFX in memory and draws the floor like the minimap does: size, background (the retail minimap colour
56, 74, 80 by default), 1 m grid (stronger every 5 m), a yellow cross at the MLO origin and the floor below as a ghost.
With *Auto Refresh* it updates when the curves change.

### Export

| Option | What it does |
|---|---|
| **Export** | *GFX Map Collection* (every curve in the collection) or *Selected*. |
| **Precision** | Internal scale: x1 … x32 (x32 by default = 1 twip of 1.56 mm). Powers of two keep the 1/scale matrix exact. |
| **Curve Tolerance** | Maximum error when Blender's Bézier curves become Flash quadratic curves. |
| **Separate Shapes** | Writes every island (outline + its holes) as its own shape, like Flash does. |
| **Levels Visible** | Exports the floor clips with alpha 100 (handy to view them in JPEXS); the game sets the alpha itself. |

*Import GFX* opens an interior `.gfx`/`.swf` as editable curves.

### GTA Measurements

Bounds and size of each floor in metres and in Flash pixels, the placement the game uses, and the *Copy Script Line*
button, which copies the `SetRadarAsInteriorThisFrame(hash, x, y, heading, level)` call to place the interior manually
from a script.

---

## How the game uses it

Verified in the source code (`frontend/MiniMapRenderThread.cpp`, `UpdateInterior`) and in game:

- The game loads the `INT<hash>` movie (hash = joaat of the interior archetype name) and calls
  `gotoAndStop("INT<hash>")`.
- It takes the child clip `interior` and places it at `(pos.x, -pos.y)` of the interior instance, with rotation
  `-heading` and 100 % scale.
- It shows the current floor by setting alpha 100 on `interior.level_<n>` (or `level_u<n>`) and alpha 0 on the
  previous one.
- The minimap layer uses **1 px = 1 m** (same as the blips), so the content is drawn in MLO-local metres with Y
  flipped. The add-on stores the shapes `scale` times bigger and scales the `interior` clip by 1/scale.
- The first tag of the file must be ExporterInfo (tag 1000), with version 0x3xx.

Tested in game with a 20 × 20 m calibration MLO: the player arrow matches to the centimetre at the centre, on an edge
and at the four corners.

### Using it in FiveM

Put `int<hash>.gfx` in a resource's `stream` folder (for example `stream/minimap/`) and restart the resource. The
interior must exist in the game with that archetype name for the minimap to load it when you enter.

---

## Changelog

- **1.10.0:** current version, released as **MLOScaleformTool**.

## License

MIT © 2025-2026 rubyys
