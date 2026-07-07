# Open Geospatial Data Sources

A collection of high-quality, freely available geospatial datasets and APIs for testing, development and production workflows.

---

# OpenStreetMap (OSM)

One of the world's largest crowdsourced mapping datasets.

## Overpass API

Perfect for downloading small areas without downloading the full OSM planet.

### Example - Roads

```python
import requests

query = """
[out:json];
way
  ["highway"]
  (-33.95,18.35,-33.90,18.50);
out geom;
"""

response = requests.get(
    "https://overpass-api.de/api/interpreter",
    params={"data": query},
)

print(response.json())
```

---

### Example - Buildings

```python
query = """
[out:json];
way
  ["building"]
  (-33.95,18.35,-33.90,18.50);
out geom;
"""
```

---

### Example - Schools

```python
query = """
[out:json];
node
  ["amenity"="school"]
  (-33.95,18.35,-33.90,18.50);
out;
"""
```

---

# OSMnx

An excellent Python library for downloading OpenStreetMap data directly into GeoPandas.

Install

```bash
pip install osmnx
```

Example

```python
import osmnx as ox

roads = ox.features_from_bbox(
    north=-33.90,
    south=-33.95,
    east=18.50,
    west=18.35,
    tags={
        "highway": True
    },
)

roads.head()
```

---

# Microsoft Building Footprints

High-quality building polygons generated from aerial imagery.

Coverage includes:

- United States
- Canada
- South Africa
- Australia
- Much of Europe

Example

```python
import geopandas as gpd

gdf = gpd.read_parquet(
    "south_africa_buildings.parquet"
)
```

---

# Natural Earth

Small-scale global datasets perfect for demos.

Includes

- Countries
- Rivers
- Lakes
- Coastlines
- Urban Areas

```python
import geopandas as gpd

world = gpd.read_file(
    "ne_110m_admin_0_countries.shp"
)
```

---

# USGS 3DEP

High-resolution DEMs for the United States.

Ideal for testing raster workflows.

---

# Copernicus DEM

Global Digital Elevation Model.

30m and 90m resolution.

---

# Sentinel-2

10 metre multispectral imagery.

Available free via AWS and Microsoft's Planetary Computer.

Example

```python
from pystac_client import Client

catalog = Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1"
)

search = catalog.search(
    collections=["sentinel-2-l2a"],
    bbox=[18.3,-34.1,18.7,-33.8],
)

items = list(search.items())

print(len(items))
```

---

# Landsat

30 metre multispectral imagery.

Ideal for change detection.

---

# Planetary Computer

One of the best places to access cloud-native geospatial datasets.

Collections include

- Sentinel
- Landsat
- NAIP
- DEMs
- Climate
- LiDAR

---

# AWS Open Data

Contains numerous GIS datasets including

- Sentinel
- Landsat
- NOAA
- LiDAR

---

# NOAA

Weather

Climate

Bathymetry

Ocean currents

---

# ESA

Sentinel satellite imagery.

---

# NASA EarthData

Global environmental datasets.

---

# GeoParquet Examples

Excellent test datasets.

https://github.com/opengeospatial/geoparquet

---

# PMTiles Examples

https://protomaps.com/downloads

---

# STAC Catalogs

Microsoft Planetary Computer

Earth Search

Radiant Earth
