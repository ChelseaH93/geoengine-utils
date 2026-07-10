"""Data models for raster metadata."""

from __future__ import annotations

from dataclasses import dataclass


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
