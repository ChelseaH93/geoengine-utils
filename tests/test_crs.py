from shapely.geometry import Point

from geoengine_utils import (
    recommend_crs,
    transform_geometry,
    validate_crs,
)


def test_valid_epsg():

    assert validate_crs("EPSG:4326")


def test_invalid_epsg():

    assert not validate_crs("EPSG:999999")


def test_transform_geometry():

    point = Point(18.4, -33.9)

    transformed = transform_geometry(
        point,
        "EPSG:4326",
        "EPSG:32734",
    )

    assert transformed.x > 0
    assert transformed.y > 0


def test_recommend_crs(cape_town_bbox):

    recommendations = recommend_crs(
        cape_town_bbox
    )

    assert recommendations.global_standard is not None


def test_recommendation_is_utm(cape_town_bbox):

    recommendations = recommend_crs(
        cape_town_bbox
    )

    assert (
        "utm"
        in recommendations.global_standard.name.lower()
    )