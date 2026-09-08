import json

import geopandas as gpd
from shapely.geometry import Point

from geoengine_utils import main
from geoengine_utils.ci import main_ci, run_ci_checks, run_ci_config


def test_run_ci_checks_passes_dataset_configuration():
    report = run_ci_checks(
        {
            "datasets": [{"name": "dem", "path": "tests/data/test_dem.tif"}],
        }
    )

    assert report.passed
    assert report.checks[0].check_type == "dataset"
    assert report.to_dict()["checks"][0]["passed"] is True


def test_ci_cli_returns_nonzero_and_json_for_missing_dataset(tmp_path, capsys):
    config = tmp_path / "ci.json"
    config.write_text(
        json.dumps({"datasets": [{"name": "missing", "path": "does-not-exist.tif"}]}),
        encoding="utf-8",
    )

    exit_code = main(["ci", str(config), "--json"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert '"passed": false' in captured.out
    assert "missing" in captured.out


def test_ci_runner_requires_configured_checks():
    try:
        run_ci_checks({})
    except ValueError as exc:
        assert "datasets or pipeline_stages" in str(exc)
    else:
        raise AssertionError("empty CI configuration must be rejected")


def test_ci_runner_handles_pipeline_checks_and_warning_policy(tmp_path):
    source = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")
    input_path = tmp_path / "input.geojson"
    output_path = tmp_path / "output.geojson"
    source.to_file(input_path, driver="GeoJSON")
    source.assign(extra=["x"]).to_file(output_path, driver="GeoJSON")

    report = run_ci_checks(
        {
            "fail_on_warnings": False,
            "pipeline_stages": [
                {
                    "input": str(input_path),
                    "output": str(output_path),
                    "config": {"allow_schema_additions": True},
                }
            ],
        }
    )

    assert report.passed
    assert report.checks[0].details["issues"]
    assert "pipeline_stage" in report.format_report()


def test_ci_runner_reports_missing_fields_and_crs_mismatch(tmp_path):
    config = tmp_path / "ci.json"
    config.write_text(json.dumps({"datasets": [{"name": "bad"}]}), encoding="utf-8")
    result = run_ci_config(config)
    assert not result.passed
    assert "requires a path" in result.errors[0]

    output = main_ci([str(tmp_path / "missing.json")])
    assert output == 2


def test_ci_dataset_check_can_compare_expected_crs(tmp_path):
    path = tmp_path / "point.geojson"
    gpd.GeoDataFrame(geometry=[Point(0, 0)], crs="EPSG:4326").to_file(
        path, driver="GeoJSON"
    )

    result = run_ci_checks(
        {"datasets": [{"path": str(path), "expected_crs": "EPSG:32616"}]}
    )
    assert not result.passed
    assert "does not match" in result.errors[0]
