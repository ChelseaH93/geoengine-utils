"""Data models for raster metadata and validation results."""

from __future__ import annotations

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

    def format_report(self) -> str:
        """Return a human-readable validation report."""

        lines = [
            f"Validation {'passed' if self.passed else 'failed'}",
            f"- path: {self.metadata.driver}",
            f"- width: {self.metadata.width}",
            f"- height: {self.metadata.height}",
            f"- bands: {self.metadata.bands}",
            f"- crs: {self.metadata.crs or 'None'}",
            f"- nodata: {self.metadata.nodata}",
            f"- warnings: {len(self.warnings)}",
            f"- errors: {len(self.errors)}",
        ]

        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"  - {warning}" for warning in self.warnings)

        if self.errors:
            lines.append("Errors:")
            lines.extend(f"  - {error}" for error in self.errors)

        return "\n".join(lines)