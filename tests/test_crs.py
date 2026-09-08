from pathlib import Path
from types import SimpleNamespace

import geopandas as gpd
import pytest
from shapely.geometry import box

from geoengine_utils.crs.country_lookup import (
    _build_country_frame,
    get_countries,
    get_country,
    get_country_centroid,
)
from geoengine_utils.crs.recommend import (
    estimate_crs,
    recommend,
    recommend_crs,
    score_crs,
)
from geoengine_utils.crs.transform import transform_geometry


def test_recommendation_has_reason():

    result = recommend(country="South Africa")

    assert result.reason
    assert result.recommended.code


def test_alternatives_are_scored():

    result = recommend(country="South Africa")

    for crs in result.alternatives:
        assert isinstance(crs.score, int)


def test_recommend_geometry():

    geometry = box(
        18,
        -35,
        25,
        -22,
    )

    result = recommend_crs(geometry)

    assert result.recommended


def test_recommend_geometry_in_england_uses_british_national_grid():

    geometry = box(-5.8, 49.8, 1.8, 55.9)

    result = recommend_crs(geometry)

    assert result.recommended.code == "27700"


def test_recommend_country():

    result = recommend(country="South Africa")

    assert result.recommended.code == "32734"


def test_estimate_crs_from_vector_path():

    path = Path(__file__).parent / "data" / "test_polygon.geojson"

    result = estimate_crs(path)

    assert result.recommended
    assert result.recommended.code


def test_estimate_crs_from_projected_vector():

    data = gpd.GeoDataFrame(
        geometry=[box(200000, 6200000, 210000, 6210000)],
        crs="EPSG:32734",
    )

    result = estimate_crs(data)

    assert result.recommended.code == "2054"


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


def test_country_lookup_builds_fallback_and_centroid():
    get_countries.cache_clear()
    countries = _build_country_frame([{"ADMIN": "Testland", "geometry": box(1, 2, 3, 4)}])
    assert countries.iloc[0]["recommended_crs"] == "EPSG:32631"

    row = get_country("France")
    centroid = get_country_centroid("France")
    assert row["ADMIN"] == "France"
    assert centroid["utm_epsg"] == 32631

    with pytest.raises(ValueError, match="not found"):
        get_country("Missingland")


def test_transform_geometry_reprojects_coordinates():
    transformed = transform_geometry(box(0, 0, 1, 1), "EPSG:4326", "EPSG:3857")
    assert transformed.bounds[2] > 100_000
