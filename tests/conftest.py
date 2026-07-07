from pathlib import Path

import pytest
from shapely.geometry import box


TEST_DATA = Path(__file__).parent / "data"


@pytest.fixture
def raster_path():
    return TEST_DATA / "test_dem.tif"


@pytest.fixture
def cape_town_bbox():
    return box(
        18.3,
        -34.1,
        18.7,
        -33.8,
    )

@pytest.fixture
def london_bbox():
    return box(
        -0.2,
        51.4,
        0.1,
        51.6,
    )