"""Benchmark and optimize common static vector data formats."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from os import PathLike
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping, Sequence

import geopandas as gpd

SUPPORTED_FORMATS = ("geoparquet", "geopackage", "shapefile", "geojson")


@dataclass(frozen=True)
class StaticDataConfiguration:
    """A candidate format and its writer options."""

    format: str
    compression: str | None = None
    layer_name: str = "data"
    encoding: str = "utf-8"

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "compression": self.compression,
            "layer_name": self.layer_name,
            "encoding": self.encoding,
        }


@dataclass(frozen=True)
class StaticDataBenchmarkReport:
    """Measured storage, schema, and read characteristics of a vector dataset."""

    dataset_path: Path
    format: str
    storage_bytes: int
    read_seconds: float
    feature_count: int
    column_count: int
    geometry_types: tuple[str, ...]
    crs: str | None
    bounds: tuple[float, float, float, float]
    configuration: StaticDataConfiguration | None = None
    write_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_path": str(self.dataset_path),
            "format": self.format,
            "storage_bytes": self.storage_bytes,
            "read_seconds": self.read_seconds,
            "feature_count": self.feature_count,
            "column_count": self.column_count,
            "geometry_types": list(self.geometry_types),
            "crs": self.crs,
            "bounds": list(self.bounds),
            "configuration": self.configuration.to_dict() if self.configuration else None,
            "write_seconds": self.write_seconds,
        }

    def format_report(self) -> str:
        return (
            f"{self.dataset_path}: {self.format}, {self.storage_bytes:,} bytes, "
            f"{self.feature_count:,} features, read {self.read_seconds:.3f}s"
        )


@dataclass(frozen=True)
class StaticDataOptimizationSuggestion:
    """A ranked recommendation from static format benchmarks."""

    recommended: StaticDataBenchmarkReport
    alternatives: tuple[StaticDataBenchmarkReport, ...]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommended": self.recommended.to_dict(),
            "alternatives": [report.to_dict() for report in self.alternatives],
            "rationale": self.rationale,
        }


def benchmark_static_dataset(
    dataset: str | PathLike[str],
    *,
    layer: str | None = None,
) -> StaticDataBenchmarkReport:
    """Benchmark an existing GeoParquet, GeoPackage, Shapefile, or GeoJSON."""

    path = Path(dataset)
    format_name = _format_from_path(path)
    started = time.perf_counter()
    frame = _read_vector(path, format_name=format_name, layer=layer)
    read_seconds = time.perf_counter() - started
    return _build_report(path, format_name, frame, _storage_bytes(path), read_seconds)


def benchmark_static_configurations(
    source: str | PathLike[str] | gpd.GeoDataFrame,
    configurations: Sequence[StaticDataConfiguration | Mapping[str, Any]],
    *,
    layer_name: str = "data",
) -> tuple[StaticDataBenchmarkReport, ...]:
    """Write and benchmark each candidate configuration in a temporary directory."""

    if not configurations:
        raise ValueError("configurations must contain at least one candidate")
    frame = _read_source(source)
    results: list[StaticDataBenchmarkReport] = []
    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        for index, candidate in enumerate(configurations):
            configuration = _coerce_configuration(candidate, layer_name=layer_name)
            started = time.perf_counter()
            output = _write_candidate(frame, root, index, configuration)
            write_seconds = time.perf_counter() - started
            report = benchmark_static_dataset(output, layer=configuration.layer_name)
            results.append(
                replace(
                    report,
                    configuration=configuration,
                    write_seconds=write_seconds,
                )
            )
    return tuple(results)


def suggest_static_optimization(
    reports: Sequence[StaticDataBenchmarkReport],
    *,
    target_read_seconds: float | None = None,
) -> StaticDataOptimizationSuggestion:
    """Rank candidates by read target, storage size, and write time."""

    if not reports:
        raise ValueError("reports must contain at least one benchmark report")
    if target_read_seconds is not None and target_read_seconds <= 0:
        raise ValueError("target_read_seconds must be greater than zero")

    def score(report: StaticDataBenchmarkReport) -> tuple[float, int, float]:
        read_over_target = (
            max(0.0, report.read_seconds - target_read_seconds)
            if target_read_seconds is not None
            else 0.0
        )
        return (read_over_target, report.storage_bytes, report.write_seconds or 0.0)

    ranked = tuple(sorted(reports, key=score))
    recommended = ranked[0]
    if target_read_seconds is None:
        rationale = "The recommendation minimizes storage size, then write time."
    else:
        rationale = (
            f"The recommendation prioritizes meeting the {target_read_seconds:.3f}s "
            "read target, then minimizes storage size and write time."
        )
    return StaticDataOptimizationSuggestion(recommended, ranked[1:], rationale)


def _coerce_configuration(
    candidate: StaticDataConfiguration | Mapping[str, Any],
    *,
    layer_name: str,
) -> StaticDataConfiguration:
    if isinstance(candidate, StaticDataConfiguration):
        return candidate
    values = dict(candidate)
    values.setdefault("layer_name", layer_name)
    return StaticDataConfiguration(**values)


def _read_source(source: str | PathLike[str] | gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if isinstance(source, gpd.GeoDataFrame):
        return source.copy()
    path = Path(source)
    return _read_vector(path, format_name=_format_from_path(path))


def _read_vector(path: Path, *, format_name: str, layer: str | None = None) -> gpd.GeoDataFrame:
    if format_name == "geoparquet":
        return gpd.read_parquet(path)
    if format_name == "geopackage":
        return gpd.read_file(path, layer=layer) if layer else gpd.read_file(path)
    return gpd.read_file(path)


def _write_candidate(
    frame: gpd.GeoDataFrame,
    root: Path,
    index: int,
    configuration: StaticDataConfiguration,
) -> Path:
    format_name = _validate_configuration(configuration)
    stem = root / f"candidate-{index}"
    if format_name == "geoparquet":
        output = stem.with_suffix(".parquet")
        frame.to_parquet(
            output,
            compression=configuration.compression or "zstd",
            index=False,
        )
        return output
    if format_name == "geopackage":
        output = stem.with_suffix(".gpkg")
        frame.to_file(output, layer=configuration.layer_name, driver="GPKG")
        return output
    if format_name == "shapefile":
        output = stem.with_suffix(".shp")
        frame.to_file(output, driver="ESRI Shapefile", encoding=configuration.encoding)
        return output
    output = stem.with_suffix(".geojson")
    frame.to_file(output, driver="GeoJSON", encoding=configuration.encoding)
    return output


def _validate_configuration(configuration: StaticDataConfiguration) -> str:
    format_name = configuration.format.lower()
    if format_name not in SUPPORTED_FORMATS:
        supported = ", ".join(SUPPORTED_FORMATS)
        raise ValueError(f"unsupported format '{configuration.format}'; use one of {supported}")
    if format_name != "geoparquet" and configuration.compression is not None:
        raise ValueError(f"compression is only configurable for GeoParquet, not {format_name}")
    return format_name


def _format_from_path(path: Path) -> str:
    suffix = path.suffix.lower()
    formats = {
        ".parquet": "geoparquet",
        ".geoparquet": "geoparquet",
        ".gpkg": "geopackage",
        ".shp": "shapefile",
        ".geojson": "geojson",
        ".json": "geojson",
    }
    try:
        return formats[suffix]
    except KeyError as exc:
        raise ValueError(f"unsupported vector format: {suffix or path.name}") from exc


def _storage_bytes(path: Path) -> int:
    if path.suffix.lower() == ".shp":
        return sum(
            sibling.stat().st_size
            for sibling in path.parent.glob(f"{path.stem}.*")
            if sibling.is_file()
        )
    return path.stat().st_size


def _build_report(
    path: Path,
    format_name: str,
    frame: gpd.GeoDataFrame,
    storage_bytes: int,
    read_seconds: float,
) -> StaticDataBenchmarkReport:
    geometry_types = tuple(sorted(str(value) for value in frame.geometry.dropna().geom_type.unique()))
    bounds = tuple(float(value) for value in frame.total_bounds)
    crs = frame.crs.to_string() if frame.crs is not None else None
    return StaticDataBenchmarkReport(
        dataset_path=path,
        format=format_name,
        storage_bytes=storage_bytes,
        read_seconds=read_seconds,
        feature_count=len(frame),
        column_count=len(frame.columns),
        geometry_types=geometry_types,
        crs=crs,
        bounds=bounds,
    )


__all__ = [
    "SUPPORTED_FORMATS",
    "StaticDataBenchmarkReport",
    "StaticDataConfiguration",
    "StaticDataOptimizationSuggestion",
    "benchmark_static_configurations",
    "benchmark_static_dataset",
    "suggest_static_optimization",
]
