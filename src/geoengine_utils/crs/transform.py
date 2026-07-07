from pyproj import Transformer
from shapely.ops import transform


def transform_geometry(
    geometry,
    source_crs,
    destination_crs,
):
    """
    Transform a Shapely geometry between coordinate systems.
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