"""Vector validation helpers."""

from __future__ import annotations

from typing import Any

import geopandas as gpd

from ..validation import VectorDataset


def validate_vector(data: Any) -> bool:
    """Validate that the supplied object can be treated as vector data.

    This remains a compatibility wrapper around the shared validation framework
    used across the package for geospatial datasets.
    """

    if isinstance(data, gpd.GeoDataFrame):
        if "geometry" not in data.columns or len(data) == 0:
            return False

        crs = data.crs.to_string() if data.crs is not None else None
        bounds = tuple(data.total_bounds) if len(data) > 0 else None
        dataset = VectorDataset(
            name="vector-data",
            crs=crs,
            bounds=bounds,
            geometry=data,
            topology=True,
        )
        return dataset.validate().passed

    if isinstance(data, gpd.GeoSeries):
        return len(data) > 0

    if hasattr(data, "__iter__"):
        items = list(data)
        if not items:
            return False
        return all(hasattr(item, "geom_type") for item in items)

    return False
