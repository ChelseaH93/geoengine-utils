"""Dataset validation and readiness assessment.

``assess_readiness`` is the primary entry point: hand it a raster path,
vector path, GeoDataFrame/GeoSeries, or iterable of geometries and it
reports whether the dataset is ready for production use, inferring all the
metadata it needs along the way.

The lower-level ``DatasetSchema``/``RasterDataset``/``VectorDataset`` classes
and the ``validate_dataset`` decorator remain available for callers building
typed ETL pipelines that want to validate function inputs/outputs explicitly.
"""

from .postgis import (
    PostGISAuditReport,
    PostGISIssue,
    PostGISQueryPlan,
    PostGISTableAudit,
    audit_postgis,
    explain_postgis_query,
)
from .readiness import assess_readiness
from .report import ValidationError, ValidationIssue, ValidationReport
from .schemas import DatasetSchema, RasterDataset, VectorDataset, validate_dataset

__all__ = [
    "assess_readiness",
    "PostGISAuditReport",
    "PostGISTableAudit",
    "PostGISIssue",
    "PostGISQueryPlan",
    "audit_postgis",
    "explain_postgis_query",
    "DatasetSchema",
    "RasterDataset",
    "VectorDataset",
    "ValidationIssue",
    "ValidationReport",
    "ValidationError",
    "validate_dataset",
]
