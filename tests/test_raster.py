import pytest

from geoengine_utils import (
    assess_readiness,
    get_raster_metadata,
    recommend_resampling,
    resample_raster,
)


def test_metadata(raster_path):

    metadata = get_raster_metadata(raster_path)

    assert metadata.width > 0
    assert metadata.height > 0
    assert metadata.crs is not None


def test_validate_raster(raster_path):

    report = assess_readiness(raster_path)

    assert report is not None


def test_recommend_resampling_for_upsampling(raster_path, tmp_path):

    target = tmp_path / "resampled.tif"
    recommendation = recommend_resampling(
        raster_path,
        target_width=200,
        target_height=200,
    )

    assert recommendation.resampling == "cubic"
    assert recommendation.scale_x > 1.0
    assert recommendation.scale_y > 1.0

    result = resample_raster(
        raster_path,
        target,
        target_width=200,
        target_height=200,
    )

    assert result.target_width == 200
    assert target.exists()


def test_recommend_resampling_supports_pixel_size_and_same_dimensions(raster_path):
    pixel = recommend_resampling(raster_path, target_pixel_size=(2, 2))
    same = recommend_resampling(raster_path, target_width=10, target_height=10)
    assert pixel.target_width > 0
    assert same.resampling == "nearest"


def test_resample_raster_rejects_invalid_strategy(raster_path, tmp_path):
    with pytest.raises(ValueError, match="Unsupported"):
        resample_raster(raster_path, tmp_path / "bad.tif", target_width=5, target_height=5, resampling="bad")
