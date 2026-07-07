# API guide

This page collects the most relevant package entry points and a few external geospatial services that fit naturally with the toolkit.

## geoengine-utils package APIs

### Raster inspection and validation

```python
from geoengine_utils import get_raster_metadata, validate_raster

metadata = get_raster_metadata("example.tif")
report = validate_raster("example.tif")
```

### CRS helpers

```python
from geoengine_utils import recommend_crs, validate_crs

validate_crs("EPSG:4326")
recommend_crs(latitude=-33.9, longitude=18.4)
```

### Vector helpers

```python
from geoengine_utils.vector import convert_vector, simplify_vector, validate_vector

import geopandas as gpd
from shapely.geometry import Point

geometries = [Point(0, 0), Point(1, 1)]
frame = convert_vector(geometries)

validate_vector(frame)
simplified = simplify_vector(frame, tolerance=0.0)
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
