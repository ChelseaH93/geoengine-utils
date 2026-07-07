from geoengine_utils import (
    get_raster_metadata,
    validate_raster,
)


def test_metadata(raster_path):

    metadata = get_raster_metadata(
        raster_path
    )

    assert metadata.width > 0
    assert metadata.height > 0
    assert metadata.crs is not None


def test_validate_raster(raster_path):

    report = validate_raster(
        raster_path
    )

    assert report is not None