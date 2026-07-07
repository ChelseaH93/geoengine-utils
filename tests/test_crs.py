from pathlib import Path
from types import SimpleNamespace

import pytest
from shapely.geometry import box

from geoengine_utils.crs.recommend import (
    recommend_crs,
    recommend,
    estimate_crs,
    score_crs,
)

def test_recommendation_has_reason():

    result = recommend(
        country="South Africa"
    )

    assert result.reason
    assert result.recommended.code

def test_alternatives_are_scored():

    result = recommend(
        country="South Africa"
    )

    for crs in result.alternatives:
        assert isinstance(
            crs.score,
            int
        )

def test_recommend_geometry():

    geometry = box(
        18,
        -35,
        25,
        -22,
    )

    result = recommend_crs(
        geometry
    )

    assert result.recommended



def test_recommend_country():

    result = recommend(
        country="South Africa"
    )

    assert (
        result.recommended.code
        == "32734"
    )


def test_estimate_crs_from_vector_path():

    path = Path(__file__).parent / "data" / "test_polygon.geojson"

    result = estimate_crs(path)

    assert result.recommended
    assert result.recommended.code


def test_score_crs_prefers_expected_utm_zone():

    expected = SimpleNamespace(
        name="WGS 84 / UTM zone 34S",
        area_of_use=SimpleNamespace(name="South Africa"),
        to_authority=lambda: ("EPSG", "32734"),
    )
    nearby = SimpleNamespace(
        name="WGS 84 / UTM zone 35S",
        area_of_use=SimpleNamespace(name="South Africa"),
        to_authority=lambda: ("EPSG", "32735"),
    )

    assert score_crs(expected, lon=18.4, lat=-33.9) > score_crs(
        nearby,
        lon=18.4,
        lat=-33.9,
    )


def test_estimate_crs_from_raster_path(raster_path):

    result = estimate_crs(raster_path)

    assert result.recommended
    assert result.recommended.code


def test_estimate_crs_invalid_input_raises():

    with pytest.raises(TypeError):
        estimate_crs(42)


def test_estimate_crs_no_matching_crs_raises():

    with pytest.raises(ValueError):
        recommend_crs((1000, 1000, 1001, 1001))


def test_recommend_country_uses_country_override():

    result = recommend(country="South Africa")

    assert result.recommended.code == "32734"
    assert result.reason