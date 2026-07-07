from pathlib import Path

from geoengine_utils import main


def test_validation_cli_reports_success(raster_path, capsys):
    exit_code = main(["validate", str(raster_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "passed" in captured.out.lower()
    assert "errors" in captured.out.lower()
