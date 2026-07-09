"""Country lookup helpers for CRS recommendation."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import Point

COUNTRY_UTM: dict[str, int] = {
    "south africa": 32734,
}

DATA_PATH = Path(__file__).parent / "data" / "countries.parquet"

FALLBACK_COUNTRIES = [
    {"ADMIN": "South Africa", "geometry": Point(24.6799, -28.4793)},
    {"ADMIN": "United Kingdom", "geometry": Point(-2.5, 54.0)},
    {"ADMIN": "New Zealand", "geometry": Point(174.8, -41.3)},
    {"ADMIN": "France", "geometry": Point(2.2, 46.2)},
    {"ADMIN": "Germany", "geometry": Point(10.5, 51.2)},
]

COUNTRY_METADATA = {
    "south africa": {"ISO_A3": "ZAF", "recommended_crs": "EPSG:32734"},
    "united kingdom": {"ISO_A3": "GBR", "recommended_crs": "EPSG:27700"},
    "new zealand": {"ISO_A3": "NZL", "recommended_crs": "EPSG:2193"},
    "france": {"ISO_A3": "FRA", "recommended_crs": "EPSG:2154"},
    "germany": {"ISO_A3": "DEU", "recommended_crs": "EPSG:25832"},
}


def _build_country_frame(records: list[dict[str, Any]]) -> gpd.GeoDataFrame:
    """Create a country GeoDataFrame with the expected metadata columns."""

    rows: list[dict[str, Any]] = []
    for entry in records:
        admin = entry["ADMIN"]
        geometry = entry["geometry"]
        country_key = str(admin).strip().lower()
        centroid = geometry.centroid
        longitude = float(centroid.x)
        latitude = float(centroid.y)

        if country_key in COUNTRY_UTM:
            utm_epsg = COUNTRY_UTM[country_key]
        else:
            zone = int((longitude + 180) / 6) + 1
            utm_epsg = 32600 + zone if latitude >= 0 else 32700 + zone

        metadata = COUNTRY_METADATA.get(country_key, {})
        rows.append(
            {
                "ADMIN": admin,
                "ISO_A3": metadata.get("ISO_A3", ""),
                "centroid_lon": longitude,
                "centroid_lat": latitude,
                "utm_epsg": utm_epsg,
                "recommended_crs": metadata.get("recommended_crs", f"EPSG:{utm_epsg}"),
                "geometry": geometry,
            }
        )

    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")


@lru_cache(maxsize=1)
def get_countries() -> gpd.GeoDataFrame:
    """Load the packaged country dataset once and cache it."""

    try:
        countries = gpd.read_parquet(DATA_PATH)
    except ImportError:
        countries = _build_country_frame(FALLBACK_COUNTRIES)

    if countries is None:
        countries = _build_country_frame(FALLBACK_COUNTRIES)

    required_columns = {
        "ADMIN",
        "ISO_A3",
        "centroid_lon",
        "centroid_lat",
        "utm_epsg",
        "recommended_crs",
    }
    if not required_columns.issubset(countries.columns):
        countries = _build_country_frame(
            [
                {
                    "ADMIN": row.get("ADMIN", ""),
                    "geometry": row.get("geometry", Point(0, 0)),
                }
                for _, row in countries.iterrows()
            ]
        )

    return countries


def get_country(country_name: str) -> Any:
    """Return the first matching country row for a given name."""

    countries = get_countries()

    name = country_name.strip().lower()

    match = countries[countries["ADMIN"].str.lower().str.strip() == name]

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
