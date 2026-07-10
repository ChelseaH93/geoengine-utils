# Vector utilities

The vector helpers are designed for simple, repeatable workflows around GeoPandas-style data.

## Converting vector inputs

```python
from geoengine_utils.vector import convert_vector

import geopandas as gpd
from shapely.geometry import Point

geometries = [Point(0, 0), Point(1, 1)]
frame = convert_vector(geometries)

print(type(frame))
print(frame.geometry)
```

## Checking readiness

```python
from geoengine_utils import assess_readiness

report = assess_readiness(frame)
print(report.passed)
print(report.format_report())
```

`assess_readiness` auto-detects the dataset type — a GeoDataFrame, GeoSeries, or an iterable of geometry objects all work — and reports errors and warnings (missing CRS, empty features, invalid/self-intersecting geometries, and so on) without you needing to supply that metadata yourself.

## Simplifying geometries

```python
from geoengine_utils.vector import simplify_vector

simplified = simplify_vector(frame, tolerance=0.0)
print(simplified)
```

Use simplification when you need a lighter geometry representation for display, caching, or reduced storage.
