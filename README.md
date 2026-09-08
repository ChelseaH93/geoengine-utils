# geoengine-utils

Practical Python utilities for validating, transforming, benchmarking, and
optimizing geospatial datasets.

## What is included

- Raster metadata, readiness checks, resampling recommendations, and resampling.
- CRS validation, estimation, country-aware recommendations, and geometry transforms.
- Vector conversion, geometry repair, simplification, and readiness checks.
- Static vector format benchmarking for GeoParquet, GeoPackage, Shapefile, and GeoJSON.
- Cloud Optimized GeoTIFF generation, benchmarking, and configuration suggestions.
- PMTiles preflight checks, streaming conversion, archive benchmarking, and suggestions.
- A CLI for dataset validation, CRS estimation, and CI/CD check execution.
- Typed validation schemas, reports, and a validation decorator for ETL workflows.

## Installation

Install the package in editable mode while developing:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux or macOS
# source .venv/bin/activate

pip install -e .
```

Optional dependency groups:

```bash
# GeoParquet support for static format benchmarking
pip install -e ".[optimization]"

# COG and PMTiles support, including vector tile dependencies
pip install -e ".[cloud]"

# Development tools and test dependencies
pip install -r requirements-dev.txt
```

## Start here

Use readiness assessment as the general entry point for raster and vector
datasets:

```python
from geoengine_utils import assess_readiness, get_raster_metadata

metadata = get_raster_metadata("example.tif")
report = assess_readiness("example.tif")

print(metadata)
print(report.format_report())
```

`assess_readiness` accepts raster paths, vector paths, GeoDataFrames,
GeoSeries, and geometry iterables. It reports issues such as missing CRS,
invalid or empty geometries, mixed geometry types, unavailable bounds, and
raster metadata problems.

## Command line

Validate a raster or vector dataset:

```bash
geoengine-utils validate example.tif
```

Estimate a projected CRS from a raster or vector dataset:

```bash
geoengine-utils estimate-crs buildings.gpkg
```

The validation command returns exit code `0` for a passing report and `1` for
a failing report. The package can also be invoked as a module:

```bash
python -m geoengine_utils.cli validate example.tif
```

Run declarative checks in CI/CD with a JSON configuration:

```bash
geoengine-utils ci .geoengine-utils-ci.json
geoengine-utils ci .geoengine-utils-ci.json --json
```

The CI runner currently composes dataset readiness/CRS checks and GIS
pipeline-stage audits. A configuration can define dataset checks like this:

```json
{
    "fail_on_warnings": true,
    "datasets": [
        {
            "name": "buildings",
            "path": "data/buildings.gpkg",
            "expected_crs": "EPSG:4326"
        }
    ],
    "pipeline_stages": [
        {
            "name": "normalized buildings",
            "input": "data/raw.geojson",
            "output": "data/normalized.geojson",
            "config": {
                "expected_crs": "EPSG:4326",
                "expected_geometry_types": ["MultiPolygon"],
                "max_feature_count_change": 0.05,
                "allow_schema_additions": false
            }
        }
    ]
}
```

Exit code `0` means every configured check passed. Exit code `1` means a check
failed, including warnings when `fail_on_warnings` is enabled. Exit code `2`
means the CI configuration itself could not be loaded or executed. Use
`--json` for CI annotations, artifact capture, or downstream reporting.

## CRS and vector workflows

Estimate a CRS from a dataset footprint. The estimator transforms projected
dataset bounds to geographic coordinates before choosing a candidate. It uses
country-specific preferences where appropriate, such as EPSG:27700 for an
England or Great Britain footprint, and otherwise selects a location-aware UTM
zone.

```python
from geoengine_utils import estimate_crs, validate_crs

print(validate_crs("EPSG:4326"))
recommendation = estimate_crs("buildings.gpkg")
print(recommendation.recommended)
print(recommendation.alternatives[:3])
```

Repair invalid geometries without mutating the source frame, then validate the
result:

```python
import geopandas as gpd

from geoengine_utils import assess_readiness
from geoengine_utils.vector import repair_vector

frame = gpd.read_file("buildings.geojson")
repaired = repair_vector(frame, drop_empty=True)
print(assess_readiness(repaired).format_report())
```

Other vector helpers include `convert_vector` and `simplify_vector`. Raster
helpers include `get_raster_metadata`, `recommend_resampling`, and
`resample_raster`.

## Static vector format optimization

The non-cloud optimization package compares common static vector formats using
the same source data. It measures storage, read time, write time, feature and
column counts, geometry types, CRS, and bounds. Shapefile storage includes its
sidecar files.

```python
from geoengine_utils.optimization import (
    StaticDataConfiguration,
    benchmark_static_configurations,
    suggest_static_optimization,
)

results = benchmark_static_configurations(
    "buildings.geojson",
    [
        StaticDataConfiguration("geoparquet", compression="zstd"),
        StaticDataConfiguration("geopackage"),
        StaticDataConfiguration("shapefile"),
        StaticDataConfiguration("geojson"),
    ],
)

suggestion = suggest_static_optimization(results, target_read_seconds=0.5)
print(suggestion.recommended.format_report())
print(suggestion.rationale)
```

Benchmark an existing file directly with `benchmark_static_dataset`. GeoParquet
support is provided by the `optimization` extra:

```bash
pip install -e ".[optimization]"
```

## Cloud Optimized GeoTIFF

Generate a tiled GeoTIFF with internal overviews, benchmark an existing COG,
or compare candidate configurations:

```python
from geoengine_utils.cloud import (
    COGConfiguration,
    benchmark_cog_configurations,
    convert_to_cog,
    suggest_cog_configuration,
)

convert_to_cog("photo_dem.tif", "photo_dem-cog.tif", block_size=256)

results = benchmark_cog_configurations(
    "photo_dem.tif",
    [
        COGConfiguration(block_size=128, compression="deflate"),
        COGConfiguration(block_size=256, compression="deflate"),
        COGConfiguration(block_size=256, compression="lzw", compression_level=None),
    ],
)

suggestion = suggest_cog_configuration(results, target_read_seconds=0.1)
print(suggestion.recommended.format_report())
```

COG reports include dimensions, compression, block layout, overview levels,
validity, archive size, and representative aligned read timing.

For the repository's 2,121 x 2,091 single-band `int16` DEM, a benchmark found
that Deflate with 256 x 256 blocks produced the smallest tested COG:

| Configuration | Output size | Read time | Conversion time |
| --- | ---: | ---: | ---: |
| Deflate, 128 x 128 blocks | 608,969 bytes | 0.005 s | 0.254 s |
| Deflate, 256 x 256 blocks | 597,827 bytes | 0.008 s | 0.261 s |
| LZW, 128 x 128 blocks | 1,457,165 bytes | 0.004 s | 0.186 s |
| LZW, 256 x 256 blocks | 1,448,663 bytes | 0.009 s | 0.188 s |

All candidates were valid and included overview levels `2, 4, 8, 16, 32`.

## PMTiles

Run PMTiles preflight checks before converting vector data:

```python
from geoengine_utils.cloud import assess_pmtiles_input, convert_vector_to_pmtiles

report = assess_pmtiles_input("buildings.gpkg")
if report.passed:
    convert_vector_to_pmtiles(
        "buildings.gpkg",
        "buildings.pmtiles",
        layer_name="buildings",
        min_zoom=0,
        max_zoom=8,
        batch_size=10_000,
    )
```

The converter reprojects to Web Mercator, clips and simplifies geometries by
zoom, encodes gzip-compressed Mapbox Vector Tiles, and stages tile features in
a temporary disk-backed SQLite store. GeoParquet inputs are read in bounded
PyArrow batches.

Benchmark an archive or compare tile configurations:

```python
from geoengine_utils.cloud import (
    PMTilesConfiguration,
    benchmark_pmtiles_archive,
    benchmark_pmtiles_configurations,
    suggest_pmtiles_configuration,
)

print(benchmark_pmtiles_archive("buildings.pmtiles").format_report())

results = benchmark_pmtiles_configurations(
    "buildings.gpkg",
    [
        PMTilesConfiguration(min_zoom=0, max_zoom=4),
        PMTilesConfiguration(min_zoom=0, max_zoom=6),
    ],
)
suggestion = suggest_pmtiles_configuration(results, target_p95_tile_bytes=50_000)
print(suggestion.recommended.format_report())
```

PMTiles reports include archive size, tile count, average and p95 tile size,
zoom coverage, payload fraction, and representative read timing.

## Validation schemas and ETL checks

Use typed schemas when a pipeline needs an explicit contract:

```python
from geoengine_utils import RasterDataset, VectorDataset, validate_dataset

raster = RasterDataset(
    name="dem",
    path="dem.tif",
    crs="EPSG:32616",
    bounds=(0, 0, 1, 1),
)
vector = VectorDataset(
    name="buildings",
    crs="EPSG:4326",
    bounds=(0, 0, 1, 1),
    geometry=None,
    topology=False,
)

print(raster.validate().format_report())
print(vector.validate().format_report())

@validate_dataset(input_schema=VectorDataset, output_schema=VectorDataset)
def transform(data):
    return data
```

## PostGIS database audits

Run a read-only audit against a live PostGIS connection or PostgreSQL DSN:

```python
from geoengine_utils.validation import audit_postgis

report = audit_postgis(connection, schemas=["public"])
print(report.format_report())
```

The audit checks PostGIS and server metadata, registered geometry columns,
spatial GiST/SP-GiST indexes, table scan statistics, and per-table geometry
quality. Quality checks report NULL, empty, and invalid geometries, as well as
missing or unknown SRIDs. Findings include suggested SQL or follow-up actions
for spatial indexing, statistics, and data repair.

Inspect a specific query plan without executing the query:

```python
from geoengine_utils.validation import explain_postgis_query

plan = explain_postgis_query(
    connection,
    "SELECT * FROM buildings WHERE geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)",
    (-87.8, 41.7, -87.5, 42.1),
)
for issue in plan.issues:
    print(issue.suggestion)
```

The package uses `EXPLAIN (FORMAT JSON)` and aggregate quality queries only;
it does not run `EXPLAIN ANALYZE` or modify database data. For DSN-based
connections, install the optional dependency:

```bash
pip install -e ".[postgis]"
```

## Snowflake and DuckDB schema validation

Validate the structure of Snowflake or DuckDB schemas using their native
`information_schema` catalogs. The validators are read-only and can inspect an
existing DB-API connection; driver imports are lazy.

```python
from geoengine_utils.validation import (
    validate_duckdb_schema,
    validate_snowflake_schema,
)

expected = {
    "buildings": {
        "id": "INTEGER",
        "geom_wkt": "VARCHAR",
    }
}

duckdb_report = validate_duckdb_schema(duckdb_connection, expected=expected)
print(duckdb_report.format_report())

snowflake_report = validate_snowflake_schema(
    snowflake_connection,
    schema="ANALYTICS",
    expected={"BUILDINGS": {"ID": "INTEGER", "GEOM_WKT": "VARCHAR"}},
)
print(snowflake_report.format_report())
```

Reports inventory tables and columns, normalize common type aliases, and flag
missing tables, missing columns, type mismatches, and undeclared columns. The
optional drivers can be installed with:

```bash
pip install -e ".[duckdb]"
pip install -e ".[snowflake]"
```

## Airflow DAG audits

Audit DAG structure and operational configuration without importing Airflow at
normal package startup. Pass an existing DAG object in unit tests or use the
file helper when Airflow is installed:

```python
from geoengine_utils.validation import AirflowAuditConfig, audit_airflow_dag

report = audit_airflow_dag(
    dag,
    config=AirflowAuditConfig(
        require_schedule=True,
        require_task_owner=True,
        require_retries=True,
        require_execution_timeout=True,
        require_tags=True,
        max_active_runs=4,
        max_active_tasks=32,
    ),
)
print(report.format_report())
```

The audit checks dependency cycles, stale task references, disconnected tasks,
empty DAGs, task owners, retry policies, execution timeouts, schedules,
catchup, tags, and active-run/task concurrency limits. Findings include
severity, category, task context, and a suggested corrective action.

Audit DAG files through Airflow's `DagBag`:

```python
from geoengine_utils.validation import audit_airflow_dag_file

reports = audit_airflow_dag_file("dags/buildings.py", dag_id="building_pipeline")
for report in reports:
    print(report.format_report())
```

Install the optional Airflow dependency with:

```bash
pip install -e ".[airflow]"
```

## GIS pipeline stage audits

Compare an input and output stage to catch spatial regressions as a pipeline
runs:

```python
from geoengine_utils.validation import PipelineAuditConfig, audit_pipeline_stage

report = audit_pipeline_stage(
    input_data,
    output_data,
    config=PipelineAuditConfig(
        expected_crs="EPSG:4326",
        expected_geometry_types=("MultiPolygon",),
        max_feature_count_change=0.05,
        max_extent_change=0.05,
        require_valid_geometry=True,
        allow_schema_additions=False,
    ),
)
print(report.format_report())
```

Stage audits check CRS changes, expected geometry types, invalid and empty
geometries, feature-count drift, spatial extent drift, removed fields, and
unexpected schema additions. Findings include a severity, category, and
remediation suggestion. Inputs and outputs may be GeoDataFrames, GeoSeries, or
vector paths including GeoParquet.

## Development

Install development dependencies and run the checks:

```bash
pip install -r requirements-dev.txt
python -m pytest
ruff check src tests
python -m geoengine_utils.cli ci .geoengine-utils-ci.json --json
```

The repository contains focused tests for CRS selection, raster handling,
vector repair, static format optimization, COG generation, PMTiles conversion,
and CLI behavior.

## License

MIT License
