import geopandas as gpd
from shapely.geometry import Point, Polygon

from geoengine_utils.validation import PipelineAuditConfig, audit_pipeline_stage


def _frame(points, *, crs="EPSG:4326", extra=False):
    data = {"id": list(range(len(points)))}
    if extra:
        data["new_field"] = ["x"] * len(points)
    return gpd.GeoDataFrame(data, geometry=points, crs=crs)


def test_audit_pipeline_stage_passes_a_stable_valid_stage():
    source = _frame([Point(0, 0), Point(1, 1)])
    result = _frame([Point(0, 0), Point(1, 1)])

    report = audit_pipeline_stage(source, result)

    assert report.passed
    assert report.input_summary.feature_count == 2
    assert report.output_summary.geometry_types == ("Point",)


def test_audit_pipeline_stage_reports_crs_quality_extent_and_schema_regressions():
    source = _frame([Point(0, 0), Point(1, 1)])
    invalid = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    result = _frame([invalid], crs="EPSG:3857", extra=True)

    report = audit_pipeline_stage(
        source,
        result,
        config=PipelineAuditConfig(
            expected_crs="EPSG:4326",
            expected_geometry_types=("Point",),
            allow_schema_additions=False,
        ),
    )

    assert not report.passed
    categories = {issue.category for issue in report.issues}
    assert {"crs", "geometry_type", "geometry_quality", "schema"} <= categories
    assert report.to_dict()["input"]["feature_count"] == 2


def test_audit_pipeline_stage_rejects_negative_thresholds():
    source = _frame([Point(0, 0)])

    try:
        audit_pipeline_stage(
            source,
            source,
            config=PipelineAuditConfig(max_feature_count_change=-0.1),
        )
    except ValueError as exc:
        assert "max_feature_count_change" in str(exc)
    else:
        raise AssertionError("negative thresholds must be rejected")