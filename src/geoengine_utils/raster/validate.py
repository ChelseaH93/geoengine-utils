from pathlib import Path

from ..validation import RasterDataset
from .metadata import get_raster_metadata
from .models import ValidationResult


def validate_raster(path: str) -> ValidationResult:
    """Validate that a raster is suitable for use in production pipelines.

    The raster module exposes this as a compatibility wrapper around the shared
    geospatial validation framework used throughout the package.
    """

    metadata = get_raster_metadata(path)
    dataset = RasterDataset(
        name=Path(path).stem or Path(path).name,
        path=path,
        crs=metadata.crs,
        bounds=metadata.bounds,
        geometry=None,
        topology=None,
    )
    report = dataset.validate()

    if metadata.width <= 0:
        report.add_error("Raster width must be greater than zero.")

    if metadata.height <= 0:
        report.add_error("Raster height must be greater than zero.")

    if metadata.bands == 0:
        report.add_error("Raster contains no bands.")

    if metadata.nodata is None:
        report.add_warning("Raster has no NoData value defined.")

    resolutions = metadata.resolution
    if resolutions and any(value is not None and value >= 10 for value in resolutions):
        report.add_warning("Raster resolution is relatively coarse for many production workflows.")

    return ValidationResult(
        passed=report.passed,
        metadata=metadata,
        warnings=[issue.message for issue in report.issues if issue.severity == "warning"],
        errors=[issue.message for issue in report.issues if issue.severity == "error"],
    )