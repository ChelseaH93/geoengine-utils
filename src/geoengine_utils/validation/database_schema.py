"""Read-only Snowflake and DuckDB schema validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence


class SchemaConnection(Protocol):
    def cursor(self) -> Any: ...


ExpectedSchema = Mapping[str, Mapping[str, str]]


@dataclass(frozen=True)
class SchemaColumn:
    """A column discovered from a database information schema."""

    name: str
    data_type: str
    nullable: bool | None
    ordinal_position: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "nullable": self.nullable,
            "ordinal_position": self.ordinal_position,
        }


@dataclass(frozen=True)
class DatabaseTableSchema:
    """A table and its discovered columns."""

    schema: str
    table: str
    columns: tuple[SchemaColumn, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "table": self.table,
            "columns": [column.to_dict() for column in self.columns],
        }


@dataclass(frozen=True)
class SchemaValidationIssue:
    """An actionable database schema finding."""

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
class DatabaseSchemaValidationReport:
    """Schema inventory and validation findings for one database engine."""

    engine: str
    schema: str
    database: str | None
    tables: tuple[DatabaseTableSchema, ...]
    issues: tuple[SchemaValidationIssue, ...]

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def errors(self) -> tuple[SchemaValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[SchemaValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def suggestions(self) -> tuple[SchemaValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "suggestion")

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "schema": self.schema,
            "database": self.database,
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
            f"{self.engine} schema validation: {len(self.tables)} tables, "
            f"{counts['error']} errors, {counts['warning']} warnings, "
            f"{counts['suggestion']} suggestions"
        ]
        lines.extend(
            f"- [{issue.severity}] {issue.message} Suggestion: {issue.suggestion}"
            for issue in self.issues
        )
        return "\n".join(lines)


def validate_snowflake_schema(
    connection: SchemaConnection | str,
    *,
    schema: str = "PUBLIC",
    database: str | None = None,
    expected: ExpectedSchema | None = None,
) -> DatabaseSchemaValidationReport:
    """Validate a Snowflake schema using read-only INFORMATION_SCHEMA queries."""

    connection_object, should_close = _open_connection(connection, "snowflake")
    try:
        catalog = database or _scalar(connection_object, "SELECT CURRENT_DATABASE()")
        rows = _fetchall(
            connection_object,
            "SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, ORDINAL_POSITION "
            "FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s "
            "ORDER BY TABLE_NAME, ORDINAL_POSITION",
            (schema.upper(),),
        )
        tables = _group_columns(rows, schema)
        issues = _validate_expected(tables, expected, case_insensitive=True)
        if not tables:
            issues.append(
                SchemaValidationIssue(
                    "warning",
                    "catalog",
                    f"Snowflake schema {schema} contains no tables or views.",
                    "Check the schema name and role privileges, then confirm the source objects exist.",
                    schema=schema,
                )
            )
        return DatabaseSchemaValidationReport("Snowflake", schema, catalog, tuple(tables), tuple(issues))
    finally:
        if should_close:
            connection_object.close()


def validate_duckdb_schema(
    connection: SchemaConnection | str,
    *,
    schema: str = "main",
    expected: ExpectedSchema | None = None,
) -> DatabaseSchemaValidationReport:
    """Validate a DuckDB schema using its read-only information schema."""

    connection_object, should_close = _open_connection(connection, "duckdb")
    try:
        rows = _fetchall(
            connection_object,
            "SELECT table_schema, table_name, column_name, data_type, is_nullable, ordinal_position "
            "FROM information_schema.columns WHERE table_schema = ? "
            "ORDER BY table_name, ordinal_position",
            (schema,),
        )
        tables = _group_columns(rows, schema)
        issues = _validate_expected(tables, expected, case_insensitive=False)
        if not tables:
            issues.append(
                SchemaValidationIssue(
                    "warning",
                    "catalog",
                    f"DuckDB schema {schema} contains no tables or views.",
                    "Check the schema name and confirm the connection points to the intended database file.",
                    schema=schema,
                )
            )
        return DatabaseSchemaValidationReport("DuckDB", schema, None, tuple(tables), tuple(issues))
    finally:
        if should_close:
            connection_object.close()


def _group_columns(rows: Sequence[Sequence[Any]], schema: str) -> list[DatabaseTableSchema]:
    grouped: dict[str, list[SchemaColumn]] = {}
    for row in rows:
        table_name = str(row[1])
        grouped.setdefault(table_name, []).append(
            SchemaColumn(
                name=str(row[2]),
                data_type=str(row[3]),
                nullable=_nullable(row[4]),
                ordinal_position=int(row[5]) if row[5] is not None else None,
            )
        )
    return [
        DatabaseTableSchema(schema=schema, table=table, columns=tuple(columns))
        for table, columns in grouped.items()
    ]


def _validate_expected(
    tables: Sequence[DatabaseTableSchema],
    expected: ExpectedSchema | None,
    *,
    case_insensitive: bool,
) -> list[SchemaValidationIssue]:
    if expected is None:
        return []
    actual_tables = {
        table.table.lower() if case_insensitive else table.table: table for table in tables
    }
    issues: list[SchemaValidationIssue] = []
    for expected_table, expected_columns in expected.items():
        table_key = expected_table.lower() if case_insensitive else expected_table
        table = actual_tables.get(table_key)
        if table is None:
            issues.append(
                SchemaValidationIssue(
                    "error",
                    "schema_contract",
                    f"Expected table {expected_table} was not found.",
                    f"Create or expose table {expected_table} in the validated schema.",
                    table=expected_table,
                )
            )
            continue
        actual_columns = {
            column.name.lower() if case_insensitive else column.name: column
            for column in table.columns
        }
        for expected_column, expected_type in expected_columns.items():
            column_key = expected_column.lower() if case_insensitive else expected_column
            actual_column = actual_columns.get(column_key)
            if actual_column is None:
                issues.append(
                    SchemaValidationIssue(
                        "error",
                        "schema_contract",
                        f"Expected column {table.table}.{expected_column} was not found.",
                        f"Add or expose column {expected_column} with type {expected_type}.",
                        table=table.table,
                        column=expected_column,
                    )
                )
            elif not _types_compatible(actual_column.data_type, expected_type):
                issues.append(
                    SchemaValidationIssue(
                        "error",
                        "schema_contract",
                        f"{table.table}.{actual_column.name} is {actual_column.data_type}, expected {expected_type}.",
                        "Cast or migrate the column to the contract type, then re-run validation.",
                        table=table.table,
                        column=actual_column.name,
                    )
                )
        expected_keys = {
            name.lower() if case_insensitive else name for name in expected_columns
        }
        for column in table.columns:
            column_key = column.name.lower() if case_insensitive else column.name
            if column_key not in expected_keys:
                issues.append(
                    SchemaValidationIssue(
                        "suggestion",
                        "schema_contract",
                        f"{table.table}.{column.name} is not declared in the expected contract.",
                        "Document the column or remove it from the published schema if it is not part of the interface.",
                        table=table.table,
                        column=column.name,
                    )
                )
    return issues


def _types_compatible(actual: str, expected: str) -> bool:
    def normalize(value: str) -> str:
        return " ".join(str(value).lower().replace("_", " ").split())

    actual_value = normalize(actual)
    expected_value = normalize(expected)
    if actual_value == expected_value:
        return True
    aliases = {
        "int": {"integer", "bigint", "int32", "int64", "number"},
        "integer": {"int", "integer", "bigint", "int32", "int64", "number"},
        "float": {"double", "real", "float", "float32", "float64", "number"},
        "string": {"varchar", "text", "string"},
    }
    return actual_value in aliases.get(expected_value, {expected_value})


def _nullable(value: Any) -> bool | None:
    if value is None:
        return None
    normalized = str(value).upper()
    if normalized in {"YES", "Y", "TRUE", "1"}:
        return True
    if normalized in {"NO", "N", "FALSE", "0"}:
        return False
    return None


def _scalar(connection: SchemaConnection, query: str) -> str | None:
    row = _fetchone(connection, query)
    return str(row[0]) if row and row[0] is not None else None


def _fetchall(connection: SchemaConnection, query: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        return list(cursor.fetchall())


def _fetchone(connection: SchemaConnection, query: str, params: Sequence[Any] = ()) -> tuple[Any, ...] | None:
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchone()


def _open_connection(connection: SchemaConnection | str, engine: str) -> tuple[Any, bool]:
    if not isinstance(connection, str):
        return connection, False
    try:
        if engine == "snowflake":
            import snowflake.connector

            return snowflake.connector.connect(connection), True
        import duckdb

        return duckdb.connect(connection), True
    except ImportError as exc:
        extra = "snowflake" if engine == "snowflake" else "duckdb"
        raise ImportError(
            f"{engine} is required for path/DSN connections. Install with `pip install geoengine-utils[{extra}]`."
        ) from exc


__all__ = [
    "DatabaseSchemaValidationReport",
    "DatabaseTableSchema",
    "SchemaColumn",
    "SchemaValidationIssue",
    "validate_duckdb_schema",
    "validate_snowflake_schema",
]
