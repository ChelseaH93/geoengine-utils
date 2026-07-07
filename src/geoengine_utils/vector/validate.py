"""Vector validation helpers."""

from __future__ import annotations

from typing import Any

import geopandas as gpd


def validate_vector(data: Any) -> bool:
    """Validate that the supplied object can be treated as vector data.

    Parameters
    ----------
    data : Any
        Vector data payload to validate.

    Returns
    -------
    bool
        ``True`` when the object can be represented as a GeoDataFrame-like
        geometry collection, otherwise ``False``.
    """

    if isinstance(data, gpd.GeoDataFrame):
        return "geometry" in data.columns and len(data) > 0

    if isinstance(data, gpd.GeoSeries):
        return len(data) > 0

    if hasattr(data, "__iter__"):
        items = list(data)
        if not items:
            return False
        return all(hasattr(item, "geom_type") for item in items)

    return False
