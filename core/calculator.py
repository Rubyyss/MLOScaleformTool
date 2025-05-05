"""
Minimap coordinate calculator for GTA V Scaleform Minimap Calculator.

This module provides functionality for converting between Blender, World, and
Scaleform coordinate systems used in GTA V minimap creation.
"""

from typing import Dict, List, Tuple, Any
import numpy as np

from ..geometry import Vector2, Vector3
from ..utils.cache import calculation_cache


class MinimapCalculator:
    """
    Handles calculations for mapping Blender coordinates to GTA V Scaleform minimap coordinates.

    This class provides conversion methods between different coordinate systems:
    - Blender: 3D coordinate system used in Blender
    - World: GTA V world-space coordinates
    - Scaleform: 2D coordinate system used for GTA V minimap
    """

    def __init__(
        self,
        world_bounds: Tuple[float, float, float, float],
        minimap_size: Tuple[float, float],
    ):
        """
        Initialize the calculator with world bounds and minimap dimensions.

        Args:
            world_bounds: Tuple of (min_x, max_x, min_y, max_y) for world boundaries
            minimap_size: Tuple of (width, height) for minimap dimensions
        """
        # Create cache key for efficient reuse
        self._cache_key = f"calc_{world_bounds}_{minimap_size}"

        # Store world boundaries
        self.world_min_x, self.world_max_x, self.world_min_y, self.world_max_y = (
            world_bounds
        )

        # Store minimap dimensions
        self.minimap_width, self.minimap_height = minimap_size

        # Calculate world dimensions
        self.world_width = self.world_max_x - self.world_min_x
        self.world_height = self.world_max_y - self.world_min_y

        # Precalculate inverses for division (faster than dividing)
        self.inv_world_width = 1.0 / self.world_width if self.world_width != 0 else 0
        self.inv_world_height = 1.0 / self.world_height if self.world_height != 0 else 0

    def world_to_minimap(self, position: Vector3) -> Vector2:
        """
        Convert world coordinates to minimap coordinates.

        The minimap coordinate system has (0,0) at the top-left corner,
        with positive x to the right and positive y downward.

        Args:
            position: World-space position

        Returns:
            Corresponding position on the minimap
        """
        # Create cache key for this specific calculation
        pos_cache_key = f"{self._cache_key}_{position.x:.3f}_{position.y:.3f}_{position.z:.3f}_minimap"

        # Check if result is in cache
        cached_result = calculation_cache.get(pos_cache_key)
        if cached_result is not None:
            return cached_result

        # Normalize position within world bounds (0.0 to 1.0)
        norm_x = (position.x - self.world_min_x) * self.inv_world_width
        norm_y = (position.y - self.world_min_y) * self.inv_world_height

        # Convert normalized position to minimap coordinates
        # Note: Y-axis is flipped in the minimap (top-left origin)
        minimap_x = norm_x * self.minimap_width
        minimap_y = (1.0 - norm_y) * self.minimap_height

        # Clamp to minimap boundaries
        result = Vector2(
            max(0.0, min(minimap_x, self.minimap_width)),
            max(0.0, min(minimap_y, self.minimap_height)),
        )

        # Store in cache for future calls
        calculation_cache.set(pos_cache_key, result)
        return result

    def blender_to_scaleform(
        self, position: Vector3, svg_scale: float, svg_width: float, svg_height: float
    ) -> Vector2:
        """
        Convert Blender coordinates to Scaleform coordinates.

        In Blender, Y corresponds to Scaleform X, and -Z corresponds to Scaleform Y,
        with appropriate scaling and centering applied.

        Args:
            position: Blender-space position
            svg_scale: Scale factor for SVG output
            svg_width: Width of SVG in Blender units
            svg_height: Height of SVG in Blender units

        Returns:
            Corresponding position in Scaleform coordinates
        """
        # Create cache key for this specific calculation
        cache_key = f"{position.x:.3f}_{position.y:.3f}_{position.z:.3f}_{svg_scale}_{svg_width}_{svg_height}"

        # Check if result is in cache
        cached_result = calculation_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Convert coordinate systems (Blender Y -> Scaleform X, Blender -Z -> Scaleform Y)
        scaleform_x = position.y * svg_scale
        scaleform_y = -position.z * svg_scale

        # Center the coordinates based on SVG dimensions
        centered_x = scaleform_x - (svg_width * svg_scale / 2)
        centered_y = scaleform_y - (svg_height * svg_scale / 2)

        result = Vector2(centered_x, centered_y)

        # Store in cache for future calls
        calculation_cache.set(cache_key, result)
        return result

    def generate_scaleform_data(self, positions: List[Vector3]) -> Dict[str, Any]:
        """
        Generate Scaleform position data for a list of world positions.

        This is useful for creating marker data to export along with SVG files.

        Args:
            positions: List of world-space positions to convert

        Returns:
            Dictionary containing minimap points with their world coordinates
        """
        # Create a hash of the positions for the cache key
        pos_hash = hash(tuple((p.x, p.y, p.z) for p in positions))
        cache_key = f"{self._cache_key}_{pos_hash}_scaleform_data"

        # Check if result is in cache
        cached_result = calculation_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Generate minimap coordinates for each position
        result = {
            "minimap_points": [
                {
                    "x": (minimap_pos := self.world_to_minimap(pos)).x,
                    "y": minimap_pos.y,
                    "world_x": pos.x,
                    "world_y": pos.y,
                    "world_z": pos.z,
                }
                for pos in positions
            ]
        }

        # Store in cache for future calls
        calculation_cache.set(cache_key, result)
        return result

    def minimap_to_world(self, minimap_pos: Vector2) -> Vector3:
        """
        Convert minimap coordinates back to approximate world coordinates.

        This is the inverse of world_to_minimap, but since Z information is lost,
        we set Z to 0.0.

        Args:
            minimap_pos: Position on the minimap

        Returns:
            Corresponding world-space position (with Z=0)
        """
        # Create cache key for this specific calculation
        cache_key = f"{self._cache_key}_{minimap_pos.x:.3f}_{minimap_pos.y:.3f}_world"

        # Check if result is in cache
        cached_result = calculation_cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Normalize position within minimap (0.0 to 1.0)
        norm_x = minimap_pos.x / self.minimap_width
        # Invert Y axis (minimap has origin at top-left)
        norm_y = 1.0 - (minimap_pos.y / self.minimap_height)

        # Convert to world coordinates
        world_x = self.world_min_x + norm_x * self.world_width
        world_y = self.world_min_y + norm_y * self.world_height

        # Create result (Z is set to 0 as this information is lost in minimap)
        result = Vector3(world_x, world_y, 0.0)

        # Store in cache for future calls
        calculation_cache.set(cache_key, result)
        return result
