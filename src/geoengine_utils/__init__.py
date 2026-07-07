"""GeoEngine Utils.

Production-ready utilities for geospatial data engineering.
"""

__version__ = "0.1.0"


def main(*args, **kwargs):
    """Run the CLI entry point for the package."""

    from .cli import main as cli_main

    return cli_main(*args, **kwargs)


from .crs import (
    find_matching_crs,
    recommend_crs,
    transform_geometry,
    validate_crs,
)
from .raster import get_raster_metadata, validate_raster

__all__ = [
    "main",
    "get_raster_metadata",
    "validate_raster",
    "find_matching_crs",
    "recommend_crs",
    "transform_geometry",
    "validate_crs",
]