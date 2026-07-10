"""CRS recommendation helpers for projected coordinate systems."""

from os import PathLike
from pathlib import Path
from typing import Any

import geopandas as gpd
import rasterio
from pyproj import CRS
from pyproj.aoi import AreaOfInterest
from pyproj.database import query_crs_info
from pyproj.enums import PJType
from shapely.geometry.base import BaseGeometry

from .country_lookup import get_country_centroid, utm_epsg_for
from .models import CRSInfo, CRSRecommendation
from .registry import PREFERRED_CRS


def normalise_bounds(
    geometry: BaseGeometry | tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    """Normalise a geometry or bounds tuple into a 4-tuple."""

    if hasattr(geometry, "bounds"):
        return tuple(float(value) for value in geometry.bounds)

    if hasattr(geometry, "__len__") and not isinstance(geometry, (str, bytes)):
        values = list(geometry)
        if len(values) == 4:
            return tuple(float(value) for value in values)

    if isinstance(geometry, tuple):
        if len(geometry) != 4:
            raise ValueError("Bounds must be (minx,miny,maxx,maxy)")
        return tuple(float(value) for value in geometry)

    raise TypeError("Expected shapely geometry or bounds tuple")


def query_matching_crs(bounds: tuple[float, float, float, float]) -> list[Any]:
    """Query projected CRS definitions covering the provided bounds."""

    minx, miny, maxx, maxy = bounds

    matches = query_crs_info(
        pj_types=PJType.PROJECTED_CRS,
        area_of_interest=AreaOfInterest(
            west_lon_degree=minx,
            south_lat_degree=miny,
            east_lon_degree=maxx,
            north_lat_degree=maxy,
        ),
        contains=False,
    )

    if not matches:
        raise ValueError("No projected CRS found for the supplied bounds")

    return matches


def crs_to_info(crs: Any, score: float = 0) -> CRSInfo:
    """Convert a CRS object into the package's CRSInfo model."""

    authority: tuple[Any, ...] | list[Any] | None = None

    if hasattr(crs, "to_authority"):
        try:
            authority = crs.to_authority()
        except Exception:
            authority = None

    if authority is None:
        authority = (
            getattr(crs, "auth_name", None),
            getattr(crs, "code", None),
        )

    auth_name = ""
    code = ""

    if isinstance(authority, (tuple, list)) and len(authority) >= 1:
        auth_name = authority[0] or ""

    if isinstance(authority, (tuple, list)) and len(authority) >= 2:
        code = authority[1] or ""

    return CRSInfo(
        auth_name=auth_name,
        code=code,
        name=crs.name,
        area_of_use=crs.area_of_use.name if crs.area_of_use else None,
        score=score,
    )


def find_country_candidate_crs(latitude: float, longitude: float) -> list[Any]:
    """Find projected CRS candidates around a country centroid."""

    bounds = (
        longitude - 0.1,
        latitude - 0.1,
        longitude + 0.1,
        latitude + 0.1,
    )

    return query_matching_crs(bounds)


def score_crs(crs: Any, lon: float | None = None, lat: float | None = None) -> int:
    """Score a CRS candidate using location-aware heuristics.

    The scoring now considers the candidate CRS name, the area of use,
    whether it is a UTM-style CRS, and whether its authority code aligns with
    the geometry centroid location.
    """

    score = 0
    name = (getattr(crs, "name", "") or "").lower()
    area = (getattr(crs.area_of_use, "name", "") or "").lower()

    if "utm" in name:
        score += 100

    if "wgs 84" in name:
        score += 20

    if "transverse mercator" in name:
        score += 15

    if lon is not None and lat is not None:
        authority = None
        if hasattr(crs, "to_authority"):
            try:
                authority = crs.to_authority()
            except Exception:
                authority = None

        if authority is None:
            authority = (getattr(crs, "auth_name", None), getattr(crs, "code", None))

        if isinstance(authority, (tuple, list)) and len(authority) >= 2:
            code = str(authority[1] or "")
            if code.startswith(("326", "327")) and len(code) == 5:
                zone = int(code[-2:])
                expected_zone = int((lon + 180) / 6) + 1
                if zone == expected_zone:
                    score += 50
                elif abs(zone - expected_zone) == 1:
                    score += 20

    if area:
        score += 5

    return score


def utm_epsg(lon: float, lat: float) -> int:
    """Derive a UTM EPSG code from longitude and latitude."""

    return utm_epsg_for(lon, lat)


def recommend_crs(geometry: BaseGeometry | tuple[float, float, float, float]) -> CRSRecommendation:
    """Recommend a projected CRS for a geometry based on its extent."""

    bounds = normalise_bounds(geometry)
    matches = query_matching_crs(bounds)

    if not matches:
        raise ValueError("No projected CRS found")

    minx, miny, maxx, maxy = bounds
    lon = (minx + maxx) / 2
    lat = (miny + maxy) / 2

    for match in matches:
        area = match.area_of_use.name.lower()

        for country, preferred in PREFERRED_CRS.items():
            if country.lower() in area:
                crs = CRS.from_epsg(preferred.epsg)
                return CRSRecommendation(
                    recommended=crs_to_info(crs),
                    alternatives=[],
                    reason=preferred.reason,
                )

    epsg = utm_epsg(lon, lat)
    crs = CRS.from_epsg(epsg)

    alternatives = sorted(
        [crs_to_info(item, score=score_crs(item, lon=lon, lat=lat)) for item in matches],
        key=lambda item: item.score,
        reverse=True,
    )

    return CRSRecommendation(
        recommended=crs_to_info(crs),
        alternatives=alternatives,
        reason="Recommended UTM CRS based on geometry centroid.",
    )


def estimate_crs(data: Any) -> CRSRecommendation:
    """Estimate a suitable projected CRS from a dataset path, geometry, or bounds."""

    if isinstance(data, (str, PathLike)):
        path = Path(data)

        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {path}")

        try:
            vector_data = gpd.read_file(path)
        except Exception:
            with rasterio.open(path) as src:
                bounds = (
                    src.bounds.left,
                    src.bounds.bottom,
                    src.bounds.right,
                    src.bounds.top,
                )
            return recommend_crs(bounds)

        return recommend_crs(vector_data.total_bounds)

    if isinstance(data, gpd.GeoDataFrame):
        return recommend_crs(data.total_bounds)

    if isinstance(data, gpd.GeoSeries):
        return recommend_crs(data.total_bounds)

    if hasattr(data, "bounds") and hasattr(data, "total_bounds"):
        return recommend_crs(data.total_bounds)

    if hasattr(data, "bounds"):
        return recommend_crs(data.bounds)

    return recommend_crs(data)


def find_matching_crs(geometry: BaseGeometry | tuple[float, float, float, float]) -> list[Any]:
    """Backwards compatible wrapper for CRS matching."""

    bounds = normalise_bounds(geometry)
    return query_matching_crs(bounds)


def recommend(
    geometry: BaseGeometry | tuple[float, float, float, float] | None = None,
    country: str | None = None,
) -> CRSRecommendation:
    """Recommend a CRS for a geometry or a country centroid."""

    if country:
        centroid = get_country_centroid(country)
        candidates = find_country_candidate_crs(
            centroid["latitude"],
            centroid["longitude"],
        )

        candidates = [
            candidate for candidate in candidates if candidate.code.startswith(("326", "327"))
        ]

        ranked = sorted(
            candidates,
            key=lambda candidate: score_crs(
                candidate, lon=centroid["longitude"], lat=centroid["latitude"]
            ),
            reverse=True,
        )
        recommended = CRS.from_epsg(centroid["utm_epsg"])

        return CRSRecommendation(
            recommended=crs_to_info(recommended),
            alternatives=[
                crs_to_info(
                    candidate,
                    score=score_crs(
                        candidate,
                        lon=centroid["longitude"],
                        lat=centroid["latitude"],
                    ),
                )
                for candidate in ranked[:5]
            ],
            reason="Recommended UTM CRS based on country centroid.",
        )

    if geometry is None:
        raise ValueError("Either geometry or country must be provided")

    return recommend_crs(geometry)
