"""Raster resampling helpers and recommendation logic."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import rasterio
from rasterio.enums import Resampling


@dataclass(slots=True)
class ResamplingRecommendation:
    """Suggested resampling strategy and factor for a raster."""

    target_width: int
    target_height: int
    scale_x: float
    scale_y: float
    resampling: str
    reason: str


def recommend_resampling(
    path: str | Path,
    *,
    target_width: int | None = None,
    target_height: int | None = None,
    target_pixel_size: tuple[float, float] | None = None,
) -> ResamplingRecommendation:
    """Recommend a resampling strategy for a raster dataset.

    The helper derives a scale factor from either the requested width/height or
    a target pixel size. It also recommends a resampling strategy based on
    whether the raster is being upsampled or downsampled.
    """

    raster_path = Path(path)

    with rasterio.open(raster_path) as src:
        width = src.width
        height = src.height
        transform = src.transform
        pixel_width = abs(transform.a)
        pixel_height = abs(transform.e)

        if target_width is not None and target_height is not None:
            target_width = int(target_width)
            target_height = int(target_height)
        elif target_pixel_size is not None:
            target_pixel_width, target_pixel_height = target_pixel_size
            target_width = max(1, int(round(width * pixel_width / target_pixel_width)))
            target_height = max(1, int(round(height * pixel_height / target_pixel_height)))
        else:
            raise ValueError("Provide either target_width/target_height or target_pixel_size")

        if target_width <= 0 or target_height <= 0:
            raise ValueError("Target width and height must be positive")

        scale_x = target_width / width
        scale_y = target_height / height

        if scale_x > 1.0 or scale_y > 1.0:
            resampling = "upsampling"
            strategy = "cubic"
            reason = "The target dimensions are larger than the source raster, so cubic resampling is a good default for smooth upsampling."
        elif scale_x < 1.0 or scale_y < 1.0:
            resampling = "downsampling"
            strategy = "average"
            reason = "The target dimensions are smaller than the source raster, so average resampling is a good default for reducing aliasing."
        else:
            resampling = "no-change"
            strategy = "nearest"
            reason = "The target dimensions match the source raster, so no resampling is required."

        return ResamplingRecommendation(
            target_width=target_width,
            target_height=target_height,
            scale_x=scale_x,
            scale_y=scale_y,
            resampling=strategy,
            reason=reason,
        )


def resample_raster(
    path: str | Path,
    output_path: str | Path,
    *,
    target_width: int | None = None,
    target_height: int | None = None,
    target_pixel_size: tuple[float, float] | None = None,
    resampling: str | None = None,
) -> ResamplingRecommendation:
    """Resample a raster to a target width, height, or pixel size."""

    recommendation = recommend_resampling(
        path,
        target_width=target_width,
        target_height=target_height,
        target_pixel_size=target_pixel_size,
    )

    strategy = resampling or recommendation.resampling

    mapping = {
        "nearest": Resampling.nearest,
        "bilinear": Resampling.bilinear,
        "cubic": Resampling.cubic,
        "average": Resampling.average,
        "mode": Resampling.mode,
    }

    if strategy not in mapping:
        raise ValueError(f"Unsupported resampling strategy: {strategy}")

    raster_path = Path(path)
    output = Path(output_path)

    with rasterio.open(raster_path) as src:
        data = src.read(out_shape=(src.count, recommendation.target_height, recommendation.target_width))
        profile = src.profile.copy()
        profile.update(
            width=recommendation.target_width,
            height=recommendation.target_height,
            transform=rasterio.transform.from_origin(
                src.bounds.left,
                src.bounds.top,
                abs(src.transform.a) * (src.width / recommendation.target_width),
                abs(src.transform.e) * (src.height / recommendation.target_height),
            ),
        )

        with rasterio.open(output, "w", **profile) as dst:
            dst.write(data, indexes=range(1, src.count + 1))

    return recommendation
