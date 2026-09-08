"""GeoEngine Utils.

Production-ready utilities for geospatial data engineering.
"""

from .ci import CICheckResult, CIRunReport, run_ci_checks, run_ci_config

__version__ = "0.1.0"

from .crs import (
    estimate_crs,
    find_matching_crs,
    recommend,
    recommend_crs,
    transform_geometry,
    validate_crs,
)
from .raster import (
    get_raster_metadata,
    recommend_resampling,
    resample_raster,
)
from .validation import (
    AirflowAuditConfig,
    AirflowAuditIssue,
    AirflowAuditReport,
    AirflowTaskAudit,
    DatabaseSchemaValidationReport,
    DatabaseTableSchema,
    DatasetSchema,
    PipelineAuditConfig,
    PipelineAuditIssue,
    PipelineStageAuditReport,
    PipelineStageSummary,
    PostGISAuditReport,
    PostGISIssue,
    PostGISQueryPlan,
    PostGISTableAudit,
    RasterDataset,
    SchemaColumn,
    SchemaValidationIssue,
    ValidationError,
    ValidationIssue,
    ValidationReport,
    VectorDataset,
    assess_readiness,
    audit_airflow_dag,
    audit_airflow_dag_file,
    audit_pipeline_stage,
    validate_dataset,
    validate_duckdb_schema,
    validate_snowflake_schema,
)


def main(*args, **kwargs):
    """Run the CLI entry point for the package."""

    from .cli import main as cli_main

    return cli_main(*args, **kwargs)


__all__ = [
    "main",
    "CICheckResult",
    "CIRunReport",
    "run_ci_checks",
    "run_ci_config",
    "__version__",
    "get_raster_metadata",
    "assess_readiness",
    "recommend_resampling",
    "resample_raster",
    "find_matching_crs",
    "recommend",
    "recommend_crs",
    "estimate_crs",
    "transform_geometry",
    "validate_crs",
    "DatasetSchema",
    "PostGISAuditReport",
    "PostGISTableAudit",
    "PostGISIssue",
    "PostGISQueryPlan",
    "PipelineAuditConfig",
    "PipelineAuditIssue",
    "PipelineStageAuditReport",
    "PipelineStageSummary",
    "audit_pipeline_stage",
    "DatabaseSchemaValidationReport",
    "DatabaseTableSchema",
    "SchemaColumn",
    "SchemaValidationIssue",
    "validate_duckdb_schema",
    "validate_snowflake_schema",
    "AirflowAuditConfig",
    "AirflowAuditIssue",
    "AirflowAuditReport",
    "AirflowTaskAudit",
    "audit_airflow_dag",
    "audit_airflow_dag_file",
    "RasterDataset",
    "VectorDataset",
    "ValidationIssue",
    "ValidationReport",
    "ValidationError",
    "validate_dataset",
]
