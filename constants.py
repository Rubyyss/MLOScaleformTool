"""
Global constants for GTA V Scaleform Minimap Calculator.

This module defines configuration constants used throughout the addon
for calculations, visualizations, and default values.
"""

import numpy as np

# Mathematical constants
MATH_PI = np.float64(3.14159265358979323846)

# World boundaries for GTA V map (min_x, max_x, min_y, max_y)
WORLD_BOUNDS = (-4000.0, 4000.0, -4000.0, 4000.0)

# Default minimap size in Scaleform coordinates
MINIMAP_SIZE = (300.0, 300.0)

# Default scale factor for SVG output
SVG_SCALE_FACTOR = 1.0

# Visualization colors (RGBA format, values from 0.0 to 1.0)
BOUNDS_COLOR = (0.2, 0.4, 0.8, 0.8)  # Blue for calculated bounds
REAL_BOUNDS_COLOR = (0.8, 0.2, 0.2, 0.8)  # Red for actual bounds
DIRECTION_COLOR = (0.2, 0.8, 0.2, 0.8)  # Green for direction indicator
CENTER_COLOR = (0.8, 0.8, 0.2, 0.8)  # Yellow for center point
GRID_COLOR = (0.5, 0.5, 0.5, 0.3)  # Gray for grid
AXIS_X_COLOR = (0.9, 0.2, 0.2, 0.8)  # Red for X axis
AXIS_Y_COLOR = (0.2, 0.9, 0.2, 0.8)  # Green for Y axis
AXIS_Z_COLOR = (0.2, 0.2, 0.9, 0.8)  # Blue for Z axis
EXPORT_DIRECTION_COLOR = (1.0, 0.5, 0.0, 0.8)  # Orange for export direction

# Line width for visualizations
LINE_WIDTH = 2.0

# Performance optimization constants
OPTIMIZATION_THRESHOLD = 100  # Threshold number of points for applying optimizations
BEZIER_RESOLUTION = 12  # Number of segments to approximate Bezier curves

# Fill color presets
FILL_PRESETS = {
    "ACCESSIBLE": (0.6, 0.6, 0.6, 1.0),  # Grey for accessible zones
    "ENTITIES": (0.435, 0.435, 0.435, 1.0),  # Darker grey for entity objects
    "NEXT_AREA": (1.0, 1.0, 1.0, 1.0),  # White for next area markers
    "LIMITS": (0.25, 0.25, 0.25, 1.0),  # Dark grey for area limits
}

# Cache configuration
DEFAULT_CACHE_LIFETIME = 300  # 5 minutes in seconds
MAX_CACHE_SIZE = 100  # Maximum number of elements in default caches

# Version information
ADDON_VERSION = (2, 2, 1)
BLENDER_MIN_VERSION = (4, 0, 0)

# Debug settings
DEBUG_MODE = False  # Set to True to enable debug output
