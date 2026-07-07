from shapely.geometry import box

from geoengine_utils.crs.recommend import (
    recommend_crs,
    recommend,
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