from .metadata import get_raster_metadata
from .models import ValidationResult


def validate_raster(path: str) -> ValidationResult:
    """
    Validate that a raster is suitable for use in production pipelines.

    Parameters
    ----------
    path : str
        Path to raster.

    Returns
    -------
    ValidationResult
    """

    metadata = get_raster_metadata(path)

    warnings = []
    errors = []

    # Required checks

    if metadata.crs is None:
        errors.append("Raster has no CRS defined.")

    if metadata.width <= 0:
        errors.append("Raster width must be greater than zero.")

    if metadata.height <= 0:
        errors.append("Raster height must be greater than zero.")

    if metadata.bands == 0:
        errors.append("Raster contains no bands.")

    if metadata.nodata is None:
        warnings.append("Raster has no NoData value defined.")

    passed = len(errors) == 0

    return ValidationResult(
        passed=passed,
        metadata=metadata,
        warnings=warnings,
        errors=errors,
    )