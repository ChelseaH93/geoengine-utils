from pathlib import Path

import geopandas as gpd

INPUT = Path(r"C:\Users\chels\Downloads\ne_10m_admin_0_countries\ne_10m_admin_0_countries.shp")
OUTPUT = Path("src/geoengine_utils/crs/data/countries.parquet")


def utm_epsg(lon, lat):

    zone = int((lon + 180) / 6) + 1

    if lat >= 0:
        return 32600 + zone

    return 32700 + zone


def main():

    countries = gpd.read_file(INPUT)

    # keep useful fields
    countries = countries[
        [
            "ADMIN",
            "ISO_A2",
            "ISO_A3",
            "geometry",
        ]
    ]

    # Calculate accurate centroid
    metric = countries.to_crs("EPSG:6933")

    centroids = metric.centroid.to_crs("EPSG:4326")

    countries["centroid_lon"] = centroids.x

    countries["centroid_lat"] = centroids.y

    countries["utm_zone"] = ((countries.centroid_lon + 180) / 6).astype(int) + 1

    countries["utm_epsg"] = [
        utm_epsg(lon, lat)
        for lon, lat in zip(
            countries.centroid_lon,
            countries.centroid_lat,
            strict=True,
        )
    ]

    countries["recommended_crs"] = "EPSG:" + countries.utm_epsg.astype(str)

    countries.to_parquet(
        OUTPUT,
        index=False,
    )


if __name__ == "__main__":
    main()
