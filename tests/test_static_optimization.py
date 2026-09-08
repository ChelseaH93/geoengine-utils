import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from geoengine_utils.optimization import (
    StaticDataConfiguration,
    benchmark_static_configurations,
    benchmark_static_dataset,
    suggest_static_optimization,
)


def _frame():
    return gpd.GeoDataFrame(
        {"name": ["a", "b"], "value": [1, 2]},
        geometry=[
            Polygon([(-87.7, 41.7), (-87.6, 41.7), (-87.6, 41.8), (-87.7, 41.7)]),
            Polygon([(-87.8, 41.8), (-87.7, 41.8), (-87.7, 41.9), (-87.8, 41.8)]),
        ],
        crs="EPSG:4326",
    )


def test_benchmark_static_dataset_counts_shapefile_sidecars(tmp_path):
    path = tmp_path / "source.shp"
    _frame().to_file(path, driver="ESRI Shapefile")

    report = benchmark_static_dataset(path)

    assert report.format == "shapefile"
    assert report.feature_count == 2
    assert report.storage_bytes > path.stat().st_size
    assert report.geometry_types == ("Polygon",)


def test_benchmark_static_configurations_supports_all_formats():
    reports = benchmark_static_configurations(
        _frame(),
        [
            StaticDataConfiguration("geoparquet", compression="zstd"),
            StaticDataConfiguration("geopackage"),
            StaticDataConfiguration("shapefile"),
            StaticDataConfiguration("geojson"),
        ],
    )

    assert [report.format for report in reports] == [
        "geoparquet",
        "geopackage",
        "shapefile",
        "geojson",
    ]
    assert all(report.feature_count == 2 for report in reports)
    assert all(report.storage_bytes > 0 for report in reports)
    assert all(report.read_seconds >= 0 for report in reports)


def test_suggest_static_optimization_prioritizes_read_target_then_size():
    reports = benchmark_static_configurations(
        _frame(),
        [
            {"format": "geoparquet", "compression": "zstd"},
            {"format": "geojson"},
        ],
    )

    suggestion = suggest_static_optimization(reports, target_read_seconds=1.0)

    assert suggestion.recommended.format in {"geoparquet", "geojson"}
    assert len(suggestion.alternatives) == 1
    assert suggestion.to_dict()["recommended"]["configuration"] is not None


def test_static_optimization_rejects_unknown_formats():
    with pytest.raises(ValueError, match="unsupported format"):
        benchmark_static_configurations(_frame(), [{"format": "topojson"}])
