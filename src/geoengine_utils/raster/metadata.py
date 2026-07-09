import rasterio

from .models import RasterMetadata


def get_raster_metadata(path: str) -> RasterMetadata:
    """
    Read metadata from a raster without modifying it.

    Parameters
    ----------
    path : str
        Path to raster file.

    Returns
    -------
    RasterMetadata
    """

    with rasterio.open(path) as src:
        return RasterMetadata(
            driver=src.driver,
            crs=str(src.crs) if src.crs else None,
            width=src.width,
            height=src.height,
            bands=src.count,
            dtype=src.dtypes[0],
            resolution=src.res,
            bounds=(
                src.bounds.left,
                src.bounds.bottom,
                src.bounds.right,
                src.bounds.top,
            ),
            nodata=src.nodata,
        )
