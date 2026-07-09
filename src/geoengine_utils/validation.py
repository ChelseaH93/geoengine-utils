"""Typed geospatial validation primitives for datasets and ETL pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Optional, Type, TypeVar


@dataclass(slots=True)
class ValidationIssue:
    """A single validation issue with a severity and message."""

    severity: str
    message: str


@dataclass(slots=True)
class ValidationReport:
    """Collection of validation issues with human-friendly summaries."""

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def add_error(self, message: str) -> None:
        self.issues.append(ValidationIssue("error", message))

    def add_warning(self, message: str) -> None:
        self.issues.append(ValidationIssue("warning", message))

    def summary(self) -> str:
        error_count = sum(1 for issue in self.issues if issue.severity == "error")
        warning_count = sum(1 for issue in self.issues if issue.severity == "warning")
        status = "passed" if self.passed else "failed"
        return (
            f"Validation {status}: {error_count} error"
            f"{'s' if error_count != 1 else ''}, {warning_count} warning"
            f"{'s' if warning_count != 1 else ''}."
        )

    def format_report(self) -> str:
        lines = [self.summary()]
        for issue in self.issues:
            lines.append(f"- [{issue.severity}] {issue.message}")
        return "\n".join(lines)


class ValidationError(Exception):
    """Raised when a dataset or pipeline payload fails validation."""

    def __init__(self, report: ValidationReport):
        self.report = report
        super().__init__(report.format_report())


@dataclass(slots=True)
class DatasetSchema:
    """Base schema for geospatial datasets used in validation workflows."""

    name: str
    crs: Optional[str] = None
    bounds: Optional[tuple[float, float, float, float]] = None

    def validate(self) -> ValidationReport:
        report = ValidationReport()
        if not self.crs:
            report.add_error("CRS is missing or invalid.")
        if not self.bounds:
            report.add_error("Bounds are missing.")
        return report


@dataclass(slots=True)
class RasterDataset(DatasetSchema):
    """Typed schema for raster datasets used in ETL and validation pipelines."""

    path: Optional[str] = None
    geometry: Optional[Any] = None
    topology: Optional[bool] = None

    def validate(self) -> ValidationReport:
        report = DatasetSchema.validate(self)
        if not self.path:
            report.add_error("Raster path is missing.")
        if self.geometry is None:
            report.add_warning("Raster geometry is not provided.")
        if self.topology is False:
            report.add_error("Raster topology is invalid.")
        return report


@dataclass(slots=True)
class VectorDataset(DatasetSchema):
    """Typed schema for vector datasets used in ETL and validation pipelines."""

    geometry: Optional[Any] = None
    topology: Optional[bool] = None

    def validate(self) -> ValidationReport:
        report = DatasetSchema.validate(self)
        if self.geometry is None:
            report.add_error("Vector geometry is missing.")
        if self.topology is False:
            report.add_error("Vector topology is invalid.")
        return report


F = TypeVar("F", bound=Callable[..., Any])


def validate_dataset(
    *,
    input_schema: Optional[Type[DatasetSchema]] = None,
    output_schema: Optional[Type[DatasetSchema]] = None,
) -> Callable[[F], F]:
    """Decorator that validates pipeline inputs and outputs against typed schemas."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if input_schema is not None:
                payload = args[0] if args else kwargs.get("data")
                report = _validate_payload(payload, input_schema)
                if not report.passed:
                    raise ValidationError(report)

            result = func(*args, **kwargs)

            if output_schema is not None:
                report = _validate_payload(result, output_schema)
                if not report.passed:
                    raise ValidationError(report)

            return result

        return wrapper  # type: ignore[return-value]

    return decorator


def _validate_payload(payload: Any, schema_type: Type[DatasetSchema]) -> ValidationReport:
    if isinstance(payload, schema_type):
        return payload.validate()

    if isinstance(payload, DatasetSchema):
        return payload.validate()

    report = ValidationReport()
    report.add_error(f"Expected {schema_type.__name__}, received {type(payload).__name__}.")
    return report
