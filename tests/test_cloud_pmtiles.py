import geopandas as gpd
import gzip
import mapbox_vector_tile
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from pmtiles.reader import MmapSource, Reader
from shapely.geometry import Point, Polygon

from geoengine_utils.cloud import (
    assess_pmtiles_input,
    convert_vector_to_pmtiles,
    iter_pyarrow_batches,
)


def test_assess_pmtiles_input_accepts_valid_geographic_data():
    frame = gpd.GeoDataFrame(
        geometry=[Point(0, 0)],
        crs="EPSG:4326",
    )

    report = assess_pmtiles_input(frame)

    assert report.passed is True
    assert not report.warnings


def test_assess_pmtiles_input_flags_invalid_geometry():
    bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    frame = gpd.GeoDataFrame(geometry=[bowtie], crs="EPSG:4326")

    report = assess_pmtiles_input(frame)

    assert report.passed is False
    assert any("topology" in error.lower() for error in report.errors)


def test_assess_pmtiles_input_warns_for_projected_crs():
    frame = gpd.GeoDataFrame(geometry=[Point(0, 0)], crs="EPSG:27700")

    report = assess_pmtiles_input(frame)

    assert report.passed is True
    assert any("reproject" in warning.lower() for warning in report.warnings)


def test_iter_pyarrow_batches_streams_bounded_record_batches(tmp_path):
    path = tmp_path / "data.parquet"
    table = pa.table({"id": list(range(5)), "name": ["a", "b", "c", "d", "e"]})
    pq.write_table(table, path)

    batches = list(iter_pyarrow_batches(path, batch_size=2))

    assert [batch.num_rows for batch in batches] == [2, 2, 1]
    assert batches[0].column_names == ["id", "name"]


def test_iter_pyarrow_batches_rejects_invalid_batch_size(tmp_path):
    with pytest.raises(ValueError, match="batch_size"):
        next(iter_pyarrow_batches(tmp_path / "data.parquet", batch_size=0))


def test_convert_vector_to_pmtiles_writes_readable_archive(tmp_path):
    source = tmp_path / "source.geojson"
    output = tmp_path / "output.pmtiles"
    frame = gpd.GeoDataFrame(
        {"name": ["origin", "nearby"]},
        geometry=[Point(0, 0), Point(0.01, 0.01)],
        crs="EPSG:4326",
    )
    frame.to_file(source, driver="GeoJSON")

    result = convert_vector_to_pmtiles(source, output, min_zoom=0, max_zoom=2, batch_size=1)

    assert result == output
    assert output.read_bytes()[:8] == b"PMTiles\x03"
    with output.open("rb") as handle:
        archive = Reader(MmapSource(handle))
        header = archive.header()
        assert header["tile_type"].name == "MVT"
        assert header["addressed_tiles_count"] > 0
        assert archive.metadata()["vector_layers"][0]["id"] == "data"
        tile = archive.get(0, 0, 0)
        assert tile is not None
        decoded = mapbox_vector_tile.decode(gzip.decompress(tile))
        assert len(decoded["data"]["features"]) == 2