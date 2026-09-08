"""Declarative CI/CD orchestration for geospatial validation checks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from pyproj import CRS

from .crs import estimate_crs
from .validation import assess_readiness, audit_pipeline_stage


@dataclass(frozen=True)
class CICheckResult:
    """Result of one configured CI check."""

    name: str
    check_type: str
    passed: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    details: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "check_type": self.check_type,
            "passed": self.passed,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class CIRunReport:
    """Aggregate result for a configured CI run."""

    checks: tuple[CICheckResult, ...]
    fail_on_warnings: bool = False

    @property
    def passed(self) -> bool:
        return all(
            check.passed and (not self.fail_on_warnings or not check.warnings)
            for check in self.checks
        )

    @property
    def errors(self) -> tuple[str, ...]:
        return tuple(
            f"{check.name}: {error}" for check in self.checks for error in check.errors
        )

    @property
    def warnings(self) -> tuple[str, ...]:
        return tuple(
            f"{check.name}: {warning}" for check in self.checks for warning in check.warnings
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "fail_on_warnings": self.fail_on_warnings,
            "checks": [check.to_dict() for check in self.checks],
        }

    def format_report(self) -> str:
        status = "passed" if self.passed else "failed"
        lines = [f"CI validation {status}: {len(self.checks)} checks"]
        for check in self.checks:
            check_status = "passed" if check.passed else "failed"
            lines.append(f"- [{check_status}] {check.name} ({check.check_type})")
            lines.extend(f"  error: {error}" for error in check.errors)
            lines.extend(f"  warning: {warning}" for warning in check.warnings)
        return "\n".join(lines)


def run_ci_checks(config: Mapping[str, Any]) -> CIRunReport:
    """Run checks from a JSON-compatible CI configuration mapping.

    Supported sections are ``datasets`` and ``pipeline_stages``. Each item can
    provide a ``name`` and the options documented by the corresponding audit.
    """

    checks: list[CICheckResult] = []
    for item in config.get("datasets", []):
        checks.append(_run_dataset_check(item))
    for item in config.get("pipeline_stages", []):
        checks.append(_run_pipeline_check(item))
    if not checks:
        raise ValueError("CI configuration must define datasets or pipeline_stages")
    return CIRunReport(tuple(checks), bool(config.get("fail_on_warnings", False)))


def run_ci_config(path: str | Path) -> CIRunReport:
    """Load and run a JSON CI configuration file."""

    config_path = Path(path)
    with config_path.open(encoding="utf-8") as handle:
        config = json.load(handle)
    if not isinstance(config, dict):
        raise ValueError("CI configuration root must be a JSON object")
    return run_ci_checks(config)


def _run_dataset_check(item: Mapping[str, Any]) -> CICheckResult:
    path = item.get("path")
    name = str(item.get("name", path or "dataset"))
    if not path:
        return _failed_result(name, "dataset", "dataset check requires a path")
    try:
        readiness = assess_readiness(path)
        errors = tuple(readiness.errors)
        warnings = tuple(readiness.warnings)
        expected_crs = item.get("expected_crs")
        details: dict[str, Any] = {"path": str(path), "readiness": readiness.format_report()}
        if expected_crs is not None:
            recommendation = estimate_crs(path)
            actual = f"{recommendation.recommended.auth_name}:{recommendation.recommended.code}"
            details["estimated_crs"] = actual
            if not _crs_matches(actual, str(expected_crs)):
                errors += (f"estimated CRS {actual} does not match expected {expected_crs}",)
        return CICheckResult(name, "dataset", not errors, errors, warnings, details)
    except Exception as exc:
        return _failed_result(name, "dataset", str(exc))


def _run_pipeline_check(item: Mapping[str, Any]) -> CICheckResult:
    name = str(item.get("name", "pipeline-stage"))
    if "input" not in item or "output" not in item:
        return _failed_result(name, "pipeline_stage", "pipeline stage check requires input and output")
    try:
        config_values = dict(item.get("config", {}))
        report = audit_pipeline_stage(item["input"], item["output"], config=_pipeline_config(config_values))
        errors = tuple(issue.message for issue in report.errors)
        warnings = tuple(issue.message for issue in report.warnings)
        details = report.to_dict()
        return CICheckResult(name, "pipeline_stage", report.passed, errors, warnings, details)
    except Exception as exc:
        return _failed_result(name, "pipeline_stage", str(exc))


def _pipeline_config(values: Mapping[str, Any]):
    from .validation import PipelineAuditConfig

    if "expected_geometry_types" in values:
        values = dict(values)
        values["expected_geometry_types"] = tuple(values["expected_geometry_types"])
    return PipelineAuditConfig(**values)


def _failed_result(name: str, check_type: str, message: str) -> CICheckResult:
    return CICheckResult(name, check_type, False, (message,), (), {})


def _crs_matches(actual: str, expected: str) -> bool:
    try:
        return CRS.from_user_input(actual) == CRS.from_user_input(expected)
    except Exception:
        return actual.upper() == expected.upper()


def main_ci(args: Sequence[str]) -> int:
    """Run the CI command and print either text or JSON output."""

    import argparse

    parser = argparse.ArgumentParser(prog="geoengine-utils ci")
    parser.add_argument("config", help="Path to a JSON CI configuration")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parsed = parser.parse_args(args)
    try:
        report = run_ci_config(parsed.config)
    except Exception as exc:
        print(f"CI configuration error: {exc}")
        return 2
    print(json.dumps(report.to_dict(), indent=2) if parsed.json else report.format_report())
    return 0 if report.passed else 1


__all__ = ["CICheckResult", "CIRunReport", "run_ci_checks", "run_ci_config", "main_ci"]
