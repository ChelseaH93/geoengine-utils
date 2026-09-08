from geoengine_utils.validation import audit_postgis, explain_postgis_query
from geoengine_utils.validation.postgis import quote_identifier


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=()):
        self.connection.queries.append(query)
        if query.startswith("SELECT current_database"):
            self.rows = [("demo",)]
        elif query.startswith("SELECT version"):
            self.rows = [("PostgreSQL 16",)]
        elif query.startswith("SELECT postgis_full_version"):
            self.rows = [("POSTGIS=3.4",)]
        elif "FROM geometry_columns" in query:
            self.rows = [("public", "roads", "geom", "LINESTRING", 4326, 2)]
        elif "FROM pg_indexes" in query:
            self.rows = []
        elif "FROM pg_stat_user_tables" in query:
            self.rows = [("public", "roads", 500, 2)]
        elif "ST_IsValid" in query:
            self.rows = [(100, 3, 1, 4)]
        elif query.startswith("EXPLAIN"):
            self.rows = [([{"Plan": {"Node Type": "Seq Scan", "Relation Name": "roads"}}],)]
        else:
            raise AssertionError(f"unexpected query: {query}")

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self):
        self.queries = []

    def cursor(self):
        return FakeCursor(self)


def test_audit_postgis_reports_quality_index_and_scan_findings():
    connection = FakeConnection()

    report = audit_postgis(connection)

    assert report.passed is False
    assert report.database == "demo"
    assert report.tables[0].feature_count == 100
    assert report.tables[0].invalid_geometry_count == 4
    categories = {issue.category for issue in report.issues}
    assert {"data_quality", "spatial_index", "query_optimization"} <= categories
    assert "CREATE INDEX" in report.format_report()


def test_explain_postgis_query_suggests_improvement_for_sequential_scan():
    plan = explain_postgis_query(FakeConnection(), "SELECT * FROM roads WHERE id = %s", (1,))

    assert plan.plan["Node Type"] == "Seq Scan"
    assert any(issue.category == "query_optimization" for issue in plan.issues)


def test_quote_identifier_escapes_names_and_rejects_dotted_values():
    assert quote_identifier('road"name') == '"road""name"'

    try:
        quote_identifier("public.roads")
    except ValueError:
        pass
    else:
        raise AssertionError("dotted SQL identifiers must be rejected")