"""
Geometry utility functions for GTA V Scaleform Minimap Calculator addon.

This module provides various geometric algorithms and helpers for
curve processing, point manipulation, and path generation.
"""

import math
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from .base import GPointF, GRectF, EPSILON

class GeometryUtils:
    """
    Utility class for geometric operations.
    
    Provides static methods for common geometric algorithms used in path
    processing, curve generation, and coordinate transformations.
    """
    
    @staticmethod
    def cubic_bezier_point(p0: GPointF, p1: GPointF, p2: GPointF, p3: GPointF, t: float) -> GPointF:
        """
        Calculate a point on a cubic Bezier curve.
        
        Args:
            p0: Start point
            p1: First control point
            p2: Second control point
            p3: End point
            t: Curve parameter (0-1)
            
        Returns:
            Point on the curve for the given t value
        """
        t2 = t * t
        t3 = t2 * t
        mt = 1 - t
        mt2 = mt * mt
        mt3 = mt2 * mt
        
        # Apply cubic Bezier formula
        return GPointF(
            mt3 * p0.x + 3 * mt2 * t * p1.x + 3 * mt * t2 * p2.x + t3 * p3.x,
            mt3 * p0.y + 3 * mt2 * t * p1.y + 3 * mt * t2 * p2.y + t3 * p3.y
        )
    
    @staticmethod
    def approximate_bezier_length(p0: GPointF, p1: GPointF, p2: GPointF, p3: GPointF, segments: int = 10) -> float:
        """
        Approximate the length of a cubic Bezier curve.
        
        Args:
            p0: Start point
            p1: First control point
            p2: Second control point
            p3: End point
            segments: Number of segments for approximation
            
        Returns:
            Approximate length of the curve
        """
        length = 0.0
        prev_point = p0
        
        for i in range(1, segments + 1):
            t = i / segments
            curr_point = GeometryUtils.cubic_bezier_point(p0, p1, p2, p3, t)
            length += prev_point.distance_to(curr_point)
            prev_point = curr_point
            
        return length
    
    @staticmethod
    def simplify_polyline(points: List[GPointF], tolerance: float = 1.0) -> List[GPointF]:
        """
        Simplify a polyline using the Douglas-Peucker algorithm.
        
        This algorithm reduces the number of points in a curve while
        maintaining its shape within a specified tolerance.
        
        Args:
            points: List of points to simplify
            tolerance: Maximum distance tolerance for simplification
            
        Returns:
            Simplified list of points
        """
        if len(points) <= 2:
            return points
            
        # Find the point farthest from the line
        max_dist = 0
        index = 0
        
        # Create the line between the endpoints
        line_start = points[0]
        line_end = points[-1]
        
        for i in range(1, len(points) - 1):
            # Calculate perpendicular distance
            dist = GeometryUtils.perpendicular_distance(points[i], line_start, line_end)
            
            if dist > max_dist:
                max_dist = dist
                index = i
                
        # If maximum distance is greater than tolerance, split and continue
        if max_dist > tolerance:
            # Recursively simplify the two parts
            first_part = GeometryUtils.simplify_polyline(points[:index + 1], tolerance)
            second_part = GeometryUtils.simplify_polyline(points[index:], tolerance)
            
            # Join the results (avoid duplicating the split point)
            return first_part[:-1] + second_part
        else:
            # All points are within tolerance, keep only the endpoints
            return [points[0], points[-1]]
    
    @staticmethod
    def perpendicular_distance(point: GPointF, line_start: GPointF, line_end: GPointF) -> float:
        """
        Calculate the perpendicular distance from a point to a line.
        
        Args:
            point: Point to calculate distance for
            line_start: Line start point
            line_end: Line end point
            
        Returns:
            Perpendicular distance
        """
        if line_start.x == line_end.x and line_start.y == line_end.y:
            # Line is a point, return distance to that point
            return point.distance_to(line_start)
            
        # Calculate perpendicular distance
        dx = line_end.x - line_start.x
        dy = line_end.y - line_start.y
        
        # Squared line length
        line_length_squared = dx * dx + dy * dy
        
        # Projection of point onto line
        t = ((point.x - line_start.x) * dx + (point.y - line_start.y) * dy) / line_length_squared
        
        # Limit t to line segment
        t = max(0, min(1, t))
        
        # Closest point on line
        closest_x = line_start.x + t * dx
        closest_y = line_start.y + t * dy
        
        # Distance to closest point
        return math.sqrt((point.x - closest_x)**2 + (point.y - closest_y)**2)
    
    @staticmethod
    def angle_between_points(p1: GPointF, p2: GPointF) -> float:
        """
        Calculate angle between two points (in radians).
        
        Args:
            p1: First point
            p2: Second point
            
        Returns:
            Angle in radians
        """
        return math.atan2(p2.y - p1.y, p2.x - p1.x)
    
    @staticmethod
    def midpoint(p1: GPointF, p2: GPointF) -> GPointF:
        """
        Calculate midpoint between two points.
        
        Args:
            p1: First point
            p2: Second point
            
        Returns:
            Midpoint
        """
        return GPointF((p1.x + p2.x) * 0.5, (p1.y + p2.y) * 0.5)
    
    @staticmethod
    def interpolate(p1: GPointF, p2: GPointF, t: float) -> GPointF:
        """
        Linearly interpolate between two points.
        
        Args:
            p1: Start point
            p2: End point
            t: Interpolation factor (0-1)
            
        Returns:
            Interpolated point
        """
        return GPointF(
            p1.x + (p2.x - p1.x) * t,
            p1.y + (p2.y - p1.y) * t
        )
    
    @staticmethod
    def create_bounds_coordinates(bounds: GRectF, height: float = 0.0) -> List[Tuple[float, float, float]]:
        """
        Create 3D coordinates for visualizing rectangle bounds.
        
        Args:
            bounds: Rectangle bounds to visualize
            height: Z-coordinate height for visualization
            
        Returns:
            List of 3D coordinates (tuples)
        """
        left, top, right, bottom = bounds.left, bounds.top, bounds.right, bounds.bottom
        return [
            (left, top, height), 
            (right, top, height),
            (right, bottom, height), 
            (left, bottom, height),
            (left, top, height)  # Close the rectangle
        ]
    
    @staticmethod
    def create_arrow_coordinates(center: GPointF, direction: GPointF, size: float = 1.0, 
                                 height: float = 0.0) -> List[Tuple[float, float, float]]:
        """
        Create 3D coordinates for an arrow visualization.
        
        Args:
            center: Center point of the arrow
            direction: Direction vector for the arrow
            size: Size of the arrow
            height: Z-coordinate height for visualization
            
        Returns:
            List of 3D coordinates (tuples) for drawing the arrow
        """
        import mathutils  # Import here to avoid Blender dependency issues
        
        # Create normalized direction vector
        dir_vec = mathutils.Vector((direction.x, direction.y, 0)).normalized()
        # Create perpendicular vector for arrow head
        perp_vec = mathutils.Vector((-dir_vec.y, dir_vec.x, 0))
        
        # Calculate arrow points
        origin = mathutils.Vector((center.x, center.y, height))
        tip = origin + dir_vec * size
        left_head = tip - dir_vec * (size * 0.3) + perp_vec * (size * 0.2)
        right_head = tip - dir_vec * (size * 0.3) - perp_vec * (size * 0.2)
        
        # Return coordinates as tuples for GPU drawing
        return [
            tuple(origin), tuple(tip),  # Main arrow line
            tuple(tip), tuple(left_head),  # Left head line
            tuple(tip), tuple(right_head)  # Right head line
        ]
    
    @staticmethod
    def is_point_in_polygon(point: GPointF, polygon: List[GPointF]) -> bool:
        """
        Determine if a point is inside a polygon using ray casting algorithm.
        
        Args:
            point: Point to check
            polygon: List of points forming the polygon
            
        Returns:
            True if point is inside, False otherwise
        """
        if len(polygon) < 3:
            return False
            
        inside = False
        j = len(polygon) - 1
        
        for i in range(len(polygon)):
            # Check if point is exactly on a vertex
            if (point.x == polygon[i].x and point.y == polygon[i].y) or \
               (point.x == polygon[j].x and point.y == polygon[j].y):
                return True
                
            # Check if point is exactly on an edge
            if (polygon[i].y == polygon[j].y and polygon[i].y == point.y and 
                min(polygon[i].x, polygon[j].x) <= point.x <= max(polygon[i].x, polygon[j].x)):
                return True
            
            # Ray casting algorithm
            if ((polygon[i].y > point.y) != (polygon[j].y > point.y)) and \
               (point.x < (polygon[j].x - polygon[i].x) * (point.y - polygon[i].y) / 
                (polygon[j].y - polygon[i].y) + polygon[i].x):
                inside = not inside
                
            j = i
            
        return inside
    
    @staticmethod
    def deg_to_rad(degrees: float) -> float:
        """
        Convert degrees to radians.
        
        Args:
            degrees: Angle in degrees
            
        Returns:
            Angle in radians
        """
        return float(degrees) * math.pi / 180.0
    
    @staticmethod
    def hex_from_rgba(rgba: Tuple[float, float, float, float]) -> str:
        """
        Convert RGBA color values to hexadecimal string.
        
        Args:
            rgba: Tuple of (red, green, blue, alpha) values in [0.0-1.0] range
            
        Returns:
            Hexadecimal color string (e.g., "#FF0000" for red)
        """
        r, g, b = [int(c * 255) for c in rgba[:3]]
        return f"#{r:02x}{g:02x}{b:02x}"
    
    @staticmethod
    def format_coordinate(value: float, precision: int, use_comma: bool) -> str:
        """
        Format coordinate value with specified precision and decimal separator.
        
        Args:
            value: Coordinate value to format
            precision: Number of decimal places
            use_comma: Whether to use comma as decimal separator
            
        Returns:
            Formatted string representation
        """
        formatted = f"{value:.{precision}f}"
        return formatted.replace(".", ",") if use_comma else formatted
