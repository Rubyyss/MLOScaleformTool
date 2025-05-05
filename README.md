# GTA V Scaleform Minimap Calculator

A Blender addon for creating GTA V minimap layouts from Blender curves.

## Overview

This addon allows you to convert Blender curve objects into SVG files suitable for use in GTA V Scaleform minimap creation. It provides tools for:

- Calculating dimensions and coordinates
- Converting between Blender, SVG, and Scaleform coordinate systems
- Visualizing curves with proper orientation
- Exporting properly formatted SVG files
- Applying fill and stroke settings to curves

## Installation

1. Download the latest release ZIP file from the releases section
2. In Blender, go to Edit > Preferences > Add-ons
3. Click "Install..." and select the downloaded ZIP file
4. Enable the "GTA V Scaleform Minimap Calculator" addon

## Project Structure

The addon is organized into logical modules:

```
mlo_scaleform_tool/
├── __init__.py                  # Main initialization
├── constants.py                 # Global constants
├── geometry/                    # Geometric primitives and transformations
│   ├── __init__.py
│   ├── base.py                  # Base geometry classes (Point, Rect, Vector)
│   ├── matrix.py                # Matrix transformation utilities
│   └── utils.py                 # Geometry utility functions
├── utils/                       # Utility functions
│   ├── __init__.py
│   ├── cache.py                 # Caching system for performance
│   └── helpers.py               # Helper functions
├── core/                        # Core calculation functionality
│   ├── __init__.py
│   ├── calculator.py            # Coordinate calculation system
│   ├── processor.py             # Curve data processing
│   └── exporter.py              # SVG export functionality
└── ui/                          # Blender interface components
    ├── __init__.py
    ├── properties.py            # UI-related properties
    ├── operators.py             # Operator definitions
    ├── panels.py                # UI panels
    └── visualization.py         # 3D viewport visualization
```

## Usage

### Basic Workflow

1. Create or import curves that represent your minimap layout in Blender
2. Select the curves you want to include in the minimap
3. Open the "GTA V Scaleform Minimap" panel in the 3D View sidebar (N panel)
4. Click "Calculate Dimensions" to analyze the selected curves
5. Review the calculated dimensions and Scaleform center coordinates
6. (Optional) Apply fill and stroke settings to your curves
7. Click "Export SVG" to save the SVG file for use in GTA V

### Advanced Features

#### Visualization

The addon includes visualization tools to help understand how your curves will be exported:

- Toggle visualization to see the bounds, center point, and axes
- Display a reference grid for better positioning
- View direction indicators showing the export orientation

#### Coordinate Systems

The addon handles the conversion between three coordinate systems:

1. **Blender**: The 3D coordinate system used in Blender
2. **SVG**: The 2D coordinate system used in SVG files (origin at top-left)
3. **Scaleform**: The coordinate system used in GTA V Scaleform (origin at center)

#### Fill and Stroke Settings

Apply different fill and stroke settings to your curves:

- Choose from predefined color presets for different area types
- Apply custom colors, opacity, and stroke widths
- Customize each curve individually or apply settings to multiple curves at once

## Performance Optimization

The addon includes a caching system to improve performance when working with complex curves:

- Calculation results are cached to avoid redundant processing
- Geometry processing is optimized for large curve sets
- Visualizations are efficiently rendered using GPU acceleration

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Credits

Developed by Ruby