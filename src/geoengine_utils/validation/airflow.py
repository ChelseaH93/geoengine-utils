"""Airflow DAG structure and operational configuration audits."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from os import PathLike
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class AirflowAuditConfig:
    """Policy thresholds for DAG structure and operational settings."""

    require_schedule: bool = False
    require_task_owner: bool = True
    require_retries: bool = True
    require_execution_timeout: bool = False
    require_tags: bool = False
    max_task_count: int | None = None
    max_active_runs: int | None = None
    max_active_tasks: int | None = None


@dataclass(frozen=True)
class AirflowAuditIssue:
    """An actionable Airflow DAG audit finding."""

    severity: str
    category: str
    message: str
    suggestion: str
    dag_id: str | None = None
    task_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "suggestion": self.suggestion,
            "dag_id": self.dag_id,
            "task_id": self.task_id,
        }


@dataclass(frozen=True)
class AirflowTaskAudit:
    """Normalized task structure and operational settings."""

    task_id: str
    upstream_task_ids: tuple[str, ...]
    downstream_task_ids: tuple[str, ...]
    owner: str | None
    retries: int | None
    execution_timeout_seconds: float | None
    pool: str | None
    priority_weight: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "upstream_task_ids": list(self.upstream_task_ids),
            "downstream_task_ids": list(self.downstream_task_ids),
            "owner": self.owner,
            "retries": self.retries,
            "execution_timeout_seconds": self.execution_timeout_seconds,
            "pool": self.pool,
            "priority_weight": self.priority_weight,
        }


@dataclass(frozen=True)
class AirflowAuditReport:
    """Complete DAG structure and operational audit result."""

    dag_id: str
    schedule: str | None
    catchup: bool | None
    max_active_runs: int | None
    max_active_tasks: int | None
    tags: tuple[str, ...]
    tasks: tuple[AirflowTaskAudit, ...]
    issues: tuple[AirflowAuditIssue, ...]

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def errors(self) -> tuple[AirflowAuditIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[AirflowAuditIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def suggestions(self) -> tuple[AirflowAuditIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "suggestion")

    def to_dict(self) -> dict[str, Any]:
        return {
            "dag_id": self.dag_id,
            "schedule": self.schedule,
            "catchup": self.catchup,
            "max_active_runs": self.max_active_runs,
            "max_active_tasks": self.max_active_tasks,
            "tags": list(self.tags),
            "tasks": [task.to_dict() for task in self.tasks],
            "issues": [issue.to_dict() for issue in self.issues],
            "passed": self.passed,
        }

    def format_report(self) -> str:
        counts = {
            severity: sum(issue.severity == severity for issue in self.issues)
            for severity in ("error", "warning", "suggestion")
        }
        lines = [
            f"Airflow DAG audit: {self.dag_id}, {len(self.tasks)} tasks, "
            f"{counts['error']} errors, {counts['warning']} warnings, "
            f"{counts['suggestion']} suggestions"
        ]
        lines.extend(
            f"- [{issue.severity}] {issue.message} Suggestion: {issue.suggestion}"
            for issue in self.issues
        )
        return "\n".join(lines)


def audit_airflow_dag(
    dag: Any,
    *,
    config: AirflowAuditConfig | None = None,
) -> AirflowAuditReport:
    """Audit an Airflow DAG object without importing Airflow at module load time."""

    policy = config or AirflowAuditConfig()
    dag_id = str(getattr(dag, "dag_id", ""))
    if not dag_id:
        raise ValueError("dag must provide a non-empty dag_id")
    raw_tasks = list(getattr(dag, "task_dict", {}).values())
    task_ids = {str(getattr(task, "task_id", "")) for task in raw_tasks}
    if "" in task_ids:
        raise ValueError("every Airflow task must provide a non-empty task_id")
    tasks = tuple(_task_audit(task) for task in raw_tasks)
    issues = _audit_dag_structure(dag, tasks, task_ids, policy)
    return AirflowAuditReport(
        dag_id=dag_id,
        schedule=_schedule_value(dag),
        catchup=_optional_bool(dag, "catchup"),
        max_active_runs=_optional_int(dag, "max_active_runs"),
        max_active_tasks=_optional_int(dag, "max_active_tasks", "concurrency"),
        tags=tuple(str(tag) for tag in (getattr(dag, "tags", None) or ())),
        tasks=tasks,
        issues=tuple(issues),
    )


def audit_airflow_dag_file(
    path: str | PathLike[str],
    *,
    dag_id: str | None = None,
    config: AirflowAuditConfig | None = None,
) -> tuple[AirflowAuditReport, ...]:
    """Load DAGs from a Python file with Airflow's DagBag and audit them."""

    try:
        from airflow.models import DagBag
    except ImportError as exc:
        raise ImportError(
            "Airflow is required for DAG-file auditing. Install with `pip install geoengine-utils[airflow]`."
        ) from exc
    dag_bag = DagBag(dag_folder=str(Path(path)), include_examples=False)
    if dag_bag.import_errors:
        errors = "; ".join(f"{name}: {message}" for name, message in dag_bag.import_errors.items())
        raise ValueError(f"Airflow DAG file contains import errors: {errors}")
    dags = list(dag_bag.dags.values())
    if dag_id is not None:
        dags = [dag for dag in dags if dag.dag_id == dag_id]
    if not dags:
        raise ValueError(f"No Airflow DAGs found in {path}")
    return tuple(audit_airflow_dag(dag, config=config) for dag in dags)


def _task_audit(task: Any) -> AirflowTaskAudit:
    timeout = getattr(task, "execution_timeout", None)
    return AirflowTaskAudit(
        task_id=str(task.task_id),
        upstream_task_ids=tuple(sorted(str(value) for value in (getattr(task, "upstream_task_ids", None) or ()))),
        downstream_task_ids=tuple(sorted(str(value) for value in (getattr(task, "downstream_task_ids", None) or ()))),
        owner=_optional_string(task, "owner"),
        retries=_optional_int(task, "retries"),
        execution_timeout_seconds=_duration_seconds(timeout),
        pool=_optional_string(task, "pool"),
        priority_weight=_optional_int(task, "priority_weight"),
    )


def _audit_dag_structure(
    dag: Any,
    tasks: Sequence[AirflowTaskAudit],
    task_ids: set[str],
    config: AirflowAuditConfig,
) -> list[AirflowAuditIssue]:
    dag_id = str(dag.dag_id)
    issues: list[AirflowAuditIssue] = []
    if config.max_task_count is not None and len(tasks) > config.max_task_count:
        issues.append(
            AirflowAuditIssue(
                "error",
                "structure",
                f"DAG {dag_id} has {len(tasks)} tasks, exceeding the configured maximum of {config.max_task_count}.",
                "Split the workflow into smaller DAGs or raise the limit deliberately.",
                dag_id=dag_id,
            )
        )
    if not tasks:
        issues.append(
            AirflowAuditIssue(
                "error",
                "structure",
                f"DAG {dag_id} contains no tasks.",
                "Add at least one task or remove the empty DAG from deployment.",
                dag_id=dag_id,
            )
        )
    if _has_cycle(tasks):
        issues.append(
            AirflowAuditIssue(
                "error",
                "structure",
                f"DAG {dag_id} contains a dependency cycle.",
                "Remove the cyclic dependency so Airflow can produce a valid topological execution order.",
                dag_id=dag_id,
            )
        )
    for task in tasks:
        missing = (set(task.upstream_task_ids) | set(task.downstream_task_ids)) - task_ids
        if missing:
            issues.append(
                AirflowAuditIssue(
                    "error",
                    "structure",
                    f"Task {task.task_id} references missing tasks: {sorted(missing)}.",
                    "Fix the dependency declaration or remove the stale task reference.",
                    dag_id=dag_id,
                    task_id=task.task_id,
                )
            )
        if len(tasks) > 1 and not task.upstream_task_ids and not task.downstream_task_ids:
            issues.append(
                AirflowAuditIssue(
                    "warning",
                    "structure",
                    f"Task {task.task_id} is disconnected from the rest of the DAG.",
                    "Connect it to the workflow or move it to a separate DAG.",
                    dag_id=dag_id,
                    task_id=task.task_id,
                )
            )
        if config.require_task_owner and not task.owner:
            issues.append(
                AirflowAuditIssue(
                    "warning",
                    "operations",
                    f"Task {task.task_id} has no owner.",
                    "Set an owner so failures have a clear operational contact.",
                    dag_id=dag_id,
                    task_id=task.task_id,
                )
            )
        if config.require_retries and (task.retries is None or task.retries <= 0):
            issues.append(
                AirflowAuditIssue(
                    "suggestion",
                    "operations",
                    f"Task {task.task_id} has no retry policy.",
                    "Configure retries for transient failures, with an appropriate retry delay.",
                    dag_id=dag_id,
                    task_id=task.task_id,
                )
            )
        if config.require_execution_timeout and task.execution_timeout_seconds is None:
            issues.append(
                AirflowAuditIssue(
                    "warning",
                    "operations",
                    f"Task {task.task_id} has no execution timeout.",
                    "Set execution_timeout to prevent stuck tasks from consuming workers indefinitely.",
                    dag_id=dag_id,
                    task_id=task.task_id,
                )
            )
    schedule = _schedule_value(dag)
    if config.require_schedule and schedule is None:
        issues.append(
            AirflowAuditIssue(
                "warning",
                "operations",
                f"DAG {dag_id} has no schedule.",
                "Set a schedule or explicitly document that the DAG is externally triggered.",
                dag_id=dag_id,
            )
        )
    catchup = _optional_bool(dag, "catchup")
    if catchup is True:
        issues.append(
            AirflowAuditIssue(
                "suggestion",
                "operations",
                f"DAG {dag_id} has catchup enabled.",
                "Disable catchup unless historical interval backfills are intentional and capacity-planned.",
                dag_id=dag_id,
            )
        )
    tags = getattr(dag, "tags", None) or ()
    if config.require_tags and not tags:
        issues.append(
            AirflowAuditIssue(
                "suggestion",
                "operations",
                f"DAG {dag_id} has no tags.",
                "Add ownership, domain, and criticality tags for discoverability and operational filtering.",
                dag_id=dag_id,
            )
        )
    max_active_runs = _optional_int(dag, "max_active_runs")
    if max_active_runs is not None and max_active_runs <= 0:
        issues.append(
            AirflowAuditIssue(
                "error",
                "operations",
                f"DAG {dag_id} has invalid max_active_runs={max_active_runs}.",
                "Set max_active_runs to a positive value.",
                dag_id=dag_id,
            )
        )
    if config.max_active_runs is not None and max_active_runs is not None and max_active_runs > config.max_active_runs:
        issues.append(
            AirflowAuditIssue(
                "warning",
                "operations",
                f"DAG {dag_id} allows {max_active_runs} active runs, above the policy limit of {config.max_active_runs}.",
                "Reduce max_active_runs or document why the higher concurrency is safe.",
                dag_id=dag_id,
            )
        )
    max_active_tasks = _optional_int(dag, "max_active_tasks", "concurrency")
    if config.max_active_tasks is not None and max_active_tasks is not None and max_active_tasks > config.max_active_tasks:
        issues.append(
            AirflowAuditIssue(
                "warning",
                "operations",
                f"DAG {dag_id} allows {max_active_tasks} active tasks, above the policy limit of {config.max_active_tasks}.",
                "Reduce the task concurrency or document the worker capacity supporting it.",
                dag_id=dag_id,
            )
        )
    return issues


def _has_cycle(tasks: Sequence[AirflowTaskAudit]) -> bool:
    remaining = {task.task_id: set(task.upstream_task_ids) for task in tasks}
    ready = [task_id for task_id, upstream in remaining.items() if not upstream]
    visited = 0
    while ready:
        task_id = ready.pop()
        visited += 1
        for candidate, upstream in remaining.items():
            if task_id in upstream:
                upstream.remove(task_id)
                if not upstream:
                    ready.append(candidate)
    return visited != len(remaining)


def _schedule_value(dag: Any) -> str | None:
    schedule = getattr(dag, "schedule", getattr(dag, "schedule_interval", None))
    if schedule is None:
        return None
    return str(schedule)


def _duration_seconds(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, timedelta):
        return value.total_seconds()
    total_seconds = getattr(value, "total_seconds", None)
    return float(total_seconds()) if callable(total_seconds) else None


def _optional_string(value: Any, name: str) -> str | None:
    result = getattr(value, name, None)
    return str(result) if result not in (None, "") else None


def _optional_int(value: Any, *names: str) -> int | None:
    for name in names:
        result = getattr(value, name, None)
        if result is not None:
            return int(result)
    return None


def _optional_bool(value: Any, name: str) -> bool | None:
    result = getattr(value, name, None)
    return bool(result) if result is not None else None


__all__ = [
    "AirflowAuditConfig",
    "AirflowAuditIssue",
    "AirflowAuditReport",
    "AirflowTaskAudit",
    "audit_airflow_dag",
    "audit_airflow_dag_file",
]
