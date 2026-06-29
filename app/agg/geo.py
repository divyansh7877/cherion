"""Geographic aggregation from trial site locations.

Produces choropleth rows (region -> trial count) and point rows (lat/lng + weight).
A trial with multiple sites in the same region counts once for that region, so a
region's count means "trials with >=1 site here". Each region cites contributing
trials.
"""

from __future__ import annotations

from collections import defaultdict

from app.agg import extractors as ex
from app.agg.citations import build_references

_FIELD = "protocolSection.contactsLocationsModule.locations"


def _locations(study: dict) -> list[dict]:
    return study.get("protocolSection", {}).get("contactsLocationsModule", {}).get("locations", [])


def aggregate_geo(studies: list[dict], region_key: str = "country", limit: int | None = None) -> tuple[dict, list[str]]:
    """Aggregate trials by region. ``region_key`` is 'country' or 'state'.

    Returns ({regions: [...], points: [...]}, notes). ``regions`` drives a
    choropleth; ``points`` drives an optional point map (only sites with geoPoint).
    """
    notes: list[str] = []
    region_contribs: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    # point map: aggregate by rounded coordinate to limit volume
    point_contribs: dict[tuple[float, float], list[str]] = defaultdict(list)
    point_label: dict[tuple[float, float], str] = {}
    missing_region = 0

    for study in studies:
        nct = ex.nct_id(study)
        regions_seen: set[str] = set()
        for loc in _locations(study):
            region = loc.get(region_key)
            if region and region not in regions_seen:
                regions_seen.add(region)
                region_contribs[region].append((nct, f"{_FIELD}.{region_key}", region))
            geo = loc.get("geoPoint") or {}
            lat, lon = geo.get("lat"), geo.get("lon")
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                key = (round(lat, 2), round(lon, 2))
                point_contribs[key].append(nct)
                point_label.setdefault(key, loc.get("city") or region or "")
        if not regions_seen:
            missing_region += 1

    regions = []
    for region, contribs in region_contribs.items():
        regions.append(
            {
                "region": region,
                "trial_count": len(contribs),
                "total_contributors": len(contribs),
                "references": [r.model_dump() for r in build_references(contribs)],
            }
        )
    regions.sort(key=lambda r: r["trial_count"], reverse=True)
    if limit and len(regions) > limit:
        notes.append(f"Showing top {limit} of {len(regions)} regions.")
        regions = regions[:limit]

    points = []
    for (lat, lon), ncts in point_contribs.items():
        uniq = list(dict.fromkeys(ncts))
        points.append(
            {
                "lat": lat,
                "lng": lon,
                "label": point_label.get((lat, lon), ""),
                "trial_count": len(uniq),
                "total_contributors": len(uniq),
                "references": [{"nct_id": n, "field": f"{_FIELD}.geoPoint", "value": f"{lat},{lon}"} for n in uniq[:5]],
            }
        )
    points.sort(key=lambda p: p["trial_count"], reverse=True)

    notes.append(f"Counts are trials with ≥1 site per {region_key}; a trial may appear in multiple regions.")
    if missing_region:
        notes.append(f"{missing_region} trials had no site location data.")
    return {"regions": regions, "points": points}, notes
