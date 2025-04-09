# 🗺️ GTA V Scaleform Minimap Calculator – Blender Add-on

**Version:** 2.2.1  
**Blender Compatibility:** 4.4.0+  
**Author:** rubyys  

The **GTA V Scaleform Minimap Calculator** is a powerful Blender add-on designed to export Blender curves as SVGs for GTA V Scaleform minimaps. It handles coordinate conversion between Blender, GTA V world, and Scaleform coordinate systems, offering an accurate and efficient workflow for minimap creation.

---

## ✨ Key Features

- ✅ Export Blender curve objects to SVG format
- 🔄 Convert coordinates between Blender, world, and Scaleform systems
- 🎨 Support for individual fill/stroke settings per curve
- ⚙️ Customizable SVG export settings
- 🚀 Caching system for improved performance
- 📏 Accurate position and dimension calculations

---

## 🧩 Installation

1. Download the add-on ZIP file.
2. Open **Blender** and go to `Edit > Preferences > Add-ons`.
3. Click **Install...** and select the ZIP file.
4. Enable the add-on: look for **Import-Export: MLOScaleformTools** and check the box.

---

## 🧭 User Interface

A new **"Scaleform"** tab will appear in the 3D Viewport sidebar, containing several panels:

### 📐 Main Panel

Core functions for minimap calculation:

- **Calculate Dimensions:** Analyze selected curves to get bounds and center points
- **Calculate Position:** Compute the Scaleform position
- **Export SVG:** Save the curves as an SVG file

After calculating, it will display:

- **Dimensions:** Original units and scaled SVG size
- **Scaleform Center:** Center point in Scaleform coordinates
- **Scaleform Position:** Final calculated placement

---

### ⚙️ Export Settings Panel

Customize how your SVG is generated:

- **SVG Scale:** Scale factor for SVG output
- **Coordinate Precision:** Decimal places for exported coordinates
- **Curve Resolution:** Approximation detail level for curves
- **Center at Origin:** Option to center the SVG output
- **Use Comma as Decimal:** Locale-friendly formatting

#### Fill & Stroke Options

- **Color Preset:** Predefined styles for different types of areas
- **Fill Settings:** Enable/disable fills, color picker
- **Stroke Settings:** Enable/disable outlines, color & width
- **Marker Settings:** Optional markers to indicate positions

---

### 🌍 Minimap Settings Panel

Configure the reference bounds and dimensions for Scaleform:

- **World Boundaries:** Choose between default GTA V world bounds or custom values
- **Minimap Dimensions:** Define minimap width and height in Scaleform units

---

## 🔄 Workflow

1. **Select Curves:** Pick one or more curve objects in your scene
2. **Calculate Dimensions:** Analyze their size and center
3. **Adjust Settings:** Tweak SVG/export parameters as needed
4. **Apply Fill Settings:** Optional fill/stroke customization
5. **Calculate Position:** Get precise Scaleform coordinates
6. **Export SVG:** Save your curves in a minimap-ready format

---

## 💡 Tips for Best Results

- Use the **MLO floor** as a reference for positioning
- Multiple curves can be selected and exported together
- Curves can have **individual fill/stroke styles**
- Some MLOs require **180° rotation** for correct alignment
- Use **dissolve** to smooth out jagged curve points
- For large MLOs, **adjust the SVG scale** appropriately
- The **center point** and direction are key for proper placement

---

## 🧠 Technical Details

### Coordinate Systems

The add-on converts between:

- **Blender Coordinates:** Standard 3D view space
- **World Coordinates:** GTA V world positioning
- **Scaleform Coordinates:** 2D minimap space

> In Blender:  
> - Y → Scaleform X  
> - -Z → Scaleform Y  
> with appropriate scale and origin adjustment.

---

### 🖼️ SVG Export

The exported file includes:

- SVG path data from curves
- Optional fill/stroke properties
- Optional reference markers

**Export Process:**

1. Extract curve data from Blender
2. Normalize scale and origin
3. Convert to SVG path format
4. Apply visual styles
5. Insert optional markers

---

## 🛠️ Architecture

Organized into several functional packages:

### `core/`
- `calculator.py` – Coordinate system conversions
- `processor.py` – Curve processing and analysis
- `exporter.py` – SVG generation

### `geometry/`
- `base.py` – Vector, point, rectangle classes
- `matrix.py` – Transformations
- `utils.py` – Geometry utilities

### `ui/`
- `properties.py` – Property declarations
- `panels.py` – UI layout
- `operators.py` – Button logic and actions

### `utils/`
- `cache.py` – Calculation caching
- `helpers.py` – Helper functions

---

## ⚡ Performance Tips

- Uses a **caching system** to skip redundant calculations
- Processes only **selected/necessary curves**
- Built with **NumPy** for heavy data sets
- Curve simplification reduces SVG size
- Efficient **real-time updates** after changes

---

## 🧩 Troubleshooting

| Problem                      | Solution |
|-----------------------------|----------|
| No curves show on export    | Ensure you selected valid curve objects |
| SVG size looks off          | Adjust the **SVG Scale** setting |
| MLO appears rotated         | Try rotating the curves 180° |
| Performance is sluggish     | Lower the **Curve Resolution** |

---

## 🙌 Acknowledgments

This add-on was created to simplify the workflow for building GTA V minimaps with Scaleform, solving common issues with coordinate systems, scaling, and positioning.

---
