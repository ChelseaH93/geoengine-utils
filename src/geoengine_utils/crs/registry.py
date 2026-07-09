"""Registry of preferred projected CRSs.

The goal of this file is to recommend the CRS that a GIS professional
would typically choose for a given country, rather than simply returning
the nearest UTM zone.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class PreferredCRS:
    """Preferred CRS metadata for a country."""

    country: str
    epsg: int
    reason: str


PREFERRED_CRS: dict[str, PreferredCRS] = {
    "United Kingdom": PreferredCRS(
        country="United Kingdom",
        epsg=27700,
        reason="British National Grid is the official mapping CRS for Great Britain.",
    ),
    "South Africa": PreferredCRS(
        country="South Africa",
        epsg=2054,
        reason="Hartebeesthoek94 / Lo31 is widely used for engineering and cadastral work.",
    ),
    "New Zealand": PreferredCRS(
        country="New Zealand",
        epsg=2193,
        reason="NZTM2000 is the national projected CRS.",
    ),
    "France": PreferredCRS(
        country="France",
        epsg=2154,
        reason="Lambert-93 is the official national projection.",
    ),
    "Germany": PreferredCRS(
        country="Germany",
        epsg=25832,
        reason="ETRS89 / UTM Zone 32N is the national standard.",
    ),
}
