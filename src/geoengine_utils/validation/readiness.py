"""Single-entry-point readiness assessment for raster and vector datasets.

``assess_readiness`` is the primary public API for checking whether a dataset
is ready for production use. Callers only need to hand it the dataset itself
-- a file path, a GeoDataFrame/GeoSeries, or an iterable of Shapely geometries
-- and it infers everything else (dataset type, CRS, bounds, geometry
validity, band/feature counts, ...) automatically. There is no need to
hand-build a schema object or supply metadata manually.
"""

from __future__ import annotations

from os import PathLike
from pathlib import Path
from typing import Any

import geopandas as gpd
import rasterio

from ..raster.metadata import get_raster_metadata
from .report import ValidationReport
from .schemas import RasterDataset, VectorDataset


def assess_readiness(source: Any) -> ValidationReport:
    """Assess whether a raster or vector dataset is ready for production use.

    Parameters
    ----------
    source : Any
        A path to a raster or vector file, a GeoDataFrame/GeoSeries, or an
        iterable of Shapely geometries. The dataset type and every detail
        needed to validate it are inferred automatically.

    Returns
    -------
    ValidationReport
        A report describing any errors or warnings found. Use
        ``report.passed`` for a pass/fail check or ``report.format_report()``
        for a human-readable summary.
    """

    if isinstance(source, (str, PathLike)):
        return _assess_path(Path(source))

    return _assess_vector(source)


def _assess_path(path: Path) -> ValidationReport:
    if not path.exists():
        report = ValidationReport()
        report.add_error(f"Dataset not found: {path}")
        return report

    try:
        with rasterio.open(path):
            pass
    except rasterio.errors.RasterioIOError:
        pass
    else:
        return _assess_raster(path)

    try:
        vector_data = gpd.read_file(path)
    except Exception:
        report = ValidationReport()
        report.add_error(f"'{path}' could not be read as a raster or vector dataset.")
        return report

    return _assess_vector(vector_data)


def _assess_raster(path: Path) -> ValidationReport:
    metadata = get_raster_metadata(str(path))
    dataset = RasterDataset(
        name=path.stem or path.name,
        path=str(path),
        crs=metadata.crs,
        bounds=metadata.bounds,
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

    return report


def _assess_vector(data: Any) -> ValidationReport:
    report = ValidationReport()

    if isinstance(data, gpd.GeoSeries):
        if len(data) == 0:
            report.add_error("Vector dataset contains no geometries.")
            return report
        data = gpd.GeoDataFrame(geometry=data, crs=data.crs)

    elif not isinstance(data, gpd.GeoDataFrame):
        if not hasattr(data, "__iter__"):
            report.add_error(f"Unsupported dataset type: {type(data).__name__}")
            return report

        items = list(data)
        if not items:
            report.add_error("Vector dataset contains no geometries.")
            return report
        if not all(hasattr(item, "geom_type") for item in items):
            report.add_error("Vector dataset contains items that are not geometries.")
            return report

        data = gpd.GeoDataFrame(geometry=items)

    if "geometry" not in data.columns:
        report.add_error("Vector dataset has no geometry column.")
        return report

    if len(data) == 0:
        report.add_error("Vector dataset contains no features.")
        return report

    crs = data.crs.to_string() if data.crs is not None else None
    valid_mask = data.geometry.is_valid
    empty_mask = data.geometry.is_empty
    topology = bool(valid_mask.all())

    dataset = VectorDataset(
        name="vector-data",
        crs=crs,
        bounds=tuple(data.total_bounds),
        geometry=data,
        topology=topology,
    )
    report.issues.extend(dataset.validate().issues)

    if empty_mask.any():
        empty_count = int(empty_mask.sum())
        report.add_error(
            f"{empty_count} of {len(data)} geometries are empty and contain no shape."
        )

    non_empty_invalid = valid_mask.eq(False) & ~empty_mask
    if non_empty_invalid.any():
        invalid_count = int(non_empty_invalid.sum())
        report.add_warning(
            f"{invalid_count} of {len(data)} geometries are invalid or self-intersecting."
        )

    geometry_types = data.geometry[~empty_mask].geom_type.unique()
    if len(geometry_types) > 1:
        type_list = ", ".join(sorted(geometry_types))
        report.add_warning(
            f"Dataset mixes multiple geometry types ({type_list}); "
            "many downstream tools expect a single geometry type per layer."
        )

    return report
