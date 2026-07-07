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
git clone https://github.com/<yourusername>/geoforge.git
cd geoforge
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

Install dependencies

```bash
pip install -r requirements-dev.txt
```

---

## Quick Start

```python
from geoforge import validate_raster

result = validate_raster("example.tif")

print(result)
```

Example output

```text
ValidationResult(
    passed=True,
    warnings=[],
    errors=[]
)
```

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

If you have ideas for improving GeoForge or spot a bug, feel free to open an issue or submit a pull request.

---

## License

MIT License