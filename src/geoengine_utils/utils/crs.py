"""CRS utilities."""

from typing import Any


def is_supported_crs(crs: Any) -> bool:
    """Return whether the supplied value looks like a CRS definition.

    Parameters
    ----------
    crs : Any
        CRS-like input.

    Returns
    -------
    bool
        ``True`` when the value is not ``None`` and is not empty.
    """

    return crs is not None and str(crs).strip() != ""
