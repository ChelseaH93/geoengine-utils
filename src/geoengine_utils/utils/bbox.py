"""Bounding box utilities."""

from typing import Any


def bbox_to_tuple(bbox: Any) -> tuple[float, float, float, float]:
    """Convert a bounding box-like object into a 4-tuple.

    Parameters
    ----------
    bbox : Any
        Bounding box representation with ``bounds`` or 4 items.

    Returns
    -------
    tuple[float, float, float, float]
        The normalised bounding box values.
    """

    if hasattr(bbox, "bounds"):
        return tuple(bbox.bounds)

    if isinstance(bbox, (tuple, list)) and len(bbox) == 4:
        return tuple(float(value) for value in bbox)

    raise TypeError("Bounding box must be a tuple/list of 4 values or expose bounds")
