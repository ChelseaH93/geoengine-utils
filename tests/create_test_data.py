from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

output = Path(__file__).parent / "data" / "test_dem.tif"

output.parent.mkdir(exist_ok=True)

array = np.random.rand(10, 10).astype("float32")

transform = from_origin(
    18.0,
    -33.0,
    10,
    10,
)

with rasterio.open(
    output,
    "w",
    driver="GTiff",
    width=10,
    height=10,
    count=1,
    dtype="float32",
    crs="EPSG:4326",
    transform=transform,
) as dst:
    dst.write(array, 1)

print("Created:", output)


def south_africa_bbox():

    return box(
        16,
        -35,
        33,
        -22,
    )
