"""Validation helpers for coordinate reference systems."""

from typing import Any

from pyproj import CRS


def validate_crs(crs: Any) -> bool:
    """Validate that a CRS can be parsed by PROJ.

    Parameters
    ----------
    crs : Any
        EPSG code, WKT, proj string or CRS object.

    Returns
    -------
    bool
        ``True`` when the CRS can be parsed successfully.
    """

    try:
        CRS.from_user_input(crs)
        return True
    except Exception:
        return False
