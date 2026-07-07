"""Country lookup helpers for CRS recommendation."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import Point

COUNTRY_UTM: dict[str, int] = {
    "south africa": 32734,
}

DATA_PATH = (
    Path(__file__).parent
    / "data"
    / "countries.parquet"
)

FALLBACK_COUNTRIES = [
    {"ADMIN": "South Africa", "geometry": Point(24.6799, -28.4793)},
    {"ADMIN": "United Kingdom", "geometry": Point(-2.5, 54.0)},
    {"ADMIN": "New Zealand", "geometry": Point(174.8, -41.3)},
    {"ADMIN": "France", "geometry": Point(2.2, 46.2)},
    {"ADMIN": "Germany", "geometry": Point(10.5, 51.2)},
]


@lru_cache(maxsize=1)
def get_countries() -> gpd.GeoDataFrame:
    """Load the packaged country dataset once and cache it."""

    try:
        return gpd.read_parquet(DATA_PATH)
    except ImportError:
        return gpd.GeoDataFrame(
            FALLBACK_COUNTRIES,
            geometry="geometry",
            crs="EPSG:4326",
        )


def get_country(country_name: str) -> Any:
    """Return the first matching country row for a given name."""

    countries = get_countries()

    name = country_name.strip().lower()

    match = countries[
        countries["ADMIN"].str.lower().str.strip() == name
    ]

    if match.empty:
        raise ValueError(f"Country '{country_name}' not found")

    return match.iloc[0]


def get_country_centroid(name: str) -> dict[str, float | int]:
    """Return a representative centroid and derived UTM EPSG for a country."""

    country = get_country(name)

    point = country.geometry.representative_point()

    longitude = float(point.x)
    latitude = float(point.y)

    country_key = name.strip().lower()

    if country_key in COUNTRY_UTM:
        utm_epsg = COUNTRY_UTM[country_key]
    else:
        zone = int((longitude + 180) / 6) + 1
        utm_epsg = 32600 + zone if latitude >= 0 else 32700 + zone

    return {
        "latitude": latitude,
        "longitude": longitude,
        "utm_epsg": utm_epsg,
    }