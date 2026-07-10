"""Typed dataset schemas used for structured validation and pipeline I/O checks."""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional, Type, TypeVar

from .report import ValidationError, ValidationReport


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
