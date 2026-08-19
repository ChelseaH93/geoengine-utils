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

## Repairing geometries

Use `repair_vector` when readiness checks identify invalid or self-intersecting geometries. It returns a new GeoDataFrame, preserves the input columns, index, and CRS, and leaves the original unchanged.

```python
from geoengine_utils import assess_readiness
from geoengine_utils.vector import repair_vector

repaired = repair_vector(frame, drop_empty=True)
print(assess_readiness(repaired).format_report())
```

The repair uses Shapely's `make_valid` operation. A repaired polygon may become a MultiPolygon or another valid geometry type, so inspect the result before writing it to a workflow that requires one geometry type. Use `drop_empty=True` to remove empty or null geometries after repair; the default preserves those rows for inspection.
