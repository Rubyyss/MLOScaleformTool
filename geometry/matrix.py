"""
Matrix transformation classes for GTA V Scaleform Minimap Calculator.

This module provides matrix operations for coordinate transformations
between different coordinate systems (Blender, Scaleform, GTA V world).
"""

import math
import numpy as np
from typing import List, Tuple, Optional, Union
from .base import GPointF, GRectF, EPSILON

# Constants for angle conversions
MATH_PI = np.float64(3.14159265358979323846)
DEG_TO_RAD = MATH_PI / 180.0
RAD_TO_DEG = 180.0 / MATH_PI


class GMatrix2D:
    """
    Optimized 2D transformation matrix for coordinate conversions.

    This class provides methods for 2D affine transformations
    including scaling, rotation, and translation operations.
    """

    __slots__ = ["M"]

    # Identity matrix for reference
    IDENTITY = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)

    def __init__(self):
        """Initialize as identity matrix."""
        self.M = np.copy(self.IDENTITY)

    def append_scaling(self, sx: float, sy: float = None) -> "GMatrix2D":
        """Apply a scaling transformation to the matrix."""
        sy = sx if sy is None else sy
        # Use np.matmul for matrix multiplication (faster)
        scale = np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]], dtype=np.float32)
        self.M = np.matmul(np.vstack([self.M, [0, 0, 1]]), scale)[:2, :]
        return self

    def append_translation(self, tx: float, ty: float) -> "GMatrix2D":
        """Apply a translation transformation to the matrix."""
        translation = np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1]], dtype=np.float32)
        self.M = np.matmul(np.vstack([self.M, [0, 0, 1]]), translation)[:2, :]
        return self

    def append_rotation(self, angle_rad: float) -> "GMatrix2D":
        """Apply a rotation transformation to the matrix."""
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        rotation = np.array(
            [[cos_a, -sin_a, 0], [sin_a, cos_a, 0], [0, 0, 1]], dtype=np.float32
        )
        self.M = np.matmul(np.vstack([self.M, [0, 0, 1]]), rotation)[:2, :]
        return self

    def rotate_degrees(self, angle_deg: float) -> "GMatrix2D":
        """Apply a rotation transformation to the matrix in degrees."""
        return self.append_rotation(angle_deg * DEG_TO_RAD)

    def transform(self, point: GPointF) -> GPointF:
        """Transform a point with this matrix."""
        # Use direct multiplication instead of matrix ops for better performance
        x = self.M[0, 0] * point.x + self.M[0, 1] * point.y + self.M[0, 2]
        y = self.M[1, 0] * point.x + self.M[1, 1] * point.y + self.M[1, 2]
        return GPointF(x, y)

    def transform_points(self, points: List[GPointF]) -> List[GPointF]:
        """Transform multiple points in a batch operation."""
        if not points:
            return []

        # Convert points to a matrix for batch transformation
        points_array = np.array([[p.x, p.y, 1] for p in points], dtype=np.float32)

        # Transform all points at once
        transformed = np.dot(points_array, np.vstack([self.M, [0, 0, 1]]).T)

        # Convert back to GPointF
        return [GPointF(p[0], p[1]) for p in transformed]

    def transform_rect(self, rect: GRectF) -> GRectF:
        """Transform a rectangle with this matrix."""
        # Convert the four corners
        corners = [
            GPointF(rect.left, rect.top),
            GPointF(rect.right, rect.top),
            GPointF(rect.right, rect.bottom),
            GPointF(rect.left, rect.bottom),
        ]

        transformed = self.transform_points(corners)

        # Find the rectangle that contains all transformed points
        min_x = min(p.x for p in transformed)
        min_y = min(p.y for p in transformed)
        max_x = max(p.x for p in transformed)
        max_y = max(p.y for p in transformed)

        return GRectF(min_x, min_y, max_x, max_y)

    def invert(self) -> bool:
        """
        Invert the matrix in-place.

        Returns:
            True if inversion was successful, False if the matrix is singular
        """
        # Add the missing row to make a 3x3 matrix
        full_matrix = np.vstack([self.M, [0, 0, 1]])

        try:
            # Calculate the inverse
            inverse = np.linalg.inv(full_matrix)
            # Extract the first two rows
            self.M = inverse[:2, :]
            return True
        except np.linalg.LinAlgError:
            # Matrix is not invertible, return identity
            result.M = np.copy(self.IDENTITY)

        return result

    def copy(self) -> "GMatrix2D":
        """Create a copy of this matrix."""
        result = GMatrix2D()
        result.M = np.copy(self.M)
        return result

    def set_identity(self) -> "GMatrix2D":
        """Reset the matrix to identity."""
        self.M = np.copy(self.IDENTITY)
        return self

    def determinant(self) -> float:
        """Calculate the determinant of the 2x2 matrix (ignoring translation)."""
        return self.M[0, 0] * self.M[1, 1] - self.M[0, 1] * self.M[1, 0]

    def get_scale(self) -> Tuple[float, float]:
        """Extract scale factors from the matrix."""
        # Scale is given by the magnitude of the columns
        scale_x = math.sqrt(self.M[0, 0] ** 2 + self.M[1, 0] ** 2)
        scale_y = math.sqrt(self.M[0, 1] ** 2 + self.M[1, 1] ** 2)
        return (scale_x, scale_y)

    def get_translation(self) -> Tuple[float, float]:
        """Extract translation components from the matrix."""
        return (self.M[0, 2], self.M[1, 2])

    def get_rotation(self) -> float:
        """Extract rotation angle from the matrix in radians."""
        # Assuming no skew, only rotation and uniform scale
        return math.atan2(self.M[1, 0], self.M[0, 0])

    def get_rotation_degrees(self) -> float:
        """Extract rotation angle from the matrix in degrees."""
        return self.get_rotation() * RAD_TO_DEG

    def to_array(self) -> np.ndarray:
        """Convert the matrix to a 3x3 NumPy array."""
        return np.vstack([self.M, [0, 0, 1]])

    @classmethod
    def from_array(cls, array: np.ndarray) -> "GMatrix2D":
        """Create a matrix from a 3x3 or 2x3 NumPy array."""
        result = cls()
        if array.shape == (3, 3):
            result.M = array[:2, :]
        elif array.shape == (2, 3):
            result.M = array
        else:
            raise ValueError(f"Incompatible matrix shape: {array.shape}")
        return result

    @classmethod
    def create_translation(cls, tx: float, ty: float) -> "GMatrix2D":
        """Create a translation matrix."""
        result = cls()
        result.M[0, 2] = tx
        result.M[1, 2] = ty
        return result

    @classmethod
    def create_scale(cls, sx: float, sy: float = None) -> "GMatrix2D":
        """Create a scaling matrix."""
        sy = sx if sy is None else sy
        result = cls()
        result.M[0, 0] = sx
        result.M[1, 1] = sy
        return result

    @classmethod
    def create_rotation(cls, angle_rad: float) -> "GMatrix2D":
        """Create a rotation matrix."""
        result = cls()
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        result.M[0, 0] = cos_a
        result.M[0, 1] = -sin_a
        result.M[1, 0] = sin_a
        result.M[1, 1] = cos_a
        return result

    @classmethod
    def create_rotation_degrees(cls, angle_deg: float) -> "GMatrix2D":
        """Create a rotation matrix with angle in degrees."""
        return cls.create_rotation(angle_deg * DEG_TO_RAD)

    def __mul__(self, other: "GMatrix2D") -> "GMatrix2D":
        """Multiply this matrix by another (composition of transformations)."""
        result = GMatrix2D()
        # Add the missing row to make 3x3 matrices
        m1 = np.vstack([self.M, [0, 0, 1]])
        m2 = np.vstack([other.M, [0, 0, 1]])
        # Multiply
        product = np.matmul(m1, m2)
        # Extract the first two rows
        result.M = product[:2, :]
        return result

    def __eq__(self, other) -> bool:
        """Compare if two matrices are equal."""
        if not isinstance(other, GMatrix2D):
            return False
        # Compare with tolerance for floating point errors
        return np.allclose(self.M, other.M, rtol=EPSILON, atol=EPSILON)

    def __repr__(self) -> str:
        """String representation of the matrix."""
        return (
            f"GMatrix2D([{self.M[0, 0]:.2f}, {self.M[0, 1]:.2f}, {self.M[0, 2]:.2f}], "
            f"[{self.M[1, 0]:.2f}, {self.M[1, 1]:.2f}, {self.M[1, 2]:.2f}])"
        )
