import geopandas as gpd
from shapely.geometry import Point

from geoengine_utils.vector import convert_vector, simplify_vector, validate_vector


def test_convert_vector_from_geometries():
    geometries = [Point(0, 0), Point(1, 1)]

    result = convert_vector(geometries)

    assert isinstance(result, gpd.GeoDataFrame)
    assert len(result) == 2


def test_validate_vector_rejects_non_geometric_input():
    assert validate_vector(["not", "valid"]) is False


def test_simplify_vector_returns_a_new_geodataframe():
    original = gpd.GeoDataFrame(
        {"name": ["a"]},
        geometry=[Point(0, 0)],
        crs="EPSG:4326",
    )

    simplified = simplify_vector(original, tolerance=0.0)

    assert isinstance(simplified, gpd.GeoDataFrame)
    assert simplified is not original
    assert simplified.crs == original.crs
