"""Optimization helpers for static geospatial datasets."""

from .static import (
    SUPPORTED_FORMATS,
    StaticDataBenchmarkReport,
    StaticDataConfiguration,
    StaticDataOptimizationSuggestion,
    benchmark_static_configurations,
    benchmark_static_dataset,
    suggest_static_optimization,
)

__all__ = [
    "SUPPORTED_FORMATS",
    "StaticDataBenchmarkReport",
    "StaticDataConfiguration",
    "StaticDataOptimizationSuggestion",
    "benchmark_static_configurations",
    "benchmark_static_dataset",
    "suggest_static_optimization",
]
