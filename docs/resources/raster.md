# Raster utilities

The raster module focuses on reading and validating geospatial rasters in a predictable way.

## Reading raster metadata

```python
from geoengine_utils import get_raster_metadata

metadata = get_raster_metadata("example.tif")

print(metadata.width)
print(metadata.height)
print(metadata.crs)
print(metadata.bounds)
```

The metadata object includes the core information most pipelines need before they begin processing:

- width and height
- CRS reference
- band count
- data type
- resolution
- bounds
- NoData value

## Validating raster data

```python
from geoengine_utils import validate_raster

report = validate_raster("example.tif")

print(report.passed)
print(report.errors)
print(report.warnings)
```

Validation is intentionally lightweight and aimed at catching common issues such as:

- missing CRS definitions
- invalid dimensions
- empty band sets
- missing NoData values

## When to use these helpers

Use the raster helpers when you want a fast sanity check before applying reprojection, tiling, or cloud conversion workflows.
