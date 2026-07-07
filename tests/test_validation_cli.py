from pathlib import Path

from geoengine_utils import main


def test_validation_cli_reports_success(raster_path, capsys):
    exit_code = main(["validate", str(raster_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "passed" in captured.out.lower()
    assert "errors" in captured.out.lower()


def test_estimate_crs_cli_reports_recommendation(capsys):
    path = Path(__file__).parent / "data" / "test_polygon.geojson"

    exit_code = main(["estimate-crs", str(path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "recommended_crs=" in captured.out
