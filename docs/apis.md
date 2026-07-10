# API guide

This page collects the most relevant package entry points and a few external geospatial services that fit naturally with the toolkit.

## geoengine-utils package APIs

### Raster inspection and readiness

```python
from geoengine_utils import assess_readiness, get_raster_metadata

metadata = get_raster_metadata("example.tif")
report = assess_readiness("example.tif")
```

### CRS helpers

```python
from geoengine_utils import recommend_crs, validate_crs

validate_crs("EPSG:4326")
recommend_crs(latitude=-33.9, longitude=18.4)
```

### Vector helpers

```python
from geoengine_utils import assess_readiness
from geoengine_utils.vector import convert_vector, simplify_vector

import geopandas as gpd
from shapely.geometry import Point

geometries = [Point(0, 0), Point(1, 1)]
frame = convert_vector(geometries)

assess_readiness(frame)
simplified = simplify_vector(frame, tolerance=0.0)
```

### Readiness assessment

`assess_readiness` is the single entry point for checking whether a raster or vector dataset is ready for production use. It accepts a file path, a GeoDataFrame/GeoSeries, or an iterable of geometries and infers the dataset type and metadata it needs automatically.

```python
from geoengine_utils import assess_readiness

print(assess_readiness("demo.tif").summary())
print(assess_readiness("demo.geojson").format_report())
```

For ETL-style pipelines that want to validate function inputs/outputs against a typed schema explicitly, the lower-level schema classes and decorator remain available.

```python
from geoengine_utils import RasterDataset, VectorDataset, ValidationReport, validate_dataset

raster = RasterDataset(name="demo", path="demo.tif", crs="EPSG:4326", bounds=(0, 0, 1, 1))
vector = VectorDataset(name="demo", crs="EPSG:4326", bounds=(0, 0, 1, 1), geometry=None, topology=False)

print(raster.validate().summary())
print(vector.validate().format_report())

@validate_dataset(input_schema=VectorDataset, output_schema=VectorDataset)
def transform(data):
    return data
```

## External services worth integrating

### OpenStreetMap

OpenStreetMap is a good source for local vector data and can be queried with OSMnx or the Overpass API.

```bash
pip install osmnx
```

### Microsoft Planetary Computer

This is a strong choice when you want to explore STAC-based raster and vector collections in a cloud-native workflow.

```python
from pystac_client import Client

catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
```

## Recommended usage pattern

1. Start with the local package helpers for validation and inspection.
2. Use external services when you need additional data sources.
3. Keep the data in GeoPandas-friendly formats for downstream processing.
