from geoengine_utils.validation import assess_readiness


def test_validate_raster_flags_large_resolution(raster_path):
    result = assess_readiness(str(raster_path))

    assert result.passed is True
    assert any("resolution" in warning.lower() for warning in result.warnings)


def test_validate_raster_flags_missing_nodata_as_warning(raster_path):
    result = assess_readiness(str(raster_path))

    assert any("nodata" in warning.lower() for warning in result.warnings)
