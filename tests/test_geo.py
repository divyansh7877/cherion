from app.agg import geo


def test_geo_regions_and_points(pembro_studies):
    result, notes = geo.aggregate_geo(pembro_studies, "country")
    assert result["regions"], "expected country aggregation"
    assert all(r["references"] for r in result["regions"])
    assert any("≥1 site" in n for n in notes)


def test_region_counts_dedup_per_trial():
    # one trial with two US sites should count once for United States
    study = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT1"},
            "contactsLocationsModule": {
                "locations": [
                    {"country": "United States", "city": "Boston", "geoPoint": {"lat": 42.36, "lon": -71.06}},
                    {"country": "United States", "city": "Austin", "geoPoint": {"lat": 30.27, "lon": -97.74}},
                ]
            },
        }
    }
    result, _ = geo.aggregate_geo([study], "country")
    us = [r for r in result["regions"] if r["region"] == "United States"][0]
    assert us["trial_count"] == 1
    # two distinct points though
    assert len(result["points"]) == 2


def test_regions_sorted_desc(diabetes_studies):
    result, _ = geo.aggregate_geo(diabetes_studies, "country")
    counts = [r["trial_count"] for r in result["regions"]]
    assert counts == sorted(counts, reverse=True)
