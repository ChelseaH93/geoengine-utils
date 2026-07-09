"""GeoEngine Utils.

Production-ready utilities for geospatial data engineering.
"""

__version__ = "0.1.0"

from .crs import (
    estimate_crs,
    find_matching_crs,
    recommend_crs,
    transform_geometry,
    validate_crs,
)
from .raster import (
    get_raster_metadata,
    recommend_resampling,
    resample_raster,
    validate_raster,
)
from .validation import (
    DatasetSchema,
    RasterDataset,
    ValidationError,
    ValidationIssue,
    ValidationReport,
    VectorDataset,
    validate_dataset,
)


def main(*args, **kwargs):
    """Run the CLI entry point for the package."""

    from .cli import main as cli_main

    return cli_main(*args, **kwargs)


__all__ = [
    "main",
    "__version__",
    "get_raster_metadata",
    "validate_raster",
    "recommend_resampling",
    "resample_raster",
    "find_matching_crs",
    "recommend_crs",
    "estimate_crs",
    "transform_geometry",
    "validate_crs",
    "DatasetSchema",
    "RasterDataset",
    "VectorDataset",
    "ValidationIssue",
    "ValidationReport",
    "ValidationError",
    "validate_dataset",
]
