"""Execute faceted exact-count aggregations.

For count-based charts over bounded-enum dimensions, this issues one concurrent
``countTotal`` query per category (or per category pair, for grouped bars),
yielding EXACT counts over the full matching population — no sampling. Each row
carries example trials (from the tiny page returned alongside each count) as
deep citations.
"""

from __future__ import annotations

from app.clinicaltrials import facets
from app.clinicaltrials.client import CTGovClient
from app.clinicaltrials.params import search_params
from app.schemas import Dimension, Filters


def _facet_param_set(base: dict, advanced: list[str], *area_exprs: str) -> dict:
    p = dict(base)
    adv = advanced + list(area_exprs)
    if adv:
        p["filter.advanced"] = " AND ".join(adv)
    return p


def _refs(studies: list[dict], dim: Dimension, raw_value: str) -> list[dict]:
    field = facets.field_path(dim)
    refs = []
    for s in studies[:5]:
        nct = s.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
        if nct:
            refs.append({"nct_id": nct, "field": field, "value": raw_value})
    return refs


def can_facet_plan(dimension, secondary, metric) -> bool:
    """True if this count plan's dimension(s) are all faceted enums within budget."""
    from app.schemas import Metric

    if metric != Metric.count:
        return False
    if not facets.is_facetable(dimension):
        return False
    if secondary is not None:
        if not facets.is_facetable(secondary):
            return False
        n = len(facets.FACETABLE[dimension].values) * len(facets.FACETABLE[secondary].values)
        return n <= facets.FACET_QUERY_BUDGET
    return True


async def faceted_categorical(
    client: CTGovClient,
    filters: Filters,
    dimension: Dimension,
    value_field: str = "trial_count",
    limit: int | None = None,
    sort_desc: bool = True,
) -> tuple[list[dict], int, list[str]]:
    """Exact counts per enum value. Returns (rows, total_population, notes)."""
    base, advanced = search_params(filters)
    values = facets.facet_values(dimension)

    # total population (base filters only) + one query per facet value, concurrently.
    param_sets = [_facet_param_set(base, advanced)]
    param_sets += [_facet_param_set(base, advanced, facets.area_expr(dimension, raw)) for raw, _ in values]
    results = await client.count_many(param_sets)

    total = results[0][0]
    rows = []
    for (raw, label), (count, studies) in zip(values, results[1:]):
        if count <= 0:
            continue
        rows.append(
            {
                dimension.value: label,
                value_field: count,
                "total_contributors": count,
                "references": _refs(studies, dimension, raw),
            }
        )
    rows.sort(key=lambda r: r[value_field], reverse=sort_desc)
    notes = ["Exact counts via faceted queries over the full matching population."]
    if limit and len(rows) > limit:
        notes.append(f"Showing top {limit} of {len(rows)} categories.")
        rows = rows[:limit]
    return rows, total, notes


async def faceted_grouped(
    client: CTGovClient,
    filters: Filters,
    primary: Dimension,
    secondary: Dimension,
    limit: int | None = None,
) -> tuple[list[dict], int, list[str]]:
    """Exact counts per (primary, secondary) enum pair."""
    base, advanced = search_params(filters)
    pvals = facets.facet_values(primary)
    svals = facets.facet_values(secondary)

    combos = [(pr, pl, sr, sl) for pr, pl in pvals for sr, sl in svals]
    total_set = _facet_param_set(base, advanced)
    param_sets = [total_set] + [
        _facet_param_set(base, advanced, facets.area_expr(primary, pr), facets.area_expr(secondary, sr))
        for pr, _, sr, _ in combos
    ]
    results = await client.count_many(param_sets)
    total = results[0][0]

    rows = []
    for (pr, pl, sr, sl), (count, studies) in zip(combos, results[1:]):
        if count <= 0:
            continue
        rows.append(
            {
                primary.value: pl,
                secondary.value: sl,
                "trial_count": count,
                "total_contributors": count,
                "references": _refs(studies, primary, pr),
            }
        )
    rows.sort(key=lambda r: r["trial_count"], reverse=True)
    notes = ["Exact counts via faceted queries over the full matching population."]
    if limit:
        rows = rows[:limit]
    return rows, total, notes
