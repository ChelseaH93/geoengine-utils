from importlib.resources import files

import geopandas as gpd


_COUNTRIES = None


def get_countries():

    global _COUNTRIES

    if _COUNTRIES is None:

        path = (
            files("geoengine_utils")
            / "data"
            / "countries.parquet"
        )

        _COUNTRIES = gpd.read_file(path)

    return _COUNTRIES