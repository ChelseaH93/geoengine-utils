"""Vector conversion helpers."""

from __future__ import annotations

from typing import Any

import geopandas as gpd


def convert_vector(data: Any) -> gpd.GeoDataFrame:
    """Convert common vector inputs into a GeoDataFrame.

    Parameters
    ----------
    data : Any
        Either a GeoDataFrame, GeoSeries, or an iterable of geometry objects.

    Returns
    -------
    gpd.GeoDataFrame
        A GeoDataFrame representation of the supplied vector data.
    """

    if isinstance(data, gpd.GeoDataFrame):
        return data.copy()

    if isinstance(data, gpd.GeoSeries):
        return gpd.GeoDataFrame(geometry=data, crs=data.crs)

    if hasattr(data, "__iter__"):
        geometries = list(data)
        if geometries and all(hasattr(item, "geom_type") for item in geometries):
            return gpd.GeoDataFrame(geometry=geometries)

    raise TypeError("Unsupported vector input. Provide a GeoDataFrame, GeoSeries, or iterable of geometries.")
