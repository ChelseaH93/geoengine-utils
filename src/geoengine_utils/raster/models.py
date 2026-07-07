"""Data models for raster metadata and validation results."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class RasterMetadata:
    """Metadata describing a raster dataset."""

    driver: str
    crs: str | None
    width: int
    height: int
    bands: int
    dtype: str
    resolution: tuple[float, float]
    bounds: tuple[float, float, float, float]
    nodata: float | None


@dataclass(slots=True)
class ValidationResult:
    """Outcome of raster validation with warnings and errors."""

    passed: bool
    metadata: RasterMetadata
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)