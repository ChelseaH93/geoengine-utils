import pytest

from geoengine_utils.validation import (
    RasterDataset,
    ValidationError,
    ValidationIssue,
    ValidationReport,
    VectorDataset,
    validate_dataset,
)


def test_validation_report_summary_includes_actionable_counts():
    report = ValidationReport(
        issues=[
            ValidationIssue("error", "CRS is missing"),
            ValidationIssue("warning", "NoData is undefined"),
        ]
    )

    summary = report.summary()

    assert "1 error" in summary
    assert "1 warning" in summary
    assert "CRS is missing" in report.format_report()


def test_raster_dataset_validation_reports_crs_and_bounds():
    dataset = RasterDataset(name="demo", path="demo.tif", crs=None, bounds=None)

    report = dataset.validate()

    assert report.passed is False
    assert any("CRS" in issue.message for issue in report.issues)
    assert any("bounds" in issue.message.lower() for issue in report.issues)


def test_validate_dataset_decorator_rejects_invalid_payloads():
    @validate_dataset(input_schema=VectorDataset, output_schema=VectorDataset)
    def transform(data):
        return data

    invalid_dataset = VectorDataset(name="bad", crs=None, bounds=None, geometry=None, topology=False)

    with pytest.raises(ValidationError) as excinfo:
        transform(invalid_dataset)

    assert "CRS" in str(excinfo.value)
