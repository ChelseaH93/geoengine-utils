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

    assert recommendations.recommended is not None


def test_cape_town_returns_sa_projection(cape_town_bbox):

    recommendation = recommend_crs(cape_town_bbox)

    assert recommendation.recommended.code == "2054"

def test_london_returns_bng(london_bbox):

    recommendation = recommend_crs(london_bbox)

    assert recommendation.recommended.code == "27700"