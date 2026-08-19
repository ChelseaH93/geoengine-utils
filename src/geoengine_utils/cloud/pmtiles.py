"""Preflight and streaming helpers for PMTiles conversion workflows."""

from __future__ import annotations

from collections import defaultdict
from os import PathLike
from pathlib import Path
from typing import Any, Iterator, Sequence

import geopandas as gpd
from pyproj import CRS
from shapely.geometry import box

from ..validation import ValidationReport, assess_readiness


def assess_pmtiles_input(source: Any) -> ValidationReport:
	"""Run data quality checks before converting a vector dataset to PMTiles.

	The checks cover readability, feature presence, CRS presence, empty and
	invalid geometries, finite bounds, and mixed geometry types. A geographic
	CRS is recommended because vector tile coordinates are geographic, but a
	projected CRS is reported as a warning so callers can reproject explicitly
	as part of their conversion pipeline.
	"""

	report = assess_readiness(source)
	if not report.passed:
		return report

	data = _read_vector_source(source)
	if data.crs is None:
		report.add_error("PMTiles input must have a CRS defined.")
	else:
		crs = CRS.from_user_input(data.crs)
		if not crs.is_geographic:
			report.add_warning(
				"PMTiles input uses a projected CRS; reproject to EPSG:4326 before tiling."
			)

	bounds = data.total_bounds
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

	report = assess_pmtiles_input(source)
	if not report.passed:
		raise ValueError(f"PMTiles preflight failed: {report.format_report()}")

	frame = _read_vector_source(source)
	if frame.crs is None:
		raise ValueError("PMTiles input must have a CRS defined")
	frame = frame.to_crs("EPSG:4326")
	bounds = tuple(float(value) for value in frame.total_bounds)
	tile_features: dict[int, list[dict[str, Any]]] = defaultdict(list)

	for batch in _iter_vector_frames(source, frame, batch_size=batch_size):
		_encode_batch_tiles(
			batch.to_crs("EPSG:3857"),
			tile_features,
			layer_name=layer_name,
			min_zoom=min_zoom,
			max_zoom=max_zoom,
			clip=clip,
			simplify=simplify,
			simplify_factor=simplify_factor,
		)

	from pmtiles.tile import Compression, TileType, tileid_to_zxy
	from pmtiles.writer import Writer

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
	with output_path.open("wb") as handle:
		writer = Writer(handle)
		for tileid, features in sorted(tile_features.items()):
			zoom, tile_x, tile_y = tileid_to_zxy(tileid)
			payload = _encode_tile(
				features,
				layer_name=layer_name,
				zoom=zoom,
				tile_x=tile_x,
				tile_y=tile_y,
			)
			writer.write_tile(tileid, payload)
		writer.finalize(header, metadata)

	return output_path


def _encode_batch_tiles(
	frame: gpd.GeoDataFrame,
	tile_features: dict[int, list[dict[str, Any]]],
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
					tile_features[zxy_to_tileid(zoom, tile_x, tile_y)].extend(features)


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
	if isinstance(source, (str, PathLike)) and Path(source).suffix.lower() in {
		".parquet",
		".geoparquet",
	}:
		for batch in iter_pyarrow_batches(source, batch_size=batch_size):
			yield gpd.GeoDataFrame.from_arrow(batch)
		return

	for start in range(0, len(frame), batch_size):
		yield frame.iloc[start : start + batch_size]


def _is_finite(value: Any) -> bool:
	return value is not None and float(value) == float(value) and abs(float(value)) != float("inf")


__all__ = ["assess_pmtiles_input", "convert_vector_to_pmtiles", "iter_pyarrow_batches"]
