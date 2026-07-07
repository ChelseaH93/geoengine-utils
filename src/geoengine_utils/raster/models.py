from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RasterMetadata:
    driver: str
    crs: Optional[str]
    width: int
    height: int
    bands: int
    dtype: str
    resolution: tuple[float, float]
    bounds: tuple[float, float, float, float]
    nodata: Optional[float]


@dataclass
class ValidationResult:
    passed: bool
    metadata: RasterMetadata
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)