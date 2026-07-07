from dataclasses import dataclass

from pyproj.database import QueryResultCategory, query_crs_info


@dataclass
class CRSRecommendation:
    auth_name: str
    code: str
    name: str
    area_of_use: str


@dataclass
class CRSRecommendations:
    global_standard: CRSRecommendation | None
    local_recommendation: CRSRecommendation | None
    alternatives: list[CRSRecommendation]


def _get_bounds(geometry) -> tuple[float, float, float, float]:
    """
    Extract bounding coordinates from common geometry types.

    Supports:
    - shapely geometries
    - (minx, miny, maxx, maxy) tuples
    """

    if isinstance(geometry, tuple):
        return geometry

    if hasattr(geometry, "bounds"):
        return geometry.bounds

    raise ValueError(
        "Geometry must be a bounding tuple or Shapely geometry."
    )


def find_matching_crs(
    geometry,
) -> list[CRSRecommendation]:

    bounds = _get_bounds(geometry)

    matches = query_crs_info(
        pj_type=QueryResultCategory.PROJECTED_CRS,
        area_of_interest=bounds,
        contained=False,
    )

    results = []

    for crs in matches:
        results.append(
            CRSRecommendation(
                auth_name=crs.auth_name,
                code=crs.code,
                name=crs.name,
                area_of_use=crs.area_of_use.name
                if crs.area_of_use
                else "Unknown",
            )
        )

    return results


def recommend_crs(geometry) -> CRSRecommendations:

    matches = find_matching_crs(geometry)

    utm = []
    local = []
    other = []

    for crs in matches:

        name = crs.name.lower()

        if "utm" in name:

            if "wgs 84" in name:
                utm.insert(0, crs)
            else:
                utm.append(crs)

        elif any(
            keyword in name
            for keyword in (
                "state plane",
                "national",
                "south africa",
                "tm",
            )
        ):
            local.append(crs)

        else:
            other.append(crs)

    return CRSRecommendations(
        global_standard=utm[0] if utm else None,
        local_recommendation=local[0] if local else None,
        alternatives=utm[1:] + local[1:] + other[:5],
    )