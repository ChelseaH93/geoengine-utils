"""Coordinate Reference System (CRS) utilities.

Provides helpers for:
- recommending suitable projected CRSs
- validating CRSs
- transforming geometries
"""

from .recommend import estimate_crs, find_matching_crs, recommend_crs
from .transform import transform_geometry
from .validate import validate_crs

__all__ = [
    "recommend_crs",
    "estimate_crs",
    "find_matching_crs",
    "transform_geometry",
    "validate_crs",
]