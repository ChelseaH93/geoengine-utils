from geoengine_utils.validation import validate_duckdb_schema, validate_snowflake_schema


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=()):
        self.connection.queries.append((query, params))
        if "CURRENT_DATABASE" in query:
            self.rows = [("ANALYTICS",)]
        elif "INFORMATION_SCHEMA.COLUMNS" in query:
            self.rows = [
                ("PUBLIC", "BUILDINGS", "ID", "NUMBER", "NO", 1),
                ("PUBLIC", "BUILDINGS", "GEOM_WKT", "VARCHAR", "YES", 2),
            ]
        elif "information_schema.columns" in query:
            self.rows = [
                ("main", "buildings", "id", "INTEGER", "NO", 1),
                ("main", "buildings", "name", "VARCHAR", "YES", 2),
            ]
        else:
            raise AssertionError(f"unexpected query: {query}")

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConnection:
    def __init__(self):
        self.queries = []

    def cursor(self):
        return FakeCursor(self)


def test_validate_snowflake_schema_checks_expected_columns_and_types():
    report = validate_snowflake_schema(
        FakeConnection(),
        schema="PUBLIC",
        expected={"BUILDINGS": {"ID": "INTEGER", "GEOM_WKT": "VARCHAR", "MISSING": "VARCHAR"}},
    )

    assert report.engine == "Snowflake"
    assert report.database == "ANALYTICS"
    assert report.tables[0].columns[0].name == "ID"
    assert not report.passed
    assert any("MISSING" in issue.message for issue in report.errors)


def test_validate_duckdb_schema_reports_undeclared_columns_as_suggestions():
    report = validate_duckdb_schema(
        FakeConnection(),
        expected={"buildings": {"id": "INTEGER"}},
    )

    assert report.engine == "DuckDB"
    assert report.passed
    assert any(issue.column == "name" for issue in report.suggestions)
    assert report.to_dict()["tables"][0]["columns"]