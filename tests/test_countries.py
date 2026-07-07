from geoengine_utils.crs.country_lookup import (
    get_country,
    get_country_centroid,
    get_countries,
)


def test_country_dataset_exists():

    countries = get_countries()

    assert len(countries) > 0



def test_country_columns():

    countries = get_countries()

    expected = {
        "ADMIN",
        "ISO_A3",
        "centroid_lon",
        "centroid_lat",
        "utm_epsg",
        "recommended_crs",
    }

    assert expected.issubset(
        countries.columns
    )



def test_lookup_south_africa():

    country = get_country(
        "South Africa"
    )

    assert country.ADMIN == (
        "South Africa"
    )



def test_lookup_case_insensitive():

    country = get_country(
        "south africa"
    )

    assert country.ADMIN == (
        "South Africa"
    )



def test_centroid_lookup():

    result = get_country_centroid(
        "South Africa"
    )

    assert result["latitude"] < 0

    assert result["utm_epsg"] == 32734