"""Vector simplification helpers."""

from __future__ import annotations

from typing import Any

import geopandas as gpd

from .convert import convert_vector


def simplify_vector(data: Any, tolerance: float = 0.0) -> gpd.GeoDataFrame:
    """Simplify vector geometries while preserving the data frame structure.

    Parameters
    ----------
    data : Any
        A GeoDataFrame or GeoSeries containing geometries.
    tolerance : float, optional
        Simplification tolerance passed to shapely's simplify operation.

    Returns
    -------
    gpd.GeoDataFrame
        A new GeoDataFrame with simplified geometries.
    """

    frame = convert_vector(data)
    simplified = frame.copy()
    simplified.geometry = simplified.geometry.simplify(tolerance=tolerance)
    return simplified
