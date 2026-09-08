"""Read-only PostGIS database auditing and optimization suggestions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Protocol, Sequence


class DBConnection(Protocol):
    def cursor(self) -> Any: ...


@dataclass(frozen=True)
class PostGISIssue:
    """An actionable PostGIS audit finding."""

    severity: str
    category: str
    message: str
    suggestion: str
    schema: str | None = None
    table: str | None = None
    column: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "suggestion": self.suggestion,
            "schema": self.schema,
            "table": self.table,
            "column": self.column,
        }


@dataclass(frozen=True)
class PostGISTableAudit:
    """Catalog, index, and quality metrics for one PostGIS geometry table."""

    schema: str
    table: str
    column: str
    geometry_type: str
    srid: int
    coordinate_dimension: int
    feature_count: int | None
    null_geometry_count: int | None
    empty_geometry_count: int | None
    invalid_geometry_count: int | None
    spatial_index_count: int
    seq_scan: int | None
    index_scan: int | None

    @property
    def has_spatial_index(self) -> bool:
        return self.spatial_index_count > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "table": self.table,
            "column": self.column,
            "geometry_type": self.geometry_type,
            "srid": self.srid,
            "coordinate_dimension": self.coordinate_dimension,
            "feature_count": self.feature_count,
            "null_geometry_count": self.null_geometry_count,
            "empty_geometry_count": self.empty_geometry_count,
            "invalid_geometry_count": self.invalid_geometry_count,
            "spatial_index_count": self.spatial_index_count,
            "seq_scan": self.seq_scan,
            "index_scan": self.index_scan,
        }


@dataclass(frozen=True)
class PostGISAuditReport:
    """Complete PostGIS audit result."""

    database: str | None
    postgis_version: str | None
    server_version: str | None
    tables: tuple[PostGISTableAudit, ...]
    issues: tuple[PostGISIssue, ...]

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def errors(self) -> tuple[PostGISIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[PostGISIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def suggestions(self) -> tuple[PostGISIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "suggestion")

    def to_dict(self) -> dict[str, Any]:
        return {
            "database": self.database,
            "postgis_version": self.postgis_version,
            "server_version": self.server_version,
            "tables": [table.to_dict() for table in self.tables],
            "issues": [issue.to_dict() for issue in self.issues],
            "passed": self.passed,
        }

    def format_report(self) -> str:
        counts = {
            severity: sum(issue.severity == severity for issue in self.issues)
            for severity in ("error", "warning", "suggestion")
        }
        lines = [
            f"PostGIS audit: {len(self.tables)} geometry tables, "
            f"{counts['error']} errors, {counts['warning']} warnings, "
            f"{counts['suggestion']} suggestions"
        ]
        lines.extend(
            f"- [{issue.severity}] {issue.message} Suggestion: {issue.suggestion}"
            for issue in self.issues
        )
        return "\n".join(lines)


@dataclass(frozen=True)
class PostGISQueryPlan:
    """Parsed output from a read-only PostgreSQL EXPLAIN."""

    plan: Mapping[str, Any]
    issues: tuple[PostGISIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"plan": dict(self.plan), "issues": [issue.to_dict() for issue in self.issues]}


def audit_postgis(
    connection: DBConnection | str,
    *,
    schemas: Sequence[str] | None = None,
    tables: Sequence[str] | None = None,
    include_quality: bool = True,
) -> PostGISAuditReport:
    """Run a read-only catalog, index, statistics, and geometry-quality audit.

    ``connection`` may be an existing DB-API connection or a PostgreSQL DSN.
    DSNs use the optional ``psycopg`` dependency, imported only when needed.
    No table data is modified; quality checks use aggregate SQL only.
    """

    connection_object, should_close = _open_connection(connection)
    try:
        database = _scalar(connection_object, "SELECT current_database()")
        server_version = _scalar(connection_object, "SELECT version()")
        postgis_version = _scalar(
            connection_object,
            "SELECT postgis_full_version()",
            missing_ok=True,
        )
        geometry_columns = _fetch_geometry_columns(connection_object, schemas, tables)
        indexes = _fetch_spatial_indexes(connection_object)
        statistics = _fetch_table_statistics(connection_object)
        audits: list[PostGISTableAudit] = []
        issues: list[PostGISIssue] = []
        if postgis_version is None:
            issues.append(
                PostGISIssue(
                    "error",
                    "database",
                    "PostGIS is not installed or postgis_full_version() is unavailable.",
                    "Install and enable the PostGIS extension in the target database before auditing spatial data.",
                )
            )
        for column in geometry_columns:
            key = (column[0], column[1])
            quality = _fetch_quality(connection_object, column) if include_quality else None
            index_count = len(indexes.get(key, ()))
            stats = statistics.get(key, (None, None))
            audit = PostGISTableAudit(
                schema=column[0],
                table=column[1],
                column=column[2],
                geometry_type=column[3],
                srid=int(column[4]),
                coordinate_dimension=int(column[5]),
                feature_count=quality[0] if quality else None,
                null_geometry_count=quality[1] if quality else None,
                empty_geometry_count=quality[2] if quality else None,
                invalid_geometry_count=quality[3] if quality else None,
                spatial_index_count=index_count,
                seq_scan=stats[0],
                index_scan=stats[1],
            )
            audits.append(audit)
            issues.extend(_issues_for_table(audit))
        if not geometry_columns:
            issues.append(
                PostGISIssue(
                    "warning",
                    "catalog",
                    "No PostGIS geometry columns were found in the selected scope.",
                    "Check schema/table filters and confirm geometry columns are registered in geometry_columns.",
                )
            )
        return PostGISAuditReport(
            database=database,
            postgis_version=postgis_version,
            server_version=server_version,
            tables=tuple(audits),
            issues=tuple(issues),
        )
    finally:
        if should_close:
            connection_object.close()


def explain_postgis_query(
    connection: DBConnection | str,
    query: str,
    params: Sequence[Any] = (),
) -> PostGISQueryPlan:
    """Run a read-only ``EXPLAIN (FORMAT JSON)`` and suggest query improvements."""

    if not query.strip():
        raise ValueError("query must not be empty")
    connection_object, should_close = _open_connection(connection)
    try:
        result = _fetchone(connection_object, f"EXPLAIN (FORMAT JSON) {query}", params)
        plan = result[0] if result else {}
        if isinstance(plan, str):
            plan = json.loads(plan)
        if isinstance(plan, list) and plan:
            plan = plan[0].get("Plan", plan[0])
        issues = tuple(_issues_for_plan(plan))
        return PostGISQueryPlan(plan=plan, issues=issues)
    finally:
        if should_close:
            connection_object.close()


def _issues_for_table(audit: PostGISTableAudit) -> list[PostGISIssue]:
    issues: list[PostGISIssue] = []
    location = {"schema": audit.schema, "table": audit.table, "column": audit.column}
    if not audit.has_spatial_index:
        issues.append(
            PostGISIssue(
                "warning",
                "spatial_index",
                f"{audit.schema}.{audit.table}.{audit.column} has no detected GiST or SP-GiST index.",
                f"CREATE INDEX ON {quote_identifier(audit.table)} USING GIST ({quote_identifier(audit.column)});",
                **location,
            )
        )
    if audit.srid == 0:
        issues.append(
            PostGISIssue(
                "warning",
                "spatial_reference",
                f"{audit.schema}.{audit.table}.{audit.column} has SRID 0.",
                "Assign the correct SRID and enforce it with a geometry typmod or constraint.",
                **location,
            )
        )
    if audit.null_geometry_count and audit.null_geometry_count > 0:
        issues.append(
            PostGISIssue(
                "warning",
                "data_quality",
                f"{audit.schema}.{audit.table}.{audit.column} contains {audit.null_geometry_count:,} NULL geometries.",
                "Remove NULL geometries or make the geometry column NOT NULL when appropriate.",
                **location,
            )
        )
    if audit.empty_geometry_count and audit.empty_geometry_count > 0:
        issues.append(
            PostGISIssue(
                "warning",
                "data_quality",
                f"{audit.schema}.{audit.table}.{audit.column} contains {audit.empty_geometry_count:,} empty geometries.",
                "Review and remove empty geometries unless they have an intentional domain meaning.",
                **location,
            )
        )
    if audit.invalid_geometry_count and audit.invalid_geometry_count > 0:
        issues.append(
            PostGISIssue(
                "error",
                "data_quality",
                f"{audit.schema}.{audit.table}.{audit.column} contains {audit.invalid_geometry_count:,} invalid geometries.",
                "Repair with ST_MakeValid in a controlled migration and re-run the audit.",
                **location,
            )
        )
    if (
        audit.seq_scan is not None
        and audit.index_scan is not None
        and audit.seq_scan > 100
        and audit.seq_scan > audit.index_scan * 2
    ):
        issues.append(
            PostGISIssue(
                "suggestion",
                "query_optimization",
                f"{audit.schema}.{audit.table} has many more sequential scans than index scans.",
                "Inspect spatial predicates with EXPLAIN (FORMAT JSON), refresh statistics with ANALYZE, and verify the spatial index is used.",
                **location,
            )
        )
    return issues


def _issues_for_plan(plan: Mapping[str, Any]) -> Iterable[PostGISIssue]:
    node_type = str(plan.get("Node Type", ""))
    relation = plan.get("Relation Name")
    if node_type == "Seq Scan":
        yield PostGISIssue(
            "suggestion",
            "query_optimization",
            f"EXPLAIN reports a sequential scan on {relation or 'a relation'}.",
            "Add a selective predicate, refresh statistics, or verify that the relevant B-tree or spatial index matches the query.",
            table=str(relation) if relation else None,
        )
    if node_type in {"Sort", "Aggregate"} and plan.get("Actual Rows", 0) > 100_000:
        yield PostGISIssue(
            "suggestion",
            "query_optimization",
            f"EXPLAIN reports a large {node_type.lower()} operation.",
            "Filter earlier, select only required columns, and consider a covering or pre-aggregated strategy.",
        )
    for child in plan.get("Plans", []) or []:
        yield from _issues_for_plan(child)


def quote_identifier(identifier: str) -> str:
    """Quote one SQL identifier; dotted identifiers are rejected."""

    if not identifier or "." in identifier or "\x00" in identifier:
        raise ValueError("identifier must be a non-empty, single SQL identifier")
    return '"' + identifier.replace('"', '""') + '"'


def _fetch_geometry_columns(connection: DBConnection, schemas: Sequence[str] | None, tables: Sequence[str] | None) -> list[tuple[Any, ...]]:
    clauses = []
    params: list[Any] = []
    if schemas:
        clauses.append("f_table_schema = ANY(%s)")
        params.append(list(schemas))
    if tables:
        clauses.append("f_table_name = ANY(%s)")
        params.append(list(tables))
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    return _fetchall(connection, "SELECT f_table_schema, f_table_name, f_geometry_column, type, srid, coord_dimension FROM geometry_columns" + where, params)


def _fetch_spatial_indexes(connection: DBConnection) -> dict[tuple[str, str], list[str]]:
    rows = _fetchall(connection, "SELECT schemaname, tablename, indexname FROM pg_indexes WHERE indexdef ILIKE '%USING gist%' OR indexdef ILIKE '%USING spgist%'")
    result: dict[tuple[str, str], list[str]] = {}
    for schema, table, index_name in rows:
        result.setdefault((schema, table), []).append(index_name)
    return result


def _fetch_table_statistics(connection: DBConnection) -> dict[tuple[str, str], tuple[int | None, int | None]]:
    rows = _fetchall(connection, "SELECT schemaname, relname, seq_scan, idx_scan FROM pg_stat_user_tables")
    return {(row[0], row[1]): (row[2], row[3]) for row in rows}


def _fetch_quality(connection: DBConnection, column: tuple[Any, ...]) -> tuple[int, int, int, int]:
    schema, table, geometry_column = column[:3]
    quoted_table = f"{quote_identifier(schema)}.{quote_identifier(table)}"
    quoted_column = quote_identifier(geometry_column)
    query = (
        f"SELECT count(*), count(*) FILTER (WHERE {quoted_column} IS NULL), "
        f"count(*) FILTER (WHERE {quoted_column} IS NOT NULL AND ST_IsEmpty({quoted_column})), "
        f"count(*) FILTER (WHERE {quoted_column} IS NOT NULL AND NOT ST_IsValid({quoted_column})) "
        f"FROM {quoted_table}"
    )
    row = _fetchone(connection, query)
    return tuple(int(value or 0) for value in row[:4])


def _scalar(connection: DBConnection, query: str, *, missing_ok: bool = False) -> str | None:
    try:
        row = _fetchone(connection, query)
    except Exception:
        if missing_ok:
            return None
        raise
    return str(row[0]) if row and row[0] is not None else None


def _fetchall(connection: DBConnection, query: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        return list(cursor.fetchall())


def _fetchone(connection: DBConnection, query: str, params: Sequence[Any] = ()) -> tuple[Any, ...] | None:
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchone()


def _open_connection(connection: DBConnection | str) -> tuple[Any, bool]:
    if not isinstance(connection, str):
        return connection, False
    try:
        import psycopg
    except ImportError as exc:
        raise ImportError(
            "psycopg is required for DSN connections. Install with `pip install geoengine-utils[postgis]`."
        ) from exc
    return psycopg.connect(connection), True


__all__ = [
    "PostGISAuditReport",
    "PostGISTableAudit",
    "PostGISIssue",
    "PostGISQueryPlan",
    "audit_postgis",
    "explain_postgis_query",
    "quote_identifier",
]
