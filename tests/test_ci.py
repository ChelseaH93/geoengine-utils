import json

from geoengine_utils import main
from geoengine_utils.ci import run_ci_checks


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
