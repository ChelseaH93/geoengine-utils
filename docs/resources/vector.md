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

## Validating vector inputs

```python
from geoengine_utils.vector import validate_vector

valid = validate_vector(frame)
print(valid)
```

The validator returns `True` for objects that can be treated as meaningful vector data, such as a GeoDataFrame or a collection of geometry objects.

## Simplifying geometries

```python
from geoengine_utils.vector import simplify_vector

simplified = simplify_vector(frame, tolerance=0.0)
print(simplified)
```

Use simplification when you need a lighter geometry representation for display, caching, or reduced storage.
