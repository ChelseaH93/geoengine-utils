from pyproj import CRS
from pyproj.database import query_crs_info
from pyproj.enums import PJType
from pyproj.aoi import AreaOfInterest

from shapely.geometry.base import BaseGeometry

from .country_lookup import get_countries

from .models import CRSInfo
from .models import CRSRecommendation
from .registry import PREFERRED_CRS

def _normalise_bounds(
    geometry: BaseGeometry | tuple
) -> tuple[float, float, float, float]:

    if hasattr(geometry, "bounds"):
        return geometry.bounds

    if isinstance(geometry, tuple):

        if len(geometry) != 4:
            raise ValueError(
                "Bounds must be "
                "(minx, miny, maxx, maxy)"
            )

        return geometry

    raise TypeError(
        "Expected Shapely geometry or bounds tuple."
    )


def get_country(geometry: BaseGeometry):

    countries = get_countries()

    centroid = geometry.centroid

    match = countries.loc[
        countries.contains(centroid)
    ]

    if match.empty:
        return None

    return match.iloc[0]["ADMIN"]

def find_matching_crs(
    geometry,
) -> list[CRSInfo]:

    minx, miny, maxx, maxy = _normalise_bounds(
        geometry
    )

    crs_list = query_crs_info(
        pj_types=PJType.PROJECTED_CRS,
        area_of_interest=AreaOfInterest(
            west_lon_degree=minx,
            south_lat_degree=miny,
            east_lon_degree=maxx,
            north_lat_degree=maxy,
        ),
        contains=False,
    )
    return [
        CRSInfo(
            auth_name=i.auth_name,
            code=i.code,
            name=i.name,
            area_of_use=i.area_of_use.name,
        )
        for i in crs_list
    ]

def _score(crs: CRSInfo):

    score = 0

    name = crs.name.lower()

    if "utm" in name:
        score += 100

    if "wgs 84" in name:
        score += 20

    if "tm" in name:
        score += 15

    if "state plane" in name:
        score += 10

    if "engineering" in name:
        score += 5

    return score

def recommend_crs(geometry):

    bounds = _normalise_bounds(geometry)

    matches = _query_matching_crs(bounds)

    if not matches:
        raise ValueError("No projected CRS found.")

    minx, miny, maxx, maxy = bounds

    lon = (minx + maxx) / 2
    lat = (miny + maxy) / 2

    #
    # STEP 1
    # Look for preferred national CRS
    #

    for match in matches:

        if not match.area_of_use:
            continue

        area_name = match.area_of_use.name

        for country, preferred in PREFERRED_CRS.items():

            if country.lower() in area_name.lower():

                crs = CRS.from_epsg(preferred.epsg)

                return CRSRecommendation(

                    recommended=CRSInfo(
                        auth_name="EPSG",
                        code=str(preferred.epsg),
                        name=crs.name,
                        area_of_use=crs.area_of_use.name,
                    ),

                    alternatives=[],

                    reason=preferred.reason,
                )

    #
    # STEP 2
    # Otherwise recommend UTM
    #

    epsg = _utm_epsg(lon, lat)

    crs = CRS.from_epsg(epsg)

    return CRSRecommendation(

        recommended=CRSInfo(
            auth_name="EPSG",
            code=str(epsg),
            name=crs.name,
            area_of_use=crs.area_of_use.name,
        ),

        alternatives=[],

        reason="Nearest UTM projection based on dataset centroid.",
    )

def _normalise_bounds(geometry):

    if hasattr(geometry, "bounds"):
        return geometry.bounds

    if isinstance(geometry, tuple):

        if len(geometry) != 4:
            raise ValueError("Bounds must be (minx,miny,maxx,maxy).")

        return geometry

    raise TypeError("Unsupported geometry.")

def _query_matching_crs(bounds):

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

def _utm_epsg(lon, lat):

    zone = int((lon + 180) / 6) + 1

    if lat >= 0:
        return 32600 + zone

    return 32700 + zone