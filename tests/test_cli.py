from geoengine_utils import main


def test_main_version(capsys):
    exit_code = main(["--version"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "geoengine-utils" in captured.out.lower()
