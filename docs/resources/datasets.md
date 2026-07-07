# Datasets and sample sources

This page collects a small set of public geospatial datasets and services that are useful for testing, exploration, and integration work.

## Vector datasets

### Natural Earth

Natural Earth is a good starting point for small-scale global examples.

```python
import geopandas as gpd

world = gpd.read_file("ne_110m_admin_0_countries.shp")
```

### OpenStreetMap

OpenStreetMap is useful for local-area vector workflows and can be accessed through tools such as OSMnx or the Overpass API.

```bash
pip install osmnx
```

```python
import osmnx as ox

roads = ox.features_from_bbox(
    north=-33.90,
    south=-33.95,
    east=18.50,
    west=18.35,
    tags={"highway": True},
)
```

## Raster datasets

### USGS 3DEP

High-resolution elevation data for the United States. This is a strong choice for testing raster metadata and validation flows.

### Copernicus DEM

Global digital elevation data with broad coverage for experimentation and automated processing pipelines.

### Sentinel-2 and Landsat

These satellite products are useful for evaluating cloud-native data access and raster workflows.

## Cloud-native catalog services

### Microsoft Planetary Computer

A good source for STAC-based discovery and access to imagery and other geospatial products.

```python
from pystac_client import Client

catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
```

### AWS Open Data

AWS hosts a wide range of public geospatial datasets, including imagery and other scientific data products.

## GeoParquet examples

GeoParquet is a practical format for storing and sharing geospatial data in a modern tabular workflow.

See: https://github.com/opengeospatial/geoparquet

# PMTiles Examples

https://protomaps.com/downloads

---

# STAC Catalogs

Microsoft Planetary Computer

Earth Search

Radiant Earth
