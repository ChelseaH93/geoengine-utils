import geopandas as gpd
from shapely.geometry import Point, Polygon

from geoengine_utils.validation import assess_readiness
from geoengine_utils.vector import convert_vector, repair_vector, simplify_vector


def test_convert_vector_from_geometries():
    geometries = [Point(0, 0), Point(1, 1)]

    result = convert_vector(geometries)

    assert isinstance(result, gpd.GeoDataFrame)
    assert len(result) == 2


def test_validate_vector_rejects_non_geometric_input():
    report = assess_readiness(["not", "valid"])

    assert report.passed is False


def test_assess_readiness_accepts_a_geodataframe_directly():
    frame = gpd.GeoDataFrame(
        {"name": ["a"]},
        geometry=[Point(0, 0)],
        crs="EPSG:4326",
    )

    report = assess_readiness(frame)

    assert report.passed is True


def test_assess_readiness_flags_invalid_geometries_as_a_warning():
    bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    frame = gpd.GeoDataFrame(geometry=[bowtie], crs="EPSG:4326")

    report = assess_readiness(frame)

    assert any("invalid" in warning.lower() for warning in report.warnings)


def test_assess_readiness_flags_empty_geometries_as_an_error():
    frame = gpd.GeoDataFrame(geometry=[Polygon(), Point(0, 0)], crs="EPSG:4326")

    report = assess_readiness(frame)

    assert report.passed is False
    assert any("empty" in error.lower() for error in report.errors)


def test_assess_readiness_flags_mixed_geometry_types_as_a_warning():
    frame = gpd.GeoDataFrame(
        geometry=[Point(0, 0), Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])],
        crs="EPSG:4326",
    )

    report = assess_readiness(frame)

    assert any("mixes multiple geometry types" in warning.lower() for warning in report.warnings)


def test_assess_readiness_auto_detects_a_vector_file(tmp_path):
    frame = gpd.GeoDataFrame(geometry=[Point(0, 0)], crs="EPSG:4326")
    path = tmp_path / "points.geojson"
    frame.to_file(path, driver="GeoJSON")

    report = assess_readiness(path)

    assert report.passed is True


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


def test_repair_vector_repairs_invalid_geometries_without_mutating_input():
    bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    original = gpd.GeoDataFrame(
        {"name": ["invalid"]},
        geometry=[bowtie],
        index=[7],
        crs="EPSG:4326",
    )

    repaired = repair_vector(original)

    assert repaired is not original
    assert repaired.index.tolist() == [7]
    assert repaired["name"].tolist() == ["invalid"]
    assert repaired.crs == original.crs
    assert repaired.geometry.is_valid.all()
    assert not original.geometry.is_valid.all()


def test_repair_vector_can_drop_empty_geometries():
    original = gpd.GeoDataFrame(
        geometry=[Polygon(), Point(0, 0)],
        crs="EPSG:4326",
    )

    repaired = repair_vector(original, drop_empty=True)

    assert len(repaired) == 1
    assert repaired.geometry.iloc[0].equals(Point(0, 0))
