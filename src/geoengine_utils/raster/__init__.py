"""Raster utilities for metadata inspection and resampling.

Raster readiness validation lives in ``geoengine_utils.validation.assess_readiness``.
"""

from .metadata import get_raster_metadata
from .resample import recommend_resampling, resample_raster

__all__ = [
    "get_raster_metadata",
    "recommend_resampling",
    "resample_raster",
]
