from pyproj.database import query_crs_info
from pyproj.enums import PJType
from pyproj.aoi import AreaOfInterest

from shapely.geometry.base import BaseGeometry

from .models import CRSInfo
from .models import CRSRecommendation

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

def recommend_crs(
    geometry,
) -> CRSRecommendation:

    matches = find_matching_crs(
        geometry
    )

    if not matches:

        raise ValueError(
            "No projected CRS found."
        )

    matches.sort(
        key=_score,
        reverse=True,
    )

    best = matches[0]

    return CRSRecommendation(
        recommended=best,
        alternatives=matches[1:6],
        reason=(
            f"{best.auth_name}:{best.code} "
            "is the highest ranked projected CRS "
            "covering the supplied extent."
        ),
    )
