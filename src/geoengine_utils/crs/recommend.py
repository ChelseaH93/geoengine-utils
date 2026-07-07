from functools import lru_cache
from pyproj import CRS
from pyproj.database import query_crs_info
from pyproj.enums import PJType
from pyproj.aoi import AreaOfInterest
from shapely.geometry.base import BaseGeometry

from .models import CRSInfo, CRSRecommendation
from .registry import PREFERRED_CRS
from .country_lookup import (
    get_country_centroid,
)

# --------------------------------------------------
# Geometry helpers
# --------------------------------------------------

def normalise_bounds(
    geometry: BaseGeometry | tuple
):

    if hasattr(geometry, "bounds"):
        return geometry.bounds

    if isinstance(geometry, tuple):

        if len(geometry) != 4:
            raise ValueError(
                "Bounds must be (minx,miny,maxx,maxy)"
            )

        return geometry

    raise TypeError(
        "Expected shapely geometry or bounds tuple"
    )


# --------------------------------------------------
# CRS discovery
# --------------------------------------------------

def query_matching_crs(bounds):

    minx, miny, maxx, maxy = bounds

    return query_crs_info(
        pj_types=PJType.PROJECTED_CRS,
        area_of_interest=AreaOfInterest(
            west_lon_degree=minx,
            south_lat_degree=miny,
            east_lon_degree=maxx,
            north_lat_degree=maxy,
        ),
        contains=False,
    )


def crs_to_info(crs):

    return CRSInfo(
        auth_name=crs.auth_name,
        code=str(crs.code),
        name=crs.name,
        area_of_use=(
            crs.area_of_use.name
            if crs.area_of_use
            else None
        ),
    )


# --------------------------------------------------
# CRS ranking
# --------------------------------------------------

def score_crs(crs):

    score = 0

    name = crs.name.lower()

    rules = {
        "utm": 100,
        "wgs 84": 20,
        "transverse mercator": 15,
        "state plane": 10,
        "engineering": 5,
    }

    for keyword, value in rules.items():

        if keyword in name:
            score += value

    return score


# --------------------------------------------------
# Recommendation engine
# --------------------------------------------------

def utm_epsg(lon, lat):

    zone = int((lon + 180) / 6) + 1

    return (
        32600 + zone
        if lat >= 0
        else 32700 + zone
    )


def recommend_crs(geometry):

    bounds = normalise_bounds(geometry)

    matches = query_matching_crs(bounds)

    if not matches:
        raise ValueError(
            "No projected CRS found"
        )


    minx, miny, maxx, maxy = bounds

    lon = (minx + maxx) / 2
    lat = (miny + maxy) / 2


    # national preferred CRS

    for match in matches:

        area = match.area_of_use.name.lower()

        for country, preferred in PREFERRED_CRS.items():

            if country.lower() in area:

                crs = CRS.from_epsg(
                    preferred.epsg
                )

                return CRSRecommendation(
                    recommended=crs_to_info(crs),
                    alternatives=[],
                    reason=preferred.reason,
                )


    # fallback UTM

    epsg = utm_epsg(lon, lat)

    crs = CRS.from_epsg(epsg)

    alternatives = sorted(
        [
            crs_to_info(i)
            for i in matches
        ],
        key=score_crs,
        reverse=True,
    )[:5]


    return CRSRecommendation(
        recommended=crs_to_info(crs),
        alternatives=alternatives,
        reason=(
            "Recommended UTM CRS "
            "based on geometry centroid."
        ),
    )


# --------------------------------------------------
# Public API
# --------------------------------------------------

def recommend(
    geometry=None,
    country=None,
):

    if country:

        centroid = get_country_centroid(
            country
        )

        geometry = (
            centroid["longitude"],
            centroid["latitude"],
            centroid["longitude"],
            centroid["latitude"],
        )


    if geometry is None:
        raise ValueError(
            "Provide geometry or country"
        )


    return recommend_crs(
        geometry
    )