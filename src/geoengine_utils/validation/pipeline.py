"""GIS pipeline stage-to-stage validation."""

from __future__ import annotations

from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import Any, Sequence

import geopandas as gpd
from pyproj import CRS


@dataclass(frozen=True)
class PipelineAuditConfig:
    """Thresholds and contracts for a GIS pipeline stage comparison."""

    expected_crs: str | None = None
    expected_geometry_types: tuple[str, ...] | None = None
    max_feature_count_change: float | None = 0.05
    max_extent_change: float | None = 0.05
    require_valid_geometry: bool = True
    allow_schema_additions: bool = True
    require_same_crs: bool = True


@dataclass(frozen=True)
class PipelineAuditIssue:
    """An actionable pipeline stage finding."""

    severity: str
    category: str
    message: str
    suggestion: str

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass(frozen=True)
class PipelineStageSummary:
    """Comparable metadata extracted from one pipeline stage."""

    feature_count: int
    columns: tuple[str, ...]
    geometry_types: tuple[str, ...]
    crs: str | None
    bounds: tuple[float, float, float, float]
    invalid_geometry_count: int
    empty_geometry_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_count": self.feature_count,
            "columns": list(self.columns),
            "geometry_types": list(self.geometry_types),
            "crs": self.crs,
            "bounds": list(self.bounds),
            "invalid_geometry_count": self.invalid_geometry_count,
            "empty_geometry_count": self.empty_geometry_count,
        }


@dataclass(frozen=True)
class PipelineStageAuditReport:
    """Comparison report for an input and output GIS pipeline stage."""

    input_summary: PipelineStageSummary
    output_summary: PipelineStageSummary
    issues: tuple[PipelineAuditIssue, ...]

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def errors(self) -> tuple[PipelineAuditIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[PipelineAuditIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def suggestions(self) -> tuple[PipelineAuditIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "suggestion")

    def to_dict(self) -> dict[str, Any]:
        return {
            "input": self.input_summary.to_dict(),
            "output": self.output_summary.to_dict(),
            "issues": [issue.to_dict() for issue in self.issues],
            "passed": self.passed,
        }

    def format_report(self) -> str:
        counts = {
            severity: sum(issue.severity == severity for issue in self.issues)
            for severity in ("error", "warning", "suggestion")
        }
        lines = [
            "Pipeline stage audit: "
            f"{counts['error']} errors, {counts['warning']} warnings, "
            f"{counts['suggestion']} suggestions"
        ]
        lines.extend(
            f"- [{issue.severity}] {issue.message} Suggestion: {issue.suggestion}"
            for issue in self.issues
        )
        return "\n".join(lines)


def audit_pipeline_stage(
    input_data: Any,
    output_data: Any,
    *,
    config: PipelineAuditConfig | None = None,
) -> PipelineStageAuditReport:
    """Compare GIS input/output stages for spatial and schema regressions."""

    policy = config or PipelineAuditConfig()
    if policy.max_feature_count_change is not None and policy.max_feature_count_change < 0:
        raise ValueError("max_feature_count_change must be non-negative")
    if policy.max_extent_change is not None and policy.max_extent_change < 0:
        raise ValueError("max_extent_change must be non-negative")
    input_summary = _summarize(_load_vector(input_data))
    output_summary = _summarize(_load_vector(output_data))
    issues = _compare_summaries(input_summary, output_summary, policy)
    return PipelineStageAuditReport(input_summary, output_summary, tuple(issues))


def _load_vector(data: Any) -> gpd.GeoDataFrame:
    if isinstance(data, gpd.GeoDataFrame):
        return data
    if isinstance(data, gpd.GeoSeries):
        return gpd.GeoDataFrame(geometry=data, crs=data.crs)
    if isinstance(data, (str, PathLike)):
        path = Path(data)
        if path.suffix.lower() in {".parquet", ".geoparquet"}:
            return gpd.read_parquet(path)
        return gpd.read_file(path)
    raise TypeError("pipeline stages must be vector paths, GeoDataFrames, or GeoSeries")


def _summarize(frame: gpd.GeoDataFrame) -> PipelineStageSummary:
    if "geometry" not in frame.columns:
        raise ValueError("pipeline stage has no geometry column")
    geometry = frame.geometry
    non_empty = geometry[~geometry.is_empty & geometry.notna()]
    bounds = tuple(float(value) for value in frame.total_bounds)
    return PipelineStageSummary(
        feature_count=len(frame),
        columns=tuple(str(column) for column in frame.columns if column != frame.geometry.name),
        geometry_types=tuple(sorted(str(value) for value in non_empty.geom_type.unique())),
        crs=frame.crs.to_string() if frame.crs is not None else None,
        bounds=bounds,
        invalid_geometry_count=int((~geometry.is_valid & ~geometry.is_empty & geometry.notna()).sum()),
        empty_geometry_count=int((geometry.is_empty | geometry.isna()).sum()),
    )


def _compare_summaries(
    source: PipelineStageSummary,
    result: PipelineStageSummary,
    config: PipelineAuditConfig,
) -> list[PipelineAuditIssue]:
    issues: list[PipelineAuditIssue] = []
    if config.expected_crs is not None and not _same_crs(result.crs, config.expected_crs):
        issues.append(
            PipelineAuditIssue(
                "error",
                "crs",
                f"Output CRS {result.crs!r} does not match expected CRS {config.expected_crs!r}.",
                "Reproject the output to the contract CRS before publishing the stage.",
            )
        )
    if config.require_same_crs and source.crs != result.crs:
        issues.append(
            PipelineAuditIssue(
                "error",
                "crs",
                f"Output CRS {result.crs!r} differs from input CRS {source.crs!r}.",
                "Confirm the reprojection is intentional and record the target CRS in the stage contract.",
            )
        )
    if config.expected_geometry_types is not None:
        allowed = set(config.expected_geometry_types)
        unexpected = set(result.geometry_types) - allowed
        if unexpected:
            issues.append(
                PipelineAuditIssue(
                    "error",
                    "geometry_type",
                    f"Output geometry types {sorted(unexpected)} are outside the expected set {sorted(allowed)}.",
                    "Normalize geometry types before publishing the stage or update the contract deliberately.",
                )
            )
    if config.require_valid_geometry and result.invalid_geometry_count:
        issues.append(
            PipelineAuditIssue(
                "error",
                "geometry_quality",
                f"Output contains {result.invalid_geometry_count:,} invalid geometries.",
                "Repair invalid geometries and re-run the stage audit before publishing.",
            )
        )
    if result.empty_geometry_count:
        issues.append(
            PipelineAuditIssue(
                "warning",
                "geometry_quality",
                f"Output contains {result.empty_geometry_count:,} empty or NULL geometries.",
                "Remove empty features or document why they are intentionally retained.",
            )
        )
    if config.max_feature_count_change is not None:
        if source.feature_count == 0:
            if result.feature_count:
                issues.append(
                    PipelineAuditIssue(
                        "warning",
                        "feature_count",
                        "The input is empty but the output contains features.",
                        "Verify that the stage is not producing records from an empty input unexpectedly.",
                    )
                )
        else:
            change = abs(result.feature_count - source.feature_count) / source.feature_count
            if change > config.max_feature_count_change:
                issues.append(
                    PipelineAuditIssue(
                        "warning",
                        "feature_count",
                        f"Feature count changed by {change:.1%} ({source.feature_count:,} to {result.feature_count:,}).",
                        "Confirm the expected loss or expansion and record the operation's cardinality policy.",
                    )
                )
    if config.max_extent_change is not None:
        extent_change = _extent_change_ratio(source.bounds, result.bounds)
        if extent_change > config.max_extent_change:
            issues.append(
                PipelineAuditIssue(
                    "warning",
                    "extent",
                    f"Output extent changed by {extent_change:.1%} relative to the input extent.",
                    "Check clipping, filtering, reprojection, and antimeridian handling against the stage contract.",
                )
            )
    source_columns = set(source.columns)
    result_columns = set(result.columns)
    removed = sorted(source_columns - result_columns)
    added = sorted(result_columns - source_columns)
    if removed:
        issues.append(
            PipelineAuditIssue(
                "warning",
                "schema",
                f"Output removed columns: {removed}.",
                "Confirm the fields are intentionally dropped and update downstream contracts if needed.",
            )
        )
    if added and not config.allow_schema_additions:
        issues.append(
            PipelineAuditIssue(
                "error",
                "schema",
                f"Output added columns: {added}.",
                "Declare the new fields in the stage contract or disable the schema additions.",
            )
        )
    elif added:
        issues.append(
            PipelineAuditIssue(
                "suggestion",
                "schema",
                f"Output added columns: {added}.",
                "Document the new fields so downstream consumers can rely on the expanded schema.",
            )
        )
    return issues


def _same_crs(actual: str | None, expected: str) -> bool:
    if actual is None:
        return False
    try:
        return CRS.from_user_input(actual) == CRS.from_user_input(expected)
    except Exception:
        return actual.upper() == expected.upper()


def _extent_change_ratio(source: Sequence[float], result: Sequence[float]) -> float:
    source_width = max(abs(source[2] - source[0]), 1e-12)
    source_height = max(abs(source[3] - source[1]), 1e-12)
    return max(
        abs(result[0] - source[0]) / source_width,
        abs(result[1] - source[1]) / source_height,
        abs(result[2] - source[2]) / source_width,
        abs(result[3] - source[3]) / source_height,
    )


__all__ = [
    "PipelineAuditConfig",
    "PipelineAuditIssue",
    "PipelineStageAuditReport",
    "PipelineStageSummary",
    "audit_pipeline_stage",
]
