"""
Curve processor for GTA V Scaleform Minimap Calculator.

This module provides functionality for extracting and processing curve data
from Blender objects for use in GTA V minimap creation.
"""

import bpy
import numpy as np
from typing import Dict, List, Tuple, Any, Optional

from ..geometry import GPointF, GRectF, Vector3, calculate_bounds
from ..constants import OPTIMIZATION_THRESHOLD
from ..utils.cache import curve_cache, geometry_cache


class CurveProcessor:
    """
    Handles processing of Blender curve objects for Scaleform minimap export.

    This class provides methods for extracting curve data, normalizing coordinates,
    and calculating dimensions for SVG export.
    """

    @staticmethod
    def _process_bezier_spline(spline, matrix, spline_points, all_points):
        """
        Process a Bezier spline into path segments.

        Args:
            spline: Blender Bezier spline to process
            matrix: World transformation matrix to apply
            spline_points: List to store the resulting path segments
            all_points: List to store all processed points (for bounds calculation)
        """
        # Precompute initial data
        bezier_points = spline.bezier_points
        use_cyclic = spline.use_cyclic_u

        if not bezier_points:
            return

        # First pass to transform all points at once
        transformed_points = []
        for point in bezier_points:
            co, hl, hr = [
                matrix @ v for v in (point.co, point.handle_left, point.handle_right)
            ]
            transformed_points.append(
                {
                    "co": GPointF(co.x, co.y),
                    "hl": GPointF(hl.x, hl.y),
                    "hr": GPointF(hr.x, hr.y),
                }
            )

        # Second pass to create segments (more efficient with points already transformed)
        first_point = transformed_points[0]
        spline_points.append({"type": "M", "points": [first_point["co"]]})
        all_points.append(first_point["co"])

        # Process intermediate points
        for i in range(1, len(transformed_points)):
            prev_point = transformed_points[i - 1]
            curr_point = transformed_points[i]

            spline_points.append(
                {
                    "type": "C",
                    "points": [prev_point["hr"], curr_point["hl"], curr_point["co"]],
                }
            )
            all_points.append(curr_point["co"])

        # Close the curve if cyclic
        if use_cyclic and transformed_points:
            last_point = transformed_points[-1]
            spline_points.append(
                {
                    "type": "C",
                    "points": [last_point["hr"], first_point["hl"], first_point["co"]],
                }
            )

    @staticmethod
    def _process_poly_spline(spline, matrix, spline_points, all_points):
        """
        Process a poly spline into path segments.

        Args:
            spline: Blender poly spline to process
            matrix: World transformation matrix to apply
            spline_points: List to store the resulting path segments
            all_points: List to store all processed points (for bounds calculation)
        """
        points = spline.points
        use_cyclic = spline.use_cyclic_u

        if not points:
            return

        # Precompute transformations for all points
        transformed_points = []
        for point in points:
            co = matrix @ point.co.to_3d()
            transformed_points.append(GPointF(co.x, co.y))

        # First point is a move
        first_point = transformed_points[0]
        spline_points.append({"type": "M", "points": [first_point]})
        all_points.append(first_point)

        # Remaining points are lines
        for i in range(1, len(transformed_points)):
            pt = transformed_points[i]
            spline_points.append({"type": "L", "points": [pt]})
            all_points.append(pt)

        # Close the curve if cyclic
        if use_cyclic and transformed_points:
            spline_points.append({"type": "L", "points": [first_point]})

    @staticmethod
    def normalize_curves(
        curve_data: Dict[str, Any], center_at_origin: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Normalize curve data for SVG export, optionally centering at origin.

        This transforms the coordinates to be relative to the top-left corner
        of the bounds (or to the center if center_at_origin is True).

        Args:
            curve_data: Dictionary with curve data from get_selected_curves
            center_at_origin: If True, center coordinates at origin instead of top-left

        Returns:
            List of normalized curve data objects with style information
        """
        # Validate input to prevent errors
        if not curve_data or "center" not in curve_data or "bounds" not in curve_data:
            return []

        center, bounds = curve_data["center"], curve_data["bounds"]
        offset_x = center.x if center_at_origin else bounds.left
        offset_y = center.y if center_at_origin else bounds.top

        # Create cache key
        cache_key = f"normalize_{hash(str(curve_data))}_{center_at_origin}"

        # Check cache
        cached_result = geometry_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        normalized_data = []

        # Iterate through each curve object
        for i, curve_obj in enumerate(curve_data.get("curves", [])):
            obj_normalized_splines = []

            # Iterate through each spline in the curve object
            for spline in curve_obj:
                normalized_segments = []

                # Normalize each segment in the spline
                for seg in spline:
                    normalized_segments.append(
                        {
                            "type": seg["type"],
                            "points": [
                                GPointF(pt.x - offset_x, pt.y - offset_y)
                                for pt in seg["points"]
                            ],
                        }
                    )

                obj_normalized_splines.append(normalized_segments)

            # Add style information if available
            curve_info = None
            if "curves_info" in curve_data and i < len(curve_data["curves_info"]):
                curve_info = curve_data["curves_info"][i]

            normalized_data.append(
                {"splines": obj_normalized_splines, "style": curve_info}
            )

        # Save in cache
        geometry_cache.set(cache_key, normalized_data)
        return normalized_data

    @staticmethod
    def calculate_dimensions(curve_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate dimensions for curve data.

        Args:
            curve_data: Dictionary with curve data from get_selected_curves

        Returns:
            Dictionary with width, height, and center information
        """
        if not curve_data or "bounds" not in curve_data or "center" not in curve_data:
            return {
                "width_orig": 0.1,
                "height_orig": 0.1,
                "width_svg": 0.1,
                "height_svg": 0.1,
                "center": GPointF(0, 0),
            }

        bounds = curve_data["bounds"]
        width = max(0.1, bounds.width())
        height = max(0.1, bounds.height())

        return {
            "width_orig": width,
            "height_orig": height,
            "width_svg": width,
            "height_svg": height,
            "center": curve_data["center"],
        }

    @staticmethod
    def simplify_curves(
        curve_data: Dict[str, Any], tolerance: float = 0.1
    ) -> Dict[str, Any]:
        """
        Simplify curves to reduce point count while maintaining shape.

        Args:
            curve_data: Dictionary with curve data from get_selected_curves
            tolerance: Tolerance for simplification (higher = more simplified)

        Returns:
            New dictionary with simplified curve data
        """
        from ..geometry.utils import GeometryUtils

        if not curve_data or not curve_data.get("valid", False):
            return curve_data

        # Create cache key
        cache_key = f"simplify_{hash(str(curve_data))}_{tolerance}"

        # Check cache
        cached_result = geometry_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        simplified_curves = []

        # Process each curve object
        for curve_obj in curve_data["curves"]:
            simplified_obj = []

            # Process each spline
            for spline in curve_obj:
                simplified_spline = []
                points_to_simplify = []

                # Extract points from spline
                for seg in spline:
                    if seg["type"] == "M":
                        # If there are accumulated points, simplify them first
                        if points_to_simplify:
                            CurveProcessor._add_simplified_points(
                                points_to_simplify,
                                simplified_spline,
                                tolerance,
                                GeometryUtils.simplify_polyline,
                            )
                            points_to_simplify = []

                        # Add move point
                        simplified_spline.append(seg)
                        points_to_simplify.append(seg["points"][0])
                    elif seg["type"] == "L":
                        # Accumulate line points for simplification
                        points_to_simplify.append(seg["points"][0])
                    elif seg["type"] == "C":
                        # Bezier curves aren't simplified directly
                        # If there are accumulated points, simplify them first
                        if points_to_simplify:
                            CurveProcessor._add_simplified_points(
                                points_to_simplify,
                                simplified_spline,
                                tolerance,
                                GeometryUtils.simplify_polyline,
                            )
                            points_to_simplify = []

                        # Add Bezier curve segment
                        simplified_spline.append(seg)

                # Process remaining points
                if points_to_simplify:
                    CurveProcessor._add_simplified_points(
                        points_to_simplify,
                        simplified_spline,
                        tolerance,
                        GeometryUtils.simplify_polyline,
                    )

                simplified_obj.append(simplified_spline)

            simplified_curves.append(simplified_obj)

        # Create result with simplified curves
        result = curve_data.copy()
        result["curves"] = simplified_curves

        # Save to cache
        geometry_cache.set(cache_key, result)
        return result

    @staticmethod
    def _add_simplified_points(points, simplified_spline, tolerance, simplify_func):
        """
        Add simplified points to a spline.

        Args:
            points: List of points to simplify
            simplified_spline: List to add simplified segments to
            tolerance: Tolerance for simplification
            simplify_func: Function to use for simplification
        """
        if len(points) <= 1:
            return

        # Use simplification algorithm
        simplified = simplify_func(points, tolerance)

        # First point should already be included as 'M'
        for i in range(1, len(simplified)):
            simplified_spline.append({"type": "L", "points": [simplified[i]]})

    @staticmethod
    def get_selected_curves(
        context: bpy.types.Context, use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Extract data from selected curve objects in Blender.

        Args:
            context: Blender context containing selection information
            use_cache: Whether to use cached results if available

        Returns:
            Dictionary with processed curve data including:
            - valid: Whether valid curve data was found
            - curves: List of curve data organized by object and spline
            - bounds: Bounding rectangle for all curves
            - center: Center point of the bounds
            - curves_info: Style information for each curve
            - message: Error message if not valid
        """
        selected_objects = [
            obj for obj in context.selected_objects if obj.type == "CURVE"
        ]
        if not selected_objects:
            return {
                "valid": False,
                "curves": [],
                "bounds": GRectF(),
                "center": GPointF(),
                "message": "No valid curve objects selected.",
            }

        # Create cache key based on selected objects and their properties
        cache_key = f"selected_curves_{'_'.join(obj.name for obj in selected_objects)}"
        cache_key += f"_{hash(tuple((obj.matrix_world[i][j] for i in range(4) for j in range(4)) for obj in selected_objects))}"

        # Check cache if allowed
        if use_cache:
            cached_result = curve_cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        all_curves_data = []  # List to store curve data by object
        all_points = []  # Flat list of all points for bounds calculation
        curves_info = []  # Style information for each curve

        # Process each selected curve object
        for obj in selected_objects:
            matrix = obj.matrix_world
            object_curves_data = []  # Store splines for this object
            object_points = []  # Points for this object

            # Process each spline in the curve object
            for spline in obj.data.splines:
                spline_points = []  # Store segments for this spline

                # Process based on spline type
                if spline.type == "BEZIER":
                    CurveProcessor._process_bezier_spline(
                        spline, matrix, spline_points, object_points
                    )
                else:
                    CurveProcessor._process_poly_spline(
                        spline, matrix, spline_points, object_points
                    )

                # Only add splines with points
                if spline_points:
                    object_curves_data.append(spline_points)

            # Only add objects with valid data
            if object_points:
                all_curves_data.append(object_curves_data)
                all_points.extend(object_points)

                # Extract style information from object properties
                curve_settings = {
                    "name": obj.name,
                    "fill_preset": obj.get("scaleform_fill_preset", "ACCESSIBLE"),
                    "use_fill": obj.get("scaleform_use_fill", True),
                    "fill_color": (
                        obj.get("scaleform_fill_color_r", 0.6),
                        obj.get("scaleform_fill_color_g", 0.6),
                        obj.get("scaleform_fill_color_b", 0.6),
                        obj.get("scaleform_fill_color_a", 1.0),
                    ),
                    "use_stroke": obj.get("scaleform_use_stroke", False),
                    "stroke_color": (
                        obj.get("scaleform_stroke_color_r", 0.25),
                        obj.get("scaleform_stroke_color_g", 0.25),
                        obj.get("scaleform_stroke_color_b", 0.25),
                        obj.get("scaleform_stroke_color_a", 1.0),
                    ),
                    "stroke_width": obj.get("scaleform_stroke_width", 0.5),
                }
                curves_info.append(curve_settings)

        # Prepare result dictionary
        result = {
            "valid": False,
            "curves": [],
            "bounds": GRectF(),
            "center": GPointF(),
            "message": "",
        }

        # If we have points, calculate bounds and populate result
        if all_points:
            bounds = calculate_bounds(all_points)
            result["bounds"] = bounds
            result["center"] = bounds.center()
            result["curves"] = all_curves_data
            result["curves_info"] = curves_info
            result["valid"] = True
        else:
            result["message"] = "No valid curve data found in selected objects."

        # Save in cache for future use if caching is enabled
        if use_cache:
            curve_cache.set(cache_key, result)

        return result

    @staticmethod
    def force_refresh_curve_data(context) -> Dict[str, Any]:
        """
        Force a refresh of the curve data without using cache.

        This is useful when the visualization needs to be updated after
        curves have been modified or when ensuring the most current data.

        Args:
            context: Blender context

        Returns:
            Fresh curve data
        """
        # Always get fresh data by passing use_cache=False
        return CurveProcessor.get_selected_curves(context, use_cache=False)
