"""
Base geometry classes for GTA V Scaleform Minimap Calculator addon.

This module provides optimized geometric primitives used throughout the addon
for coordinate calculations, transformations, and bounds determination.
"""

import math
import numpy as np
from typing import List, Tuple, Optional, Union
from mathutils import Vector

# Constants for floating point comparisons
EPSILON = 1e-6

class Vector2:
    """
    2D vector representation with x and y components.
    
    This class is used for 2D coordinate operations and transformations
    throughout the minimap calculations.
    """
    
    def __init__(self, x: float, y: float):
        """
        Initialize a new Vector2.
        
        Args:
            x: X-coordinate component
            y: Y-coordinate component
        """
        self.x = x
        self.y = y
    
    def __repr__(self) -> str:
        """String representation of the vector."""
        return f"Vector2({self.x:.2f}, {self.y:.2f})"
    
    def __eq__(self, other) -> bool:
        """Check if two vectors are equal (within epsilon)."""
        if not isinstance(other, Vector2):
            return False
        return (abs(self.x - other.x) < EPSILON and 
                abs(self.y - other.y) < EPSILON)
    
    def __hash__(self) -> int:
        """Hash implementation for dict keys."""
        return hash((round(self.x, 3), round(self.y, 3)))
    
    def length(self) -> float:
        """Calculate vector length (magnitude)."""
        return math.sqrt(self.x * self.x + self.y * self.y)
    
    def length_squared(self) -> float:
        """Calculate squared length (more efficient for comparisons)."""
        return self.x * self.x + self.y * self.y
    
    def distance_to(self, other: 'Vector2') -> float:
        """Calculate distance to another vector."""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)
    
    def normalize(self) -> 'Vector2':
        """Return a normalized version of the vector (unit length)."""
        length = self.length()
        if length < EPSILON:
            return Vector2(0, 0)
        return Vector2(self.x / length, self.y / length)
    
    def dot(self, other: 'Vector2') -> float:
        """Calculate dot product with another vector."""
        return self.x * other.x + self.y * other.y
    
    def perpendicular(self) -> 'Vector2':
        """Return a perpendicular vector (rotated 90 degrees counterclockwise)."""
        return Vector2(-self.y, self.x)
    
    @classmethod
    def from_blender_vector(cls, vector: Vector) -> 'Vector2':
        """
        Create a Vector2 from a Blender Vector.
        
        Args:
            vector: Blender Vector to convert
            
        Returns:
            New Vector2 instance with x, y components from the Blender Vector
        """
        return cls(vector.x, vector.y)


class Vector3:
    """
    3D vector representation with x, y, and z components.
    
    Used for 3D coordinate operations in world-space before conversion
    to Scaleform coordinates.
    """
    
    def __init__(self, x: float, y: float, z: float):
        """
        Initialize a new Vector3.
        
        Args:
            x: X-coordinate component
            y: Y-coordinate component
            z: Z-coordinate component
        """
        self.x = x
        self.y = y
        self.z = z
    
    def __add__(self, other: 'Vector3') -> 'Vector3':
        """Add two vectors."""
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Vector3') -> 'Vector3':
        """Subtract two vectors."""
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float) -> 'Vector3':
        """Multiply vector by scalar."""
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def __eq__(self, other) -> bool:
        """Check if two vectors are equal (within epsilon)."""
        if not isinstance(other, Vector3):
            return False
        return (abs(self.x - other.x) < EPSILON and 
                abs(self.y - other.y) < EPSILON and 
                abs(self.z - other.z) < EPSILON)
    
    def __hash__(self) -> int:
        """Hash implementation for dict keys."""
        return hash((round(self.x, 3), round(self.y, 3), round(self.z, 3)))
    
    def dot(self, other: 'Vector3') -> float:
        """
        Calculate dot product with another vector.
        
        Args:
            other: Vector to calculate dot product with
            
        Returns:
            Dot product value
        """
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def cross(self, other: 'Vector3') -> 'Vector3':
        """
        Calculate cross product with another vector.
        
        Args:
            other: Vector to calculate cross product with
            
        Returns:
            New vector representing the cross product
        """
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )
    
    def length(self) -> float:
        """Calculate vector length (magnitude)."""
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
    
    def length_squared(self) -> float:
        """Calculate squared length (more efficient for comparisons)."""
        return self.x * self.x + self.y * self.y + self.z * self.z
    
    def normalize(self) -> 'Vector3':
        """Return a normalized vector (unit length)."""
        length = self.length()
        if length < EPSILON:
            return Vector3(0, 0, 0)
        inv_length = 1.0 / length
        return Vector3(self.x * inv_length, self.y * inv_length, self.z * inv_length)
    
    def to_vector2(self) -> Vector2:
        """Convert to Vector2 (discarding z component)."""
        return Vector2(self.x, self.y)
    
    def to_blender_vector(self) -> Vector:
        """Convert to a Blender Vector."""
        return Vector((self.x, self.y, self.z))
    
    @classmethod
    def from_blender_vector(cls, vec: Vector) -> 'Vector3':
        """
        Create a Vector3 from a Blender Vector.
        
        Args:
            vec: Blender Vector to convert
            
        Returns:
            New Vector3 instance
        """
        return cls(vec.x, vec.y, vec.z)
    
    def __repr__(self) -> str:
        """String representation of the vector."""
        return f"Vector3({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"


class GPointF:
    """
    2D point representation with floating-point coordinates.
    
    Used primarily for path generation and SVG output coordinates.
    """
    
    def __init__(self, x: float = 0.0, y: float = 0.0):
        """
        Initialize a new GPointF.
        
        Args:
            x: X-coordinate value (default: 0.0)
            y: Y-coordinate value (default: 0.0)
        """
        self.x = x
        self.y = y
    
    def __eq__(self, other) -> bool:
        """Check if two points are equal (within epsilon)."""
        if not isinstance(other, GPointF):
            return False
        return (abs(self.x - other.x) < EPSILON and 
                abs(self.y - other.y) < EPSILON)
    
    def __hash__(self) -> int:
        """Hash implementation for dict keys."""
        return hash((round(self.x, 3), round(self.y, 3)))
    
    def to_vector2(self) -> Vector2:
        """Convert to Vector2."""
        return Vector2(self.x, self.y)
    
    def distance_to(self, other: 'GPointF') -> float:
        """
        Calculate distance to another point.
        
        Args:
            other: Point to calculate distance to
            
        Returns:
            Euclidean distance between points
        """
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)
    
    def __repr__(self) -> str:
        """String representation of the point."""
        return f"GPointF({self.x:.2f}, {self.y:.2f})"


class GSizeF:
    """
    2D size representation with floating-point width and height.
    
    Used for dimensions and scaling operations.
    """
    
    def __init__(self, width: float = 0.0, height: float = 0.0):
        """
        Initialize a new GSizeF.
        
        Args:
            width: Width value (default: 0.0)
            height: Height value (default: 0.0)
        """
        self.width = width
        self.height = height
    
    def area(self) -> float:
        """Calculate area (width × height)."""
        return self.width * self.height
    
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio (width/height)."""
        if abs(self.height) < EPSILON:
            return 0.0
        return self.width / self.height
    
    def __repr__(self) -> str:
        """String representation of the size."""
        return f"GSizeF({self.width:.2f}, {self.height:.2f})"


class GRectF:
    """
    Rectangle representation with floating-point coordinates.
    
    Used for bounds calculations and region operations.
    """
    
    def __init__(self, left: float = 0.0, top: float = 0.0, right: float = 0.0, bottom: float = 0.0):
        """
        Initialize a new GRectF.
        
        Args:
            left: Left boundary (default: 0.0)
            top: Top boundary (default: 0.0)
            right: Right boundary (default: 0.0)
            bottom: Bottom boundary (default: 0.0)
        """
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    def width(self) -> float:
        """Calculate rectangle width."""
        return max(0.0, self.right - self.left)

    def height(self) -> float:
        """Calculate rectangle height."""
        return max(0.0, self.bottom - self.top)

    def size(self) -> GSizeF:
        """Get rectangle size as GSizeF."""
        return GSizeF(self.width(), self.height())

    def center(self) -> GPointF:
        """Calculate rectangle center point."""
        return GPointF((self.left + self.right) * 0.5, (self.top + self.bottom) * 0.5)
    
    def area(self) -> float:
        """Calculate rectangle area."""
        return self.width() * self.height()
    
    def contains_point(self, point: GPointF) -> bool:
        """
        Determine if the rectangle contains a point.
        
        Args:
            point: Point to check
            
        Returns:
            True if the point is within or on the boundary of the rectangle
        """
        return (self.left <= point.x <= self.right and 
                self.top <= point.y <= self.bottom)
    
    def overlaps(self, other: 'GRectF') -> bool:
        """
        Determine if this rectangle overlaps with another.
        
        Args:
            other: Rectangle to check
            
        Returns:
            True if the rectangles overlap
        """
        return (self.left <= other.right and other.left <= self.right and
                self.top <= other.bottom and other.top <= self.bottom)
    
    def union(self, other: 'GRectF') -> 'GRectF':
        """
        Calculate the union of this rectangle with another.
        
        Args:
            other: Rectangle to unite with
            
        Returns:
            New rectangle that contains both input rectangles
        """
        return GRectF(
            min(self.left, other.left),
            min(self.top, other.top),
            max(self.right, other.right),
            max(self.bottom, other.bottom)
        )
    
    def intersection(self, other: 'GRectF') -> 'GRectF':
        """
        Calculate the intersection of this rectangle with another.
        
        Args:
            other: Rectangle to intersect with
            
        Returns:
            New rectangle containing the intersection area, or empty rectangle if no intersection
        """
        left = max(self.left, other.left)
        top = max(self.top, other.top)
        right = min(self.right, other.right)
        bottom = min(self.bottom, other.bottom)
        
        # If there is no intersection, return an empty rectangle
        if left > right or top > bottom:
            return GRectF()
            
        return GRectF(left, top, right, bottom)
    
    def is_valid(self) -> bool:
        """Check if the rectangle is valid (positive width and height)."""
        return self.left <= self.right and self.top <= self.bottom
    
    def normalized(self) -> 'GRectF':
        """Return a normalized rectangle (left ≤ right, top ≤ bottom)."""
        return GRectF(
            min(self.left, self.right),
            min(self.top, self.bottom),
            max(self.left, self.right),
            max(self.top, self.bottom)
        )
    
    def scale(self, sx: float, sy: float = None) -> 'GRectF':
        """
        Scale the rectangle by the given factors.
        
        Args:
            sx: Scale factor for x-axis
            sy: Scale factor for y-axis (defaults to sx if not provided)
            
        Returns:
            New scaled rectangle
        """
        sy = sx if sy is None else sy
        center_x = (self.left + self.right) * 0.5
        center_y = (self.top + self.bottom) * 0.5
        half_width = (self.right - self.left) * 0.5 * sx
        half_height = (self.bottom - self.top) * 0.5 * sy
        
        return GRectF(
            center_x - half_width,
            center_y - half_height,
            center_x + half_width,
            center_y + half_height
        )
    
    def __repr__(self) -> str:
        """String representation of the rectangle."""
        return f"GRectF({self.left:.2f}, {self.top:.2f}, {self.right:.2f}, {self.bottom:.2f})"


def calculate_bounds(points: List[GPointF]) -> GRectF:
    """
    Calculate the bounding rectangle for a list of points.
    
    Args:
        points: List of points to calculate bounds for
        
    Returns:
        Rectangle containing all points
    """
    if not points:
        return GRectF()
    
    # For large sets, using NumPy is faster
    if len(points) > 100:
        x_coords = np.array([p.x for p in points])
        y_coords = np.array([p.y for p in points])
        
        return GRectF(
            float(np.min(x_coords)),
            float(np.min(y_coords)),
            float(np.max(x_coords)),
            float(np.max(y_coords))
        )
    else:
        # For small sets, direct approach is faster
        min_x = min(p.x for p in points)
        min_y = min(p.y for p in points)
        max_x = max(p.x for p in points)
        max_y = max(p.y for p in points)
        
        return GRectF(min_x, min_y, max_x, max_y)