from pyproj import CRS


def validate_crs(crs) -> bool:
    """
    Validate that a CRS can be parsed by PROJ.

    Parameters
    ----------
    crs
        EPSG code, WKT, proj string or CRS object.

    Returns
    -------
    bool
    """

    try:
        CRS.from_user_input(crs)
        return True

    except Exception:
        return False