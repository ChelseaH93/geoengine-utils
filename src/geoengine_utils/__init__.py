"""
GeoEngine Utils

Production-ready utilities for geospatial data engineering.
"""

from .raster import (
    get_raster_metadata,
    validate_raster,
)

from .crs import (
    find_matching_crs,
    recommend_crs,
    transform_geometry,
    validate_crs,
)

__version__ = "0.1.0"

__all__ = [
    # Raster
    "get_raster_metadata",
    "validate_raster",

    # CRS
    "find_matching_crs",
    "recommend_crs",
    "transform_geometry",
    "validate_crs",
]