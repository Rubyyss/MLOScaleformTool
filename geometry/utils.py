"""
Geometry utility functions for GTA V Scaleform Minimap Calculator.

This module provides utility functions for geometry operations,
transformations, and coordinate system conversions.
"""

from typing import List, Tuple, Any, Optional, Dict
from ..geometry import GPointF, GRectF


class GeometryUtils:
    """
    Utility class for geometry operations.

    This class provides static methods for various geometry calculations,
    coordinate transformations, and vector operations.
    """

    @staticmethod
    def create_bounds_coordinates(bounds):
        """
        Create coordinates for drawing a rectangle from bounds.

        Args:
            bounds: GRectF bounds object

        Returns:
            List of 3D coordinates for the rectangle vertices
        """
        return [
            (bounds.left, bounds.top, 0),
            (bounds.right, bounds.top, 0),
            (bounds.right, bounds.bottom, 0),
            (bounds.left, bounds.bottom, 0),
            (bounds.left, bounds.top, 0),
        ]

    @staticmethod
    def create_arrow_coordinates(center, direction, size=1.0, head_size=0.3):
        """
        Create coordinates for an arrow pointing in the specified direction.

        Args:
            center: Origin point for the arrow
            direction: Direction vector (will be normalized)
            size: Length of the arrow
            head_size: Size of the arrow head relative to arrow length

        Returns:
            List of 3D coordinates for drawing the arrow
        """
        # Normalize direction
        dir_len = (direction.x**2 + direction.y**2) ** 0.5
        if dir_len < 0.0001:
            # Avoid division by zero
            dir_x, dir_y = 0, -1
        else:
            dir_x, dir_y = direction.x / dir_len, direction.y / dir_len

        # Calculate perpendicular vector
        perp_x, perp_y = -dir_y, dir_x

        # Start and end points of main line
        start_x, start_y = center.x, center.y
        end_x, end_y = center.x + dir_x * size, center.y + dir_y * size

        # Arrow head points
        head_left_x = end_x - dir_x * size * head_size + perp_x * size * head_size * 0.5
        head_left_y = end_y - dir_y * size * head_size + perp_y * size * head_size * 0.5

        head_right_x = (
            end_x - dir_x * size * head_size - perp_x * size * head_size * 0.5
        )
        head_right_y = (
            end_y - dir_y * size * head_size - perp_y * size * head_size * 0.5
        )

        # Create coordinates for lines (main line + 2 arrow head lines)
        coords = [
            # Main line
            (start_x, start_y, 0),
            (end_x, end_y, 0),
            # Left arrow head line
            (end_x, end_y, 0),
            (head_left_x, head_left_y, 0),
            # Right arrow head line
            (end_x, end_y, 0),
            (head_right_x, head_right_y, 0),
        ]

        return coords

    @staticmethod
    def hex_from_rgba(rgba):
        """
        Convert RGBA color to hex format.

        Args:
            rgba: Tuple of (r, g, b, a) values in the range 0.0-1.0

        Returns:
            Hex color string (#RRGGBB)
        """
        r, g, b = [int(c * 255) for c in rgba[:3]]
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def format_coordinate(value, precision, use_comma):
        """
        Format a coordinate value with specified precision and separator.

        Args:
            value: Coordinate value to format
            precision: Number of decimal places
            use_comma: Whether to use comma as decimal separator

        Returns:
            Formatted coordinate string
        """
        formatted = f"{value:.{precision}f}"
        if use_comma:
            formatted = formatted.replace(".", ",")
        return formatted

    @staticmethod
    def distance(point1, point2):
        """Calculate Euclidean distance between two points."""
        dx = point2.x - point1.x
        dy = point2.y - point1.y
        return (dx**2 + dy**2) ** 0.5

    @staticmethod
    def simplify_polyline(points, tolerance=0.1):
        """
        Simplify a polyline using the Ramer-Douglas-Peucker algorithm.

        Args:
            points: List of points to simplify
            tolerance: Simplification tolerance (higher = more simplified)

        Returns:
            Simplified list of points
        """
        if len(points) <= 2:
            return points

        # Find the point with the maximum distance
        max_dist = 0
        index = 0
        for i in range(1, len(points) - 1):
            # Calculate distance from point to line
            dist = GeometryUtils._point_line_distance(points[i], points[0], points[-1])
            if dist > max_dist:
                max_dist = dist
                index = i

        # If max distance is greater than tolerance, recursively simplify
        if max_dist > tolerance:
            # Recursive call
            first_half = GeometryUtils.simplify_polyline(points[: index + 1], tolerance)
            second_half = GeometryUtils.simplify_polyline(points[index:], tolerance)

            # Concat the two arrays
            return first_half[:-1] + second_half
        else:
            return [points[0], points[-1]]

    @staticmethod
    def _point_line_distance(point, line_start, line_end):
        """
        Calculate the perpendicular distance from a point to a line.

        Args:
            point: Point to calculate distance for
            line_start: Start point of the line
            line_end: End point of the line

        Returns:
            Perpendicular distance from point to line
        """
        if line_start.x == line_end.x and line_start.y == line_end.y:
            return GeometryUtils.distance(point, line_start)

        # Calculate the perpendicular distance
        num = abs(
            (line_end.y - line_start.y) * point.x
            - (line_end.x - line_start.x) * point.y
            + line_end.x * line_start.y
            - line_end.y * line_start.x
        )

        den = (
            (line_end.y - line_start.y) ** 2 + (line_end.x - line_start.x) ** 2
        ) ** 0.5

        return num / den

    @staticmethod
    def normalize_points(points, origin=None):
        """
        Normalize points relative to an origin.

        Args:
            points: List of points to normalize
            origin: Origin point (None for center of bounds)

        Returns:
            Normalized points
        """
        if not points:
            return []

        # Calculate bounds if no origin specified
        if origin is None:
            from ..geometry import calculate_bounds

            bounds = calculate_bounds(points)
            origin = bounds.center()

        # Normalize points relative to origin
        return [GPointF(p.x - origin.x, p.y - origin.y) for p in points]

    @staticmethod
    def rotate_point(point, angle, center=None):
        """
        Rotate a point around a center by a given angle.

        Args:
            point: Point to rotate
            angle: Angle in radians
            center: Center of rotation (None for origin)

        Returns:
            Rotated point
        """
        import math

        # Default to origin if no center specified
        if center is None:
            center = GPointF(0, 0)

        # Translate point to origin
        translated_x = point.x - center.x
        translated_y = point.y - center.y

        # Rotate
        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)

        rotated_x = translated_x * cos_angle - translated_y * sin_angle
        rotated_y = translated_x * sin_angle + translated_y * cos_angle

        # Translate back
        return GPointF(rotated_x + center.x, rotated_y + center.y)
