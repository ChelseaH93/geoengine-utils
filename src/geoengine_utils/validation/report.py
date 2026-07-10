"""Validation reporting primitives shared across dataset validators."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ValidationIssue:
    """A single validation issue with a severity and message."""

    severity: str
    message: str


@dataclass(slots=True)
class ValidationReport:
    """Collection of validation issues with human-friendly summaries."""

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def errors(self) -> list[str]:
        """Messages for every issue with ``error`` severity."""

        return [issue.message for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[str]:
        """Messages for every issue with ``warning`` severity."""

        return [issue.message for issue in self.issues if issue.severity == "warning"]

    def add_error(self, message: str) -> None:
        self.issues.append(ValidationIssue("error", message))

    def add_warning(self, message: str) -> None:
        self.issues.append(ValidationIssue("warning", message))

    def summary(self) -> str:
        error_count = len(self.errors)
        warning_count = len(self.warnings)
        status = "passed" if self.passed else "failed"
        return (
            f"Validation {status}: {error_count} error"
            f"{'s' if error_count != 1 else ''}, {warning_count} warning"
            f"{'s' if warning_count != 1 else ''}."
        )

    def format_report(self) -> str:
        lines = [self.summary()]
        for issue in self.issues:
            lines.append(f"- [{issue.severity}] {issue.message}")
        return "\n".join(lines)


class ValidationError(Exception):
    """Raised when a dataset or pipeline payload fails validation."""

    def __init__(self, report: ValidationReport):
        self.report = report
        super().__init__(report.format_report())
