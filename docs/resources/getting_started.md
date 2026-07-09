# Getting started

geoengine-utils is a small Python toolkit for checking whether geospatial data is suitable for downstream pipelines. It focuses on practical validation steps such as inspecting raster metadata, validating CRS information, and preparing vector data for further processing.

## Installation

Install the package in editable mode from the repository root:

```bash
pip install -r requirements-dev.txt
pip install -e .
```

## Quick example

### Raster metadata and validation

```python
from geoengine_utils import get_raster_metadata, validate_raster

result = validate_raster("example.tif")
metadata = get_raster_metadata("example.tif")

print(metadata)
print(result.passed)
```

### CRS utilities

```python
from geoengine_utils import recommend_crs, validate_crs

is_valid = validate_crs("EPSG:4326")
recommendation = recommend_crs(latitude=-33.9, longitude=18.4)

print(is_valid)
print(recommendation)
```

### Vector helpers

```python
from geoengine_utils.vector import convert_vector, simplify_vector, validate_vector

import geopandas as gpd
from shapely.geometry import Point

geometries = [Point(0, 0), Point(1, 1)]
frame = convert_vector(geometries)

print(validate_vector(frame))
simplified = simplify_vector(frame, tolerance=0.0)
```

### Shared validation workflow

For ETL-style pipelines, the package exposes a shared validation framework that can validate raster and vector datasets with the same reporting model.

```python
from geoengine_utils import RasterDataset, VectorDataset, validate_dataset

raster = RasterDataset(name="demo", path="demo.tif", crs="EPSG:4326", bounds=(0, 0, 1, 1))
vector = VectorDataset(name="demo", crs="EPSG:4326", bounds=(0, 0, 1, 1), geometry=None, topology=False)

print(raster.validate().summary())

@validate_dataset(input_schema=VectorDataset, output_schema=VectorDataset)
def transform(data):
    return data
```

## Recommended workflow

1. Inspect the input dataset with the relevant metadata helpers.
2. Validate the dataset against basic production checks.
3. Transform or simplify the data only when the validation output suggests it is necessary.
4. Save the cleaned output in a format that fits your downstream tooling.
