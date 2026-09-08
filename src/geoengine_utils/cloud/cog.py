"""Cloud Optimized GeoTIFF generation, benchmarking, and recommendations."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, replace
from os import PathLike
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping, Sequence

import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window


@dataclass(frozen=True)
class COGConfiguration:
	"""A raster-to-COG conversion configuration."""

	block_size: int = 256
	compression: str = "deflate"
	compression_level: int | None = 6
	overview_factor: int = 2
	overview_resampling: str = "average"

	def to_dict(self) -> dict[str, Any]:
		return {
			"block_size": self.block_size,
			"compression": self.compression,
			"compression_level": self.compression_level,
			"overview_factor": self.overview_factor,
			"overview_resampling": self.overview_resampling,
		}


@dataclass(frozen=True)
class COGBenchmarkReport:
	"""Measured characteristics of a Cloud Optimized GeoTIFF."""

	archive_path: Path
	elapsed_seconds: float
	read_seconds: float
	file_size_bytes: int
	width: int
	height: int
	band_count: int
	block_shapes: tuple[tuple[int, int], ...]
	overview_levels: tuple[int, ...]
	compression: str | None
	valid: bool
	configuration: COGConfiguration | None = None
	conversion_seconds: float | None = None

	@property
	def pixel_count(self) -> int:
		return self.width * self.height

	def to_dict(self) -> dict[str, Any]:
		return {
			"archive_path": str(self.archive_path),
			"elapsed_seconds": self.elapsed_seconds,
			"read_seconds": self.read_seconds,
			"file_size_bytes": self.file_size_bytes,
			"width": self.width,
			"height": self.height,
			"band_count": self.band_count,
			"block_shapes": [list(shape) for shape in self.block_shapes],
			"overview_levels": list(self.overview_levels),
			"compression": self.compression,
			"valid": self.valid,
			"configuration": self.configuration.to_dict() if self.configuration else None,
			"conversion_seconds": self.conversion_seconds,
		}

	def format_report(self) -> str:
		return (
			f"{self.archive_path}: {self.file_size_bytes:,} bytes, "
			f"{self.width}x{self.height}x{self.band_count}, "
			f"compression={self.compression}, overviews={list(self.overview_levels)}, "
			f"valid={self.valid}, read {self.read_seconds:.3f}s"
		)


@dataclass(frozen=True)
class COGConfigurationSuggestion:
	"""A ranked COG configuration recommendation."""

	recommended: COGBenchmarkReport
	alternatives: tuple[COGBenchmarkReport, ...]
	rationale: str

	def to_dict(self) -> dict[str, Any]:
		return {
			"recommended": self.recommended.to_dict(),
			"alternatives": [report.to_dict() for report in self.alternatives],
			"rationale": self.rationale,
		}


def convert_to_cog(
	source: str | PathLike[str],
	output: str | PathLike[str],
	*,
	configuration: COGConfiguration | None = None,
	**configuration_overrides: Any,
) -> Path:
	"""Create a tiled, overviewed GeoTIFF suitable for cloud access."""

	config = _resolve_configuration(configuration, configuration_overrides)
	_validate_configuration(config)
	output_path = Path(output)
	with rasterio.open(source) as source_dataset:
		profile = source_dataset.profile.copy()
		profile.update(
			driver="GTiff",
			tiled=True,
			blockxsize=config.block_size,
			blockysize=config.block_size,
			compress=config.compression,
			BIGTIFF="IF_SAFER",
		)
		if config.compression_level is not None:
			profile["zlevel"] = config.compression_level
		with rasterio.open(output_path, "w", **profile) as destination:
			for band_index in range(1, source_dataset.count + 1):
				destination.write(source_dataset.read(band_index), band_index)
			levels = _overview_levels(source_dataset.width, source_dataset.height, config.overview_factor)
			if levels:
				destination.build_overviews(levels, _resampling(config.overview_resampling))
				destination.update_tags(ns="rio_overview", resampling=config.overview_resampling)
	return output_path


def benchmark_cog(
	archive: str | PathLike[str],
	*,
	sample_reads: int = 25,
) -> COGBenchmarkReport:
	"""Measure COG structure, size, and representative aligned block reads."""

	if sample_reads <= 0:
		raise ValueError("sample_reads must be greater than zero")
	archive_path = Path(archive)
	started = time.perf_counter()
	with rasterio.open(archive_path) as dataset:
		read_started = time.perf_counter()
		random_source = random.Random(0)
		windows = _sample_windows(dataset, sample_reads, random_source)
		for window in windows:
			dataset.read(1, window=window)
		read_seconds = time.perf_counter() - read_started
		block_shapes = tuple(dataset.block_shapes)
		overview_levels = tuple(dataset.overviews(1))
		requires_overviews = max(dataset.width, dataset.height) >= 128
		valid = (
			dataset.driver == "GTiff"
			and dataset.profile.get("tiled", False)
			and (bool(overview_levels) or not requires_overviews)
		)
		if any(width <= 0 or height <= 0 for width, height in block_shapes):
			valid = False
		return COGBenchmarkReport(
			archive_path=archive_path,
			elapsed_seconds=time.perf_counter() - started,
			read_seconds=read_seconds,
			file_size_bytes=archive_path.stat().st_size,
			width=dataset.width,
			height=dataset.height,
			band_count=dataset.count,
			block_shapes=block_shapes,
			overview_levels=overview_levels,
			compression=dataset.compression.value.lower() if dataset.compression else None,
			valid=valid,
		)


def benchmark_cog_configurations(
	source: str | PathLike[str],
	configurations: Sequence[COGConfiguration | Mapping[str, Any]],
	*,
	sample_reads: int = 25,
) -> tuple[COGBenchmarkReport, ...]:
	"""Generate and benchmark each COG candidate in a temporary directory."""

	if not configurations:
		raise ValueError("configurations must contain at least one candidate")
	results: list[COGBenchmarkReport] = []
	with TemporaryDirectory() as temporary_directory:
		for index, candidate in enumerate(configurations):
			configuration = (
				candidate
				if isinstance(candidate, COGConfiguration)
				else COGConfiguration(**candidate)
			)
			output = Path(temporary_directory) / f"candidate-{index}.tif"
			started = time.perf_counter()
			convert_to_cog(source, output, configuration=configuration)
			conversion_seconds = time.perf_counter() - started
			report = benchmark_cog(output, sample_reads=sample_reads)
			results.append(
				replace(report, configuration=configuration, conversion_seconds=conversion_seconds)
			)
	return tuple(results)


def suggest_cog_configuration(
	reports: Sequence[COGBenchmarkReport],
	*,
	target_read_seconds: float | None = None,
) -> COGConfigurationSuggestion:
	"""Rank valid COGs by size, optionally enforcing a read-time target."""

	if not reports:
		raise ValueError("reports must contain at least one benchmark report")
	if target_read_seconds is not None and target_read_seconds <= 0:
		raise ValueError("target_read_seconds must be greater than zero")

	def score(report: COGBenchmarkReport) -> tuple[int, float, int, float]:
		read_over_target = (
			max(0.0, report.read_seconds - target_read_seconds)
			if target_read_seconds is not None
			else 0.0
		)
		return (
			0 if report.valid else 1,
			read_over_target,
			report.file_size_bytes,
			report.conversion_seconds or 0.0,
		)

	ranked = tuple(sorted(reports, key=score))
	recommended = ranked[0]
	rationale = "The recommendation prioritizes valid COG structure and the smallest archive."
	if target_read_seconds is not None:
		rationale = (
		f"The recommendation prioritizes valid COG structure and meeting the "
		f"{target_read_seconds:.3f}s read target, then minimizes archive size."
	)
	return COGConfigurationSuggestion(recommended, ranked[1:], rationale)


def _resolve_configuration(
	configuration: COGConfiguration | None,
	overrides: Mapping[str, Any],
) -> COGConfiguration:
	if configuration is not None and overrides:
		raise ValueError("pass configuration or configuration overrides, not both")
	return configuration or COGConfiguration(**overrides)


def _validate_configuration(configuration: COGConfiguration) -> None:
	if configuration.block_size < 16 or configuration.block_size > 4096:
		raise ValueError("block_size must be between 16 and 4096")
	if configuration.block_size & (configuration.block_size - 1):
		raise ValueError("block_size must be a power of two")
	if configuration.compression_level is not None and not 1 <= configuration.compression_level <= 9:
		raise ValueError("compression_level must be between 1 and 9")
	if configuration.overview_factor < 2:
		raise ValueError("overview_factor must be at least 2")
	_resampling(configuration.overview_resampling)


def _overview_levels(width: int, height: int, factor: int) -> list[int]:
	levels = []
	level = factor
	while max(width, height) // level >= 64:
		levels.append(level)
		level *= factor
	return levels


def _resampling(name: str) -> Resampling:
	try:
		return getattr(Resampling, name.lower())
	except AttributeError as exc:
		raise ValueError(f"unsupported overview_resampling: {name}") from exc


def _sample_windows(dataset: rasterio.io.DatasetReader, count: int, random_source: random.Random) -> list[Window]:
	block_height, block_width = dataset.block_shapes[0]
	max_row = max(0, dataset.height - block_height)
	max_col = max(0, dataset.width - block_width)
	return [
		Window(
			row_off=(random_source.randint(0, max_row) // block_height) * block_height,
			col_off=(random_source.randint(0, max_col) // block_width) * block_width,
			width=min(block_width, dataset.width),
			height=min(block_height, dataset.height),
		)
		for _ in range(count)
	]


__all__ = [
	"COGBenchmarkReport",
	"COGConfiguration",
	"COGConfigurationSuggestion",
	"benchmark_cog",
	"benchmark_cog_configurations",
	"convert_to_cog",
	"suggest_cog_configuration",
]
