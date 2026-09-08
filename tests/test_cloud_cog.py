import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from geoengine_utils.cloud import (
	COGConfiguration,
	benchmark_cog,
	benchmark_cog_configurations,
	convert_to_cog,
	suggest_cog_configuration,
)


def _write_raster(path, *, size=256):
	with rasterio.open(
		path,
		"w",
		driver="GTiff",
		width=size,
		height=size,
		count=1,
		dtype="float32",
		crs="EPSG:4326",
		transform=from_origin(-180, 90, 360 / size, 180 / size),
	) as dataset:
		dataset.write(np.arange(size * size, dtype="float32").reshape(size, size), 1)


def test_convert_to_cog_creates_tiled_overviewed_raster(tmp_path):
	source = tmp_path / "source.tif"
	output = tmp_path / "output.tif"
	_write_raster(source)

	result = convert_to_cog(source, output, block_size=128)

	assert result == output
	report = benchmark_cog(output, sample_reads=2)
	assert report.valid is True
	assert report.block_shapes == ((128, 128),)
	assert report.overview_levels == (2, 4)
	assert report.compression == "deflate"


def test_benchmark_cog_configurations_and_suggest(tmp_path):
	source = tmp_path / "source.tif"
	_write_raster(source)
	configurations = [
		COGConfiguration(block_size=128, compression="deflate", compression_level=6),
		{"block_size": 64, "compression": "lzw", "compression_level": None},
	]

	reports = benchmark_cog_configurations(source, configurations, sample_reads=2)
	suggestion = suggest_cog_configuration(reports, target_read_seconds=1.0)

	assert len(reports) == 2
	assert all(report.valid for report in reports)
	assert all(report.configuration is not None for report in reports)
	assert suggestion.recommended.configuration is not None
	assert len(suggestion.alternatives) == 1
	assert suggestion.to_dict()["recommended"]["valid"] is True


def test_cog_validation_rejects_empty_candidates():
	with pytest.raises(ValueError, match="configurations"):
		benchmark_cog_configurations("source.tif", [])