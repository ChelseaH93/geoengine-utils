"""Geometry transformation helpers for CRS conversions."""

from typing import Any

from pyproj import Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


def transform_geometry(
    geometry: BaseGeometry,
    source_crs: Any,
    destination_crs: Any,
) -> BaseGeometry:
    """Transform a Shapely geometry between coordinate systems.

    Parameters
    ----------
    geometry : BaseGeometry
        The geometry to transform.
    source_crs : Any
        Source CRS definition.
    destination_crs : Any
        Destination CRS definition.

    Returns
    -------
    BaseGeometry
        The transformed geometry.
    """

    transformer = Transformer.from_crs(
        source_crs,
        destination_crs,
        always_xy=True,
    )

    return transform(
        transformer.transform,
        geometry,
    )