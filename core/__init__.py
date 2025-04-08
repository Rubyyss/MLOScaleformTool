"""
Core package for GTA V Scaleform Minimap Calculator addon.

This package provides the main functionality for processing curves
and converting between coordinate systems.
"""

from .calculator import MinimapCalculator
from .processor import CurveProcessor
from .exporter import SVGExporter

__all__ = [
    'MinimapCalculator',
    'CurveProcessor',
    'SVGExporter'
]
