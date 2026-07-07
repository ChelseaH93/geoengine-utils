# Geospatial API Cookbook

This document contains working examples for interacting with popular geospatial APIs and cloud-native geospatial services using Python.

---

# OpenStreetMap

OpenStreetMap (OSM) is the world's largest open geographic database and provides roads, buildings, land use, points of interest, administrative boundaries, and much more.

## Best For

- Roads
- Buildings
- Amenities
- Parks
- Administrative boundaries

---

## Option 1 - OSMnx (Recommended)

The easiest way to download OpenStreetMap data directly into GeoPandas.

### Install

```bash
pip install osmnx
```

### Download Buildings

```python
import osmnx as ox

buildings = ox.features_from_bbox(
    north=-33.90,
    south=-33.95,
    east=18.50,
    west=18.35,
    tags={
        "building": True
    }
)

buildings.head()
```

Returns

```
GeoDataFrame
```

---

### Download Roads

```python
roads = ox.features_from_bbox(
    north=-33.90,
    south=-33.95,
    east=18.50,
    west=18.35,
    tags={
        "highway": True
    }
)
```

---

### Download Schools

```python
schools = ox.features_from_bbox(
    north=-33.90,
    south=-33.95,
    east=18.50,
    west=18.35,
    tags={
        "amenity": "school"
    }
)
```

---

# Option 2 - Overpass API

Useful when you want complete control over your query or don't want another dependency.

Endpoint

```
https://overpass-api.de/api/interpreter
```

### Roads

```python
import requests
import geopandas as gpd

query = """
[out:json];
way
  ["highway"]
  (-33.95,18.35,-33.90,18.50);
out geom;
"""

response = requests.get(
    "https://overpass-api.de/api/interpreter",
    params={
        "data": query
    },
)

response.raise_for_status()

data = response.json()
```

---

### Buildings

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

### Hospitals

```python
query = """
[out:json];
node
  ["amenity"="hospital"]
  (-33.95,18.35,-33.90,18.50);
out;
"""
```

---

### Restaurants

```python
query = """
[out:json];
node
  ["amenity"="restaurant"]
  (-33.95,18.35,-33.90,18.50);
out;
"""
```

---

### Administrative Boundaries

```python
query = """
[out:json];
relation
  ["boundary"="administrative"];
out geom;
"""
```

---

## Saving to GeoJSON

```python
buildings.to_file(
    "buildings.geojson",
    driver="GeoJSON"
)
```

---

# Quick Reference

| Want... | Tag |
|----------|-----|
| Buildings | `"building": True` |
| Roads | `"highway": True` |
| Schools | `"amenity": "school"` |
| Hospitals | `"amenity": "hospital"` |
| Restaurants | `"amenity": "restaurant"` |
| Parks | `"leisure": "park"` |
| Water | `"natural": "water"` |
| Railways | `"railway": True` |
| Powerlines | `"power": "line"` |
| Rivers | `"waterway": "river"` |