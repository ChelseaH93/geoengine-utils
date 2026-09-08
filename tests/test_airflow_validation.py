from types import SimpleNamespace

from geoengine_utils.validation import AirflowAuditConfig, audit_airflow_dag


def _task(task_id, *, upstream=(), downstream=(), owner=None, retries=0, timeout=None):
    return SimpleNamespace(
        task_id=task_id,
        upstream_task_ids=set(upstream),
        downstream_task_ids=set(downstream),
        owner=owner,
        retries=retries,
        execution_timeout=timeout,
        pool="default_pool",
        priority_weight=1,
    )


def test_audit_airflow_dag_reports_structure_and_operational_findings():
    tasks = {
        "extract": _task("extract", downstream=("transform",)),
        "transform": _task("transform", upstream=("extract",), downstream=("load",)),
        "load": _task("load", upstream=("transform",)),
        "orphan": _task("orphan"),
    }
    dag = SimpleNamespace(
        dag_id="building_pipeline",
        task_dict=tasks,
        schedule=None,
        catchup=True,
        max_active_runs=8,
        max_active_tasks=32,
        tags=[],
    )

    report = audit_airflow_dag(
        dag,
        config=AirflowAuditConfig(
            require_schedule=True,
            require_task_owner=True,
            require_retries=True,
            require_execution_timeout=True,
            require_tags=True,
            max_active_runs=4,
            max_active_tasks=16,
        ),
    )

    assert report.passed
    categories = {issue.category for issue in report.issues}
    assert {"structure", "operations"} <= categories
    assert any("orphan" in issue.message for issue in report.warnings)
    assert any("catchup" in issue.message for issue in report.suggestions)
    assert report.to_dict()["tasks"]


def test_audit_airflow_dag_detects_cycles_and_missing_dependencies():
    dag = SimpleNamespace(
        dag_id="bad_pipeline",
        task_dict={
            "a": _task("a", upstream=("b",), downstream=("b", "missing")),
            "b": _task("b", upstream=("a",), downstream=("a",)),
        },
        schedule="@daily",
        catchup=False,
        max_active_runs=1,
        max_active_tasks=2,
        tags=["geo"],
    )

    report = audit_airflow_dag(dag)

    assert not report.passed
    assert any("cycle" in issue.message for issue in report.errors)
    assert any("missing" in issue.message for issue in report.errors)