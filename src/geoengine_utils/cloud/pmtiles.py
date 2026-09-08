"""Preflight and streaming helpers for PMTiles conversion workflows."""

from __future__ import annotations

import json
import math
import random
import sqlite3
import time
from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass, replace
from os import PathLike
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterator, Mapping, Sequence

import geopandas as gpd
from pyproj import CRS
from shapely.geometry import box

from ..validation import ValidationReport, assess_readiness


@dataclass(frozen=True)
class PMTilesBenchmarkReport:
	"""Measured characteristics of a PMTiles archive."""

	archive_path: Path
	elapsed_seconds: float
	read_seconds: float
	file_size_bytes: int
	tile_count: int
	total_tile_bytes: int
	average_tile_bytes: float
	p95_tile_bytes: float
	max_tile_bytes: int
	min_zoom: int
	max_zoom: int
	addressed_tiles_count: int
	conversion_seconds: float | None = None
	configuration: "PMTilesConfiguration | None" = None

	@property
	def tile_payload_fraction(self) -> float:
		return self.total_tile_bytes / self.file_size_bytes if self.file_size_bytes else 0.0

	def to_dict(self) -> dict[str, Any]:
		return {
			"archive_path": str(self.archive_path),
			"elapsed_seconds": self.elapsed_seconds,
			"read_seconds": self.read_seconds,
			"file_size_bytes": self.file_size_bytes,
			"tile_count": self.tile_count,
			"total_tile_bytes": self.total_tile_bytes,
			"average_tile_bytes": self.average_tile_bytes,
			"p95_tile_bytes": self.p95_tile_bytes,
			"max_tile_bytes": self.max_tile_bytes,
			"min_zoom": self.min_zoom,
			"max_zoom": self.max_zoom,
			"addressed_tiles_count": self.addressed_tiles_count,
			"tile_payload_fraction": self.tile_payload_fraction,
			"conversion_seconds": self.conversion_seconds,
			"configuration": self.configuration.to_dict() if self.configuration else None,
		}

	def format_report(self) -> str:
		return (
			f"{self.archive_path}: {self.file_size_bytes:,} bytes, "
			f"{self.tile_count:,} tiles, average tile {self.average_tile_bytes:,.0f} bytes, "
			f"p95 tile {self.p95_tile_bytes:,.0f} bytes, "
			f"zoom {self.min_zoom}-{self.max_zoom}, read {self.read_seconds:.3f}s"
		)


@dataclass(frozen=True)
class PMTilesConfiguration:
	"""A conversion configuration that can be benchmarked."""

	min_zoom: int = 0
	max_zoom: int = 8
	batch_size: int = 10_000
	clip: bool = True
	simplify: bool = True
	simplify_factor: float = 0.5

	def to_dict(self) -> dict[str, Any]:
		return {
			"min_zoom": self.min_zoom,
			"max_zoom": self.max_zoom,
			"batch_size": self.batch_size,
			"clip": self.clip,
			"simplify": self.simplify,
			"simplify_factor": self.simplify_factor,
		}


@dataclass(frozen=True)
class PMTilesConfigurationSuggestion:
	"""A ranked recommendation based on benchmarked configurations."""

	recommended: PMTilesBenchmarkReport
	alternatives: tuple[PMTilesBenchmarkReport, ...]
	rationale: str

	def to_dict(self) -> dict[str, Any]:
		return {
			"recommended": self.recommended.to_dict(),
			"alternatives": [report.to_dict() for report in self.alternatives],
			"rationale": self.rationale,
		}


def benchmark_pmtiles_archive(
	archive: str | PathLike[str],
	*,
	sample_tiles: int = 1_000,
) -> PMTilesBenchmarkReport:
	"""Benchmark archive size, tile density, and representative read latency.

	Tile sizes are sampled with a deterministic reservoir, so large archives do
	not require retaining every tile payload in memory. ``sample_tiles`` also
	controls how many tile reads are timed after the archive scan.
	"""

	if sample_tiles <= 0:
		raise ValueError("sample_tiles must be greater than zero")

	from pmtiles.reader import MmapSource, Reader, all_tiles

	archive_path = Path(archive)
	started = time.perf_counter()
	tile_sizes: list[int] = []
	tile_ids: list[tuple[int, int, int]] = []
	total_tile_bytes = 0
	tile_count = 0
	random_source = random.Random(0)
	with archive_path.open("rb") as handle:
		source = MmapSource(handle)
		reader = Reader(source)
		header = reader.header()
		scan_started = time.perf_counter()
		for index, (zxy, payload) in enumerate(all_tiles(source)):
			tile_count += 1
			total_tile_bytes += len(payload)
			if len(tile_sizes) < sample_tiles:
				tile_sizes.append(len(payload))
			else:
				position = random_source.randint(0, index)
				if position < sample_tiles:
					tile_sizes[position] = len(payload)
			if len(tile_ids) < sample_tiles:
				tile_ids.append(zxy)
		for zoom, tile_x, tile_y in tile_ids:
			reader.get(zoom, tile_x, tile_y)
		read_seconds = time.perf_counter() - scan_started

	sorted_sizes = sorted(tile_sizes)
	p95_index = min(len(sorted_sizes) - 1, math.ceil(len(sorted_sizes) * 0.95) - 1)
	return PMTilesBenchmarkReport(
		archive_path=archive_path,
		elapsed_seconds=time.perf_counter() - started,
		read_seconds=read_seconds,
		file_size_bytes=archive_path.stat().st_size,
		tile_count=tile_count,
		total_tile_bytes=total_tile_bytes,
		average_tile_bytes=total_tile_bytes / tile_count if tile_count else 0.0,
		p95_tile_bytes=float(sorted_sizes[p95_index]) if sorted_sizes else 0.0,
		max_tile_bytes=max(tile_sizes, default=0),
		min_zoom=header["min_zoom"],
		max_zoom=header["max_zoom"],
		addressed_tiles_count=header["addressed_tiles_count"],
	)


def benchmark_pmtiles_configurations(
	source: Any,
	configurations: Sequence[PMTilesConfiguration | Mapping[str, Any]],
	*,
	sample_tiles: int = 1_000,
) -> tuple[PMTilesBenchmarkReport, ...]:
	"""Convert and benchmark each candidate configuration in a temp directory."""

	if not configurations:
		raise ValueError("configurations must contain at least one candidate")
	results: list[PMTilesBenchmarkReport] = []
	with TemporaryDirectory() as temporary_directory:
		for index, candidate in enumerate(configurations):
			configuration = (
				candidate
				if isinstance(candidate, PMTilesConfiguration)
				else PMTilesConfiguration(**candidate)
			)
			output = Path(temporary_directory) / f"candidate-{index}.pmtiles"
			started = time.perf_counter()
			convert_vector_to_pmtiles(source, output, **configuration.to_dict())
			conversion_seconds = time.perf_counter() - started
			report = benchmark_pmtiles_archive(output, sample_tiles=sample_tiles)
			results.append(
				replace(report, conversion_seconds=conversion_seconds, configuration=configuration)
			)
	return tuple(results)


def suggest_pmtiles_configuration(
	reports: Sequence[PMTilesBenchmarkReport],
	*,
	target_p95_tile_bytes: int = 50_000,
) -> PMTilesConfigurationSuggestion:
	"""Rank benchmark results, preferring small tiles and shorter conversions."""

	if not reports:
		raise ValueError("reports must contain at least one benchmark report")
	if target_p95_tile_bytes <= 0:
		raise ValueError("target_p95_tile_bytes must be greater than zero")

	def score(report: PMTilesBenchmarkReport) -> tuple[float, float, float]:
		over_target = max(0.0, report.p95_tile_bytes - target_p95_tile_bytes)
		return (over_target, report.file_size_bytes, report.conversion_seconds or 0.0)

	ranked = tuple(sorted(reports, key=score))
	recommended = ranked[0]
	if recommended.p95_tile_bytes <= target_p95_tile_bytes:
		rationale = (
			f"The recommended configuration keeps the measured p95 tile below "
			f"the {target_p95_tile_bytes:,}-byte target while minimizing archive size."
		)
	else:
		rationale = (
			f"No candidate meets the {target_p95_tile_bytes:,}-byte p95 tile target; "
			"the recommendation minimizes the amount by which candidates exceed it."
		)
	return PMTilesConfigurationSuggestion(recommended, ranked[1:], rationale)


def assess_pmtiles_input(source: Any, *, batch_size: int = 10_000) -> ValidationReport:
	"""Run data quality checks before converting a vector dataset to PMTiles.

	The checks cover readability, feature presence, CRS presence, empty and
	invalid geometries, finite bounds, and mixed geometry types. A geographic
	CRS is recommended because vector tile coordinates are geographic, but a
	projected CRS is reported as a warning so callers can reproject explicitly
	as part of their conversion pipeline.
	"""

	report = assess_readiness(source, batch_size=batch_size)
	if not report.passed:
		return report

	if _is_parquet_source(source):
		crs, bounds = _stream_parquet_summary(source, batch_size=batch_size)
	else:
		data = _read_vector_source(source)
		crs, bounds = data.crs, data.total_bounds

	if crs is None:
		report.add_error("PMTiles input must have a CRS defined.")
	else:
		parsed_crs = CRS.from_user_input(crs)
		if not parsed_crs.is_geographic:
			report.add_warning(
				"PMTiles input uses a projected CRS; reproject to EPSG:4326 before tiling."
			)

	if len(bounds) != 4 or not all(_is_finite(value) for value in bounds):
		report.add_error("PMTiles input has non-finite or unavailable bounds.")

	return report


def iter_pyarrow_batches(
	source: str | PathLike[str],
	*,
	batch_size: int = 10_000,
	columns: Sequence[str] | None = None,
) -> Iterator[Any]:
	"""Stream a Parquet or GeoParquet dataset as bounded PyArrow batches.

	PyArrow is imported lazily so the rest of the package remains usable
	without the optional cloud dependencies. Each yielded item is a
	``pyarrow.RecordBatch`` and is released by the caller after conversion.
	"""

	if batch_size <= 0:
		raise ValueError("batch_size must be greater than zero")

	try:
		import pyarrow.dataset as pads
	except ImportError as exc:
		raise ImportError(
			"PyArrow is required for streaming Parquet batches. "
			"Install the cloud extra with `pip install geoengine-utils[cloud]`."
		) from exc

	dataset = pads.dataset(Path(source), format="parquet")
	yield from dataset.scanner(columns=columns, batch_size=batch_size).to_batches()


def convert_vector_to_pmtiles(
	source: Any,
	output: str | PathLike[str],
	*,
	layer_name: str = "data",
	min_zoom: int = 0,
	max_zoom: int = 8,
	batch_size: int = 10_000,
	clip: bool = True,
	simplify: bool = True,
	simplify_factor: float = 0.5,
) -> Path:
	"""Convert a vector dataset to a PMTiles archive using bounded batches.

	Parquet and GeoParquet sources are read with PyArrow record batches. Other
	vector sources are read with GeoPandas and processed in DataFrame chunks.
	Parquet and GeoParquet sources are streamed as Arrow record batches. Each
	batch is reprojected to Web Mercator, spatially indexed, clipped to tile
	bounds, and simplified according to its zoom before MVT encoding.
	"""

	if min_zoom < 0 or max_zoom < min_zoom or max_zoom > 22:
		raise ValueError("zoom range must satisfy 0 <= min_zoom <= max_zoom <= 22")
	if batch_size <= 0:
		raise ValueError("batch_size must be greater than zero")
	if simplify_factor < 0:
		raise ValueError("simplify_factor must be greater than or equal to zero")

	report = assess_pmtiles_input(source, batch_size=batch_size)
	if not report.passed:
		raise ValueError(f"PMTiles preflight failed: {report.format_report()}")

	from pmtiles.tile import Compression, TileType, tileid_to_zxy
	from pmtiles.writer import Writer

	if _is_parquet_source(source):
		crs, bounds = _stream_parquet_summary(source, batch_size=batch_size)
		frame = None
	else:
		frame = _read_vector_source(source)
		crs, bounds = frame.crs, frame.total_bounds
	if crs is None:
		raise ValueError("PMTiles input must have a CRS defined")

	output_path = Path(output)
	header = {
		"tile_compression": Compression.GZIP,
		"tile_type": TileType.MVT,
		"min_zoom": min_zoom,
		"max_zoom": max_zoom,
		"min_lon_e7": round(bounds[0] * 10_000_000),
		"min_lat_e7": round(bounds[1] * 10_000_000),
		"max_lon_e7": round(bounds[2] * 10_000_000),
		"max_lat_e7": round(bounds[3] * 10_000_000),
	}
	metadata = {
		"name": output_path.stem,
		"format": "pbf",
		"type": "overlay",
		"version": "1.0",
		"vector_layers": [{"id": layer_name, "fields": {}}],
	}
	with TemporaryDirectory() as temporary_directory:
		store_path = Path(temporary_directory) / "tile_features.sqlite"
		with closing(sqlite3.connect(store_path)) as tile_store:
			tile_store.execute(
				"CREATE TABLE tile_features (tile_id INTEGER, feature_json TEXT)"
			)
			tile_store.execute("CREATE INDEX tile_features_tile_id ON tile_features(tile_id)")

			for batch in _iter_vector_frames(source, frame, batch_size=batch_size):
				_encode_batch_tiles(
					batch.to_crs("EPSG:3857"),
					tile_store,
					layer_name=layer_name,
					min_zoom=min_zoom,
					max_zoom=max_zoom,
					clip=clip,
					simplify=simplify,
					simplify_factor=simplify_factor,
				)
			tile_store.commit()

			with output_path.open("wb") as handle:
				writer = Writer(handle)
				tile_rows = tile_store.execute(
					"SELECT tile_id, feature_json FROM tile_features ORDER BY tile_id"
				)
				current_tile_id = None
				features = []
				for tile_id, feature_json in tile_rows:
					if current_tile_id is not None and tile_id != current_tile_id:
						zoom, tile_x, tile_y = tileid_to_zxy(current_tile_id)
						writer.write_tile(
							current_tile_id,
							_encode_tile(
								features,
								layer_name=layer_name,
								zoom=zoom,
								tile_x=tile_x,
								tile_y=tile_y,
							),
						)
						features = []
					current_tile_id = tile_id
					features.append(json.loads(feature_json))
				if current_tile_id is not None:
					zoom, tile_x, tile_y = tileid_to_zxy(current_tile_id)
					writer.write_tile(
						current_tile_id,
						_encode_tile(
							features,
							layer_name=layer_name,
							zoom=zoom,
							tile_x=tile_x,
							tile_y=tile_y,
						),
					)
				tile_rows.close()
				writer.finalize(header, metadata)

	return output_path


def _encode_batch_tiles(
	frame: gpd.GeoDataFrame,
	tile_store: sqlite3.Connection,
	*,
	layer_name: str,
	min_zoom: int,
	max_zoom: int,
	clip: bool,
	simplify: bool,
	simplify_factor: float,
) -> None:
	from pmtiles.tile import zxy_to_tileid

	for zoom in range(min_zoom, max_zoom + 1):
		grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
		min_lon, min_lat, max_lon, max_lat = _mercator_to_lonlat_bounds(frame.total_bounds)
		min_tile_x = _lon_to_tile(min_lon, zoom)
		max_tile_x = _lon_to_tile(max_lon, zoom)
		min_tile_y = _lat_to_tile(max_lat, zoom)
		max_tile_y = _lat_to_tile(min_lat, zoom)
		spatial_index = frame.sindex
		tile_width = 40075016.68557849 / (1 << zoom)

		for tile_x in range(min_tile_x, max_tile_x + 1):
			for tile_y in range(min_tile_y, max_tile_y + 1):
				west, south, east, north = _tile_bounds_mercator(tile_x, tile_y, zoom)
				tile_geometry = box(west, south, east, north)
				candidate_indexes = spatial_index.query(tile_geometry, predicate="intersects")
				features = []
				for index in candidate_indexes:
					row = frame.iloc[index]
					geometry = row.geometry
					if clip:
						geometry = geometry.intersection(tile_geometry)
					if simplify and not geometry.is_empty:
						geometry = geometry.simplify(
							tolerance=tile_width / 4096 * simplify_factor,
							preserve_topology=True,
						)
					if geometry.is_empty:
						continue
					properties = {
						str(key): value
						for key, value in row.items()
						if key != frame.geometry.name and value is not None
					}
					features.append(
						{
							"geometry": geometry.__geo_interface__,
							"properties": properties,
							"id": row.name,
						}
					)

				if features:
					grouped[zxy_to_tileid(zoom, tile_x, tile_y)].extend(features)

		for tile_id, features in grouped.items():
			tile_store.executemany(
				"INSERT INTO tile_features(tile_id, feature_json) VALUES (?, ?)",
				[(tile_id, json.dumps(feature, default=str)) for feature in features],
			)


def _encode_tile(
	features: list[dict[str, Any]],
	*,
	layer_name: str,
	zoom: int,
	tile_x: int,
	tile_y: int,
) -> bytes:
	import gzip

	import mapbox_vector_tile

	west, south, east, north = _tile_bounds_mercator(tile_x, tile_y, zoom)
	encoded = mapbox_vector_tile.encode(
		[{"name": layer_name, "features": features}],
		default_options={
			"quantize_bounds": (west, south, east, north),
			"extents": 4096,
			"y_coord_down": False,
		},
	)
	return gzip.compress(encoded)


def _lon_to_tile(longitude: float, zoom: int) -> int:
	size = 1 << zoom
	return max(0, min(size - 1, int((longitude + 180) / 360 * size)))


def _lat_to_tile(latitude: float, zoom: int) -> int:
	import math

	size = 1 << zoom
	clipped = max(-85.05112878, min(85.05112878, latitude))
	value = (1 - math.asinh(math.tan(math.radians(clipped))) / math.pi) / 2
	return max(0, min(size - 1, int(value * size)))


def _tile_bounds(tile_x: int, tile_y: int, zoom: int) -> tuple[float, float, float, float]:
	import math

	size = 1 << zoom
	west = tile_x / size * 360 - 180
	east = (tile_x + 1) / size * 360 - 180
	north = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * tile_y / size))))
	south = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (tile_y + 1) / size))))
	return west, south, east, north


def _tile_bounds_mercator(
	tile_x: int, tile_y: int, zoom: int
) -> tuple[float, float, float, float]:
	world = 40075016.68557849
	west = tile_x / (1 << zoom) * world - world / 2
	east = (tile_x + 1) / (1 << zoom) * world - world / 2
	north = world / 2 - tile_y / (1 << zoom) * world
	south = world / 2 - (tile_y + 1) / (1 << zoom) * world
	return west, south, east, north


def _mercator_to_lonlat_bounds(
	bounds: Sequence[float],
) -> tuple[float, float, float, float]:
	import math

	minx, miny, maxx, maxy = bounds
	world = 40075016.68557849
	min_lon = minx / world * 360
	max_lon = maxx / world * 360
	min_lat = math.degrees(math.atan(math.sinh(2 * math.pi * miny / world)))
	max_lat = math.degrees(math.atan(math.sinh(2 * math.pi * maxy / world)))
	return min_lon, min_lat, max_lon, max_lat


def _read_vector_source(source: Any) -> gpd.GeoDataFrame:
	if isinstance(source, gpd.GeoDataFrame):
		return source
	if isinstance(source, gpd.GeoSeries):
		return gpd.GeoDataFrame(geometry=source, crs=source.crs)
	if isinstance(source, (str, PathLike)):
		path = Path(source)
		if path.suffix.lower() in {".parquet", ".geoparquet"}:
			return gpd.read_parquet(path)
		return gpd.read_file(path)
	raise TypeError("PMTiles input must be a vector path, GeoDataFrame, or GeoSeries")


def _iter_vector_frames(
	source: Any,
	frame: gpd.GeoDataFrame,
	*,
	batch_size: int,
) -> Iterator[gpd.GeoDataFrame]:
	if _is_parquet_source(source):
		for batch in iter_pyarrow_batches(source, batch_size=batch_size):
			yield gpd.GeoDataFrame.from_arrow(batch)
		return

	for start in range(0, len(frame), batch_size):
		yield frame.iloc[start : start + batch_size]


def _is_parquet_source(source: Any) -> bool:
	return isinstance(source, (str, PathLike)) and Path(source).suffix.lower() in {
		".parquet",
		".geoparquet",
	}


def _stream_parquet_summary(
	source: str | PathLike[str],
	*,
	batch_size: int,
) -> tuple[Any, tuple[float, float, float, float]]:
	crs = None
	minimum_x = minimum_y = float("inf")
	maximum_x = maximum_y = float("-inf")

	for batch in iter_pyarrow_batches(source, batch_size=batch_size):
		frame = gpd.GeoDataFrame.from_arrow(batch)
		if crs is None:
			crs = frame.crs
		minx, miny, maxx, maxy = frame.total_bounds
		minimum_x = min(minimum_x, minx)
		minimum_y = min(minimum_y, miny)
		maximum_x = max(maximum_x, maxx)
		maximum_y = max(maximum_y, maxy)

	return crs, (minimum_x, minimum_y, maximum_x, maximum_y)


def _is_finite(value: Any) -> bool:
	return value is not None and float(value) == float(value) and abs(float(value)) != float("inf")


__all__ = ["assess_pmtiles_input", "convert_vector_to_pmtiles", "iter_pyarrow_batches"]
