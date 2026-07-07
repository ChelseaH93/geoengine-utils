from functools import lru_cache
from pathlib import Path

import geopandas as gpd


DATA_PATH = (
    Path(__file__).parent
    / "data"
    / "countries.parquet"
)


@lru_cache(maxsize=1)
def get_countries():

    return gpd.read_parquet(
        DATA_PATH
    )


def get_country(country_name: str):

    countries = get_countries()

    name = country_name.strip().lower()

    match = countries[
        countries["ADMIN"]
        .str.lower()
        .str.strip()
        == name
    ]

    if match.empty:
        raise ValueError(
            f"Country '{country_name}' not found"
        )

    return match.iloc[0]


def get_country_centroid(country_name):

    country = get_country(
        country_name
    )

    return {
        "country": country.ADMIN,
        "longitude": country.centroid_lon,
        "latitude": country.centroid_lat,
        "utm_epsg": country.utm_epsg,
    }