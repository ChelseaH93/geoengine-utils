"""Vector geometry repair helpers."""

from __future__ import annotations

from typing import Any

import geopandas as gpd
from shapely.validation import make_valid

from .convert import convert_vector


def repair_vector(data: Any, *, drop_empty: bool = False) -> gpd.GeoDataFrame:
    """Repair invalid vector geometries while preserving dataset metadata.

    Parameters
    ----------
    data : Any
        A GeoDataFrame, GeoSeries, or iterable of Shapely geometries.
    drop_empty : bool, optional
        Remove empty or null geometries after repair. By default, rows are
        preserved and empty geometries remain for inspection.

    Returns
    -------
    gpd.GeoDataFrame
        A new GeoDataFrame with invalid non-empty geometries repaired using
        Shapely's ``make_valid`` operation.
    """

    frame = convert_vector(data)
    repaired = frame.copy()
    invalid = ~repaired.geometry.is_valid & ~repaired.geometry.is_empty
    repaired.loc[invalid, "geometry"] = repaired.loc[invalid, "geometry"].map(make_valid)

    if drop_empty:
        keep = repaired.geometry.map(
            lambda geometry: geometry is not None and not geometry.is_empty
        )
        repaired = repaired.loc[keep].copy()

    return repaired