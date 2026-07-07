# geoengine-utils

> Modern Python utilities for geospatial data engineering.

geoengine-utils is an open-source toolkit designed to simplify common geospatial data engineering tasks such as validating raster datasets, preparing cloud-native geospatial formats, and building reliable GIS data pipelines.

The goal is to provide production-ready utilities that help engineers build scalable geospatial workflows rather than ad hoc scripts.

---

## ✨ Features

### Current

- Read raster metadata
- Validate raster datasets
- Production-ready validation reports

### Planned

- Cloud Optimized GeoTIFF (COG) validation
- COG conversion
- GeoParquet utilities
- PMTiles generation
- STAC metadata generation
- Raster clipping
- Raster reprojection
- CRS utilities
- Vector validation
- Command Line Interface
- Performance benchmarking

---

## Installation

Clone the repository

```bash
git clone https://github.com/<yourusername>/geoengine-utils.git
cd geoengine-utils
```

Create a virtual environment

```bash
python -m venv .venv
```

Activate it

Windows

```bash
.venv\Scripts\activate
```

Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies and the package itself

```bash
pip install -r requirements-dev.txt
pip install -e .
```

---

## Quick Start

```python
from geoengine_utils import get_raster_metadata, validate_raster

metadata = get_raster_metadata("example.tif")
result = validate_raster("example.tif")

print(metadata)
print(result.passed)
print(result.errors)
```

### CLI validation

You can also validate a raster from the command line:

```bash
python -m geoengine_utils.cli validate example.tif
```

A passing validation returns exit code `0`, while failing validation returns `1` so it can be used in scripts and CI pipelines.

### CRS and vector helpers

You can use the CRS helpers to validate a CRS definition or estimate a suitable projected CRS for a dataset footprint.

```python
from pathlib import Path

from geoengine_utils import estimate_crs, validate_crs

print(validate_crs("EPSG:4326"))

recommendation = estimate_crs(Path("example.geojson"))
print(recommendation.recommended)
print(recommendation.alternatives[:3])
```

For country-specific defaults, the package can also recommend a CRS from a country centroid.

---

## Philosophy

geoengine-utils aims to answer one question:

> **"Is this dataset ready for production?"**

Instead of simply reading metadata, geoengine-utils focuses on validating datasets against best practices used in modern geospatial data engineering workflows.

Future validation will include checks for:

- CRS validity
- NoData values
- Internal tiling
- Compression
- Overviews
- Cloud Optimized GeoTIFF compliance
- Metadata completeness
- Resolution consistency
- File integrity

---

## Roadmap

### Version 0.1

- [x] Read raster metadata
- [x] Validate raster metadata

### Version 0.2

- [ ] Raster statistics
- [ ] Pretty validation reports

### Version 0.3

- [ ] COG validation

### Version 0.4

- [ ] Convert raster to COG

### Version 0.5

- [ ] Vector utilities

### Version 1.0

- [ ] CLI
- [ ] Documentation website
- [ ] PyPI package
- [ ] GitHub Actions
- [ ] Complete test suite

---

## Contributing

Contributions are welcome!

If you have ideas for improving geoengine-utils or spot a bug, feel free to open an issue or submit a pull request.

---

## License

MIT License
