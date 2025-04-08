"""
Geometry package for GTA V Scaleform Minimap Calculator addon.

This package provides geometric primitives and transformation utilities
for processing Blender curves and converting between coordinate systems.
"""

from .base import (
    Vector2, Vector3, GPointF, GSizeF, GRectF, 
    calculate_bounds, EPSILON
)
from .matrix import GMatrix2D, DEG_TO_RAD, RAD_TO_DEG
from .utils import GeometryUtils

__all__ = [
    # Base geometry classes
    'Vector2', 'Vector3', 'GPointF', 'GSizeF', 'GRectF', 'EPSILON',
    
    # Matrix transformations
    'GMatrix2D', 'DEG_TO_RAD', 'RAD_TO_DEG',
    
    # Utility functions and classes
    'GeometryUtils', 'calculate_bounds'
]
