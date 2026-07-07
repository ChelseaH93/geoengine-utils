"""Country lookup helpers for CRS recommendation."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import geopandas as gpd

COUNTRY_UTM: dict[str, int] = {
    "south africa": 32734,
}

DATA_PATH = (
    Path(__file__).parent
    / "data"
    / "countries.parquet"
)


@lru_cache(maxsize=1)
def get_countries() -> gpd.GeoDataFrame:
    """Load the packaged country dataset once and cache it."""

    return gpd.read_parquet(DATA_PATH)


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