"""
SVG export functionality for GTA V Scaleform Minimap Calculator.

This module provides functionality for exporting processed curve data
to SVG format for use in GTA V minimap creation.
"""

import os
import json
from typing import Dict, List, Tuple, Any

from ..geometry import GPointF, GRectF, Vector2
from ..geometry.utils import GeometryUtils


class SVGExporter:
    """
    Handles exporting curve data to SVG format for GTA V Scaleform minimap.

    This class provides methods for generating SVG content from curve data
    and exporting it to files.
    """

    @staticmethod
    def generate_svg_content(
        dimensions: Dict[str, float],
        normalized_curves: List[Dict[str, Any]],
        settings,
        minimap_coords: List[Dict[str, float]],
    ) -> str:
        """
        Generate SVG content from normalized curve data.

        Args:
            dimensions: Dictionary with width and height information
            normalized_curves: List of normalized curve objects with style information
            settings: Blender settings object containing SVG export settings
            minimap_coords: List of minimap coordinate points

        Returns:
            String containing complete SVG document
        """
        width = max(0.1, dimensions["width_svg"]) * settings.svg_scale
        height = max(0.1, dimensions["height_svg"]) * settings.svg_scale

        # Start SVG document
        svg_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="{width:.2f}px" height="{height:.2f}px" viewBox="0 0 {width:.2f} {height:.2f}" xmlns="http://www.w3.org/2000/svg">
  <g transform="scale({settings.svg_scale})">
"""
        # Check for empty curves
        if not normalized_curves or len(normalized_curves) == 0:
            svg_content += f'    <rect x="0" y="0" width="{width/settings.svg_scale:.2f}" height="{height/settings.svg_scale:.2f}" fill="none" stroke="red" stroke-width="0.5" stroke-dasharray="2,2" />\n'
            svg_content += f'    <text x="{width/(2*settings.svg_scale):.2f}" y="{height/(2*settings.svg_scale):.2f}" text-anchor="middle" fill="red">No curve data</text>\n'
        else:
            # Process each curve with its own style information
            for curve_obj in normalized_curves:
                splines = curve_obj["splines"]
                style = curve_obj["style"]

                # If style information exists, use it
                if style:
                    fill_color = (
                        GeometryUtils.hex_from_rgba(style["fill_color"])
                        if style["use_fill"]
                        else "none"
                    )
                    stroke_color = (
                        GeometryUtils.hex_from_rgba(style["stroke_color"])
                        if style["use_stroke"]
                        else "none"
                    )
                    stroke_width = style["stroke_width"] if style["use_stroke"] else 0
                else:
                    # Fallback to global settings
                    fill_color = (
                        GeometryUtils.hex_from_rgba(settings.fill_color)
                        if settings.use_fill
                        else "none"
                    )
                    stroke_color = (
                        GeometryUtils.hex_from_rgba(settings.stroke_color)
                        if settings.use_stroke
                        else "none"
                    )
                    stroke_width = settings.stroke_width if settings.use_stroke else 0

                # Generate path data for all splines in the object
                for spline in splines:
                    path_data = SVGExporter._generate_path_data(
                        spline, settings.precision, settings.use_comma_separator
                    )
                    if path_data:
                        svg_content += f'    <path d="{path_data}" fill="{fill_color}" stroke="{stroke_color}" stroke-width="{stroke_width}" />\n'

        # Add markers if enabled
        if settings.show_markers:
            for coord in minimap_coords:
                x, y = coord["x"] * settings.svg_scale, coord["y"] * settings.svg_scale
                svg_content += f'    <circle cx="{x:.2f}" cy="{y:.2f}" r="{settings.marker_size}" fill="{settings.marker_color}" />\n'
            svg_content += f"    <!-- Markers show reference points for positioning. Can be safely removed. -->\n"

        # Close SVG document
        return svg_content + "  </g>\n</svg>"

    @staticmethod
    def _generate_path_data(
        spline: List[Dict[str, Any]], precision: int, use_comma: bool
    ) -> str:
        """
        Generate SVG path data from spline segments.

        Args:
            spline: List of spline segments
            precision: Number of decimal places for coordinates
            use_comma: Whether to use comma as decimal separator

        Returns:
            SVG path data string
        """
        # Join multiple segments into a single path for better performance
        path_segments = []

        for segment in spline:
            seg_type, points = segment["type"], segment["points"]
            if seg_type == "M":
                x = GeometryUtils.format_coordinate(points[0].x, precision, use_comma)
                y = GeometryUtils.format_coordinate(points[0].y, precision, use_comma)
                path_segments.append(f"M {x},{y}")
            elif seg_type == "L":
                x = GeometryUtils.format_coordinate(points[0].x, precision, use_comma)
                y = GeometryUtils.format_coordinate(points[0].y, precision, use_comma)
                path_segments.append(f"L {x},{y}")
            elif seg_type == "C":
                x1 = GeometryUtils.format_coordinate(points[0].x, precision, use_comma)
                y1 = GeometryUtils.format_coordinate(points[0].y, precision, use_comma)
                x2 = GeometryUtils.format_coordinate(points[1].x, precision, use_comma)
                y2 = GeometryUtils.format_coordinate(points[1].y, precision, use_comma)
                x3 = GeometryUtils.format_coordinate(points[2].x, precision, use_comma)
                y3 = GeometryUtils.format_coordinate(points[2].y, precision, use_comma)
                path_segments.append(f"C {x1},{y1} {x2},{y2} {x3},{y3}")

        # Join all segments with a single space
        return " ".join(path_segments)

    @staticmethod
    def export_svg_file(filepath: str, svg_content: str) -> None:
        """
        Write SVG content to file.

        Args:
            filepath: Path to save the SVG file
            svg_content: SVG content to write
        """
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(svg_content)

    @staticmethod
    def export_minimap_data(filepath: str, minimap_data: Dict[str, Any]) -> str:
        """
        Export minimap data to JSON file.

        Args:
            filepath: Base path for the SVG file
            minimap_data: Minimap data to export

        Returns:
            Path to the exported JSON file
        """
        json_filepath = os.path.join(os.path.dirname(filepath), "minimap_data.json")
        with open(json_filepath, "w") as f:
            json.dump(minimap_data, f, indent=2)
        return json_filepath
